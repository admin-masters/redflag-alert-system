#!/usr/bin/env python
"""
Import a condition form from a Google Sheet laid out LONG-wise:
one row per option, grouped by "Sr No".

No 'QuestionKey' column is required.
"""

from __future__ import annotations
import argparse, re
from typing import Dict
import gspread
import pandas as pd
import numpy as np
from unidecode import unidecode
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db import models


# ---------------- helpers --------------------------------------------------- #
def slug(txt: str, max_len: int = 60) -> str:
    base = unidecode(txt).lower()
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    return base[:max_len] or "x"


def upsert(db: Session, model, match: Dict, defaults: Dict):
    obj = db.query(model).filter_by(**match).one_or_none()
    if obj:
        for k, v in defaults.items():
            setattr(obj, k, v)
    else:
        obj = model(**match, **defaults)
        db.add(obj)
    return obj


# ---------------- core ingest ---------------------------------------------- #
def ingest_tab(df: pd.DataFrame, lang: str, form: models.Form, db: Session):

    # standardise headers -> remove spaces, lower-case, replace with underscores
    df.columns = [re.sub(r"[^A-Za-z0-9]", "_", c).lower() for c in df.columns]

    must_have = {"sr_no", "question", "option"}
    if not must_have.issubset(df.columns):
        raise ValueError(
            f"Sheet '{lang}' missing columns: {', '.join(must_have - set(df.columns))}"
        )

    # clean Sr No column -> forward-fill
    df["sr_no"] = (
        df["sr_no"]
        .astype(str)
        .str.strip()
        .replace({"": np.nan})
        .ffill()
    )

    # drop rows still NaN
    df = df.dropna(subset=["sr_no", "question", "option"])

    for sr_no, group in df.groupby("sr_no", sort=False):
        try:
            order_idx = int(float(sr_no))
        except ValueError:
            print(f"[WARN] bad Sr No '{sr_no}', skipped")
            continue

        q_text = str(group["question"].iloc[0]).strip()
        if not q_text:
            continue

        # ① upsert QUESTION by (form, order)
        # detect type: single 'Free text' row ⇒ text, ≥1 rows & "multi" flag later ⇒ checkbox
        first_opt = str(group["option"].iloc[0]).strip().lower()
        input_type = models.InputType.text if first_opt == "free text" else models.InputType.radio
        question = upsert(
                db,
                models.Question,
                {"form_id": form.id, "order_idx": order_idx},
                {"input_type": input_type},
        )
        db.flush()
        upsert(
            db,
            models.QuestionLocalised,
            {"question_id": question.id, "lang_code": lang},
            {"text": q_text},
        )

        # iterate each OPTION row for this question
        for idx, row in enumerate(group.itertuples(index=False), start=1):
            opt_txt = str(row.option).strip()
            if not opt_txt:
                continue

            opt_key = slug(opt_txt, 40)
            is_rf = str(getattr(row, "red_flag_trigger", "")).strip().lower() in {
                "yes", "true", "y", "1"
            }
            rf_raw = str(getattr(row, "redflag_id", "")).strip()
            rf_slug = slug(rf_raw) if is_rf and rf_raw else None

            # ② upsert OPTION
            db.flush()  # ← ensure option.id is now assigned
            option = upsert(
                    db,
                    models.Option,
                    {"question_id": question.id, "order_idx": idx},
                    {
                            "option_key": opt_key,
                            "is_redflag": is_rf,
                    },
            )
            db.flush()  # option.id now non-NULL

            upsert(
                db,
                models.OptionLocalised,
                {"option_id": option.id, "lang_code": lang},
                {"text": opt_txt},
            )

            # ③ red-flag rows & resources
            if is_rf and rf_slug:
                ataglance = str(getattr(row, "at_a_glance", "")).strip()
                mini_cme = str(getattr(row, "mini_cme_vimeo", "")).strip() or None
                long_cme = str(getattr(row, "long_cme_vimeo", "")).strip() or None
                patient_vid = str(
                    getattr(row, "patient_video_you_tube", "")
                ).strip() or None

                rf = upsert(
                    db,
                    models.RedFlag,
                    {"slug": rf_slug},
                    {
                        "name_en": rf_raw or rf_slug,
                        "ataglance_en": ataglance,
                        "mini_cme_vimeo": mini_cme,
                        "long_cme_vimeo": long_cme,
                    },
                )

                db.flush()  # <-- Ensure rf.id is assigned

                option.redflag_id = rf.id

                upsert(
                    db,
                    models.RedFlagLocalised,
                    {"redflag_id": rf.id, "lang_code": lang},
                    {
                        "name": rf.name_en,
                        "ataglance_text": ataglance,
                        "patient_video_youtube": patient_vid,
                    },
                )

            elif is_rf and not rf_slug:
                print(f"[WARN] Sr No {sr_no} option '{opt_txt}' marked as red‑flag but Redflag_id blank – skipped")

    db.commit()
    print(f"✓ {lang} imported")


# ---------------- CLI ------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--version", default="1")
    ap.add_argument("--langs", nargs="+", required=True)
    args = ap.parse_args()

    gs = gspread.service_account(filename="gsa_inditech.json")  # JSON pointed to by $GOOGLE_APPLICATION_CREDENTIALS
    sh = gs.open_by_key(args.sheet)

    db: Session = SessionLocal()
    form = upsert(
        db,
        models.Form,
        {"slug": args.slug},
        {
            "version": args.version,
            "is_active": True,
            "title_en": sh.title,
            "description_en": f"{sh.title} imported",
        },
    )
    db.commit()

    for lang in args.langs:
        try:
            ws = sh.worksheet(lang)
        except gspread.WorksheetNotFound:
            print(f"[WARN] tab '{lang}' not found; skipping")
            continue

        rows = ws.get_all_values()
        if not rows:
            print(f"[WARN] tab '{lang}' empty; skipping")
            continue

        df = pd.DataFrame(rows[1:], columns=rows[0])
        ingest_tab(df, lang, form, db)

    db.close()
    print("✓ Import complete")


if __name__ == "__main__":
    main()
