"""
Usage:
    python scripts/import_form_from_gsheet.py \
        --sheet "1J4xsPiY_GSeIMyBqz8V77IX9dhmzsaTHc9tcwSA__yE" \
        --slug rash_body --version 1 \
        --langs EN HI TA

The script:
  • Creates (or updates) Form, Questions, Options, RedFlags, Videos, References
  • Handles any number of language tabs (one tab per language code)
  • Is idempotent – running twice won’t duplicate rows
"""

from __future__ import annotations
import argparse, re, json
import gspread
import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db import models

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def upsert(db: Session, model, match: dict, defaults: dict):
    obj = db.query(model).filter_by(**match).one_or_none()
    if obj:
        for k, v in defaults.items():
            setattr(obj, k, v)
    else:
        obj = model(**match, **defaults)
        db.add(obj)
    return obj


def parse_options(row: pd.Series) -> list[dict]:
    """
    Expect columns Option 1 Text, Option 1 Key, Option 1 IsRedFlag, ...
    Returns list[{option_key, text, is_redflag, redflag_slug, redflag_name, …}]
    """
    opts = []
    opt_cols = [c for c in row.index if re.match(r"Option \d+ Text", c)]
    for text_col in opt_cols:
        base = text_col.replace(" Text", "")
        key_col = base.replace("Text", "Key")
        rf_col = base.replace("Text", "IsRedFlag")
        rf_slug_col = base.replace("Text", "RedFlagSlug")
        rf_name_col = base.replace("Text", "RedFlagName")
        if pd.isna(row[text_col]):
            continue
        opts.append(
            {
                "option_key": str(row[key_col]).strip(),
                "text": str(row[text_col]).strip(),
                "is_redflag": bool(row[rf_col]),
                "redflag_slug": str(row[rf_slug_col]).strip() if rf_slug_col in row else None,
                "redflag_name": str(row[rf_name_col]).strip() if rf_name_col in row else None,
            }
        )
    return opts


def ingest_tab(db: Session, df: pd.DataFrame, lang: str, form: models.Form):
    """
    df = one sheet read via pandas
    Assumes first data row per question; blank rows ignored.
    """
    for _, row in df.dropna(subset=["QuestionKey"]).iterrows():
        q = upsert(
            db,
            models.Question,
            {"question_key": row["QuestionKey"]},
            {"form_id": form.id, "order_idx": int(row["Order"])},
        )

        upsert(
            db,
            models.QuestionLocalised,
            {"question_id": q.id, "lang_code": lang},
            {"text": row["QuestionText"]},
        )

        for idx, opt in enumerate(parse_options(row), start=1):
            o = upsert(
                db,
                models.Option,
                {"question_id": q.id, "option_key": opt["option_key"]},
                {
                    "order_idx": idx,
                    "is_redflag": opt["is_redflag"],
                },
            )
            upsert(
                db,
                models.OptionLocalised,
                {"option_id": o.id, "lang_code": lang},
                {"text": opt["text"]},
            )

            # — red-flag rows (create once, language-agnostic name_en now) —
            if opt["is_redflag"] and opt["redflag_slug"]:
                rf = upsert(
                    db,
                    models.RedFlag,
                    {"slug": opt["redflag_slug"]},
                    {
                        "name_en": opt["redflag_name"] or opt["redflag_slug"],
                        "ataglance_en": row.get("AtAGlanceEN", ""),
                    },
                )
                o.redflag_id = rf.id  # link option→redflag

    db.flush()


# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True, help="Google sheet id")
    ap.add_argument("--slug", required=True, help="form slug, e.g. rash_body")
    ap.add_argument("--version", default="1")
    ap.add_argument("--langs", nargs="+", required=True, help="EN HI TA ...")
    args = ap.parse_args()

    # Connect Sheets
    gc = gspread.client.Client.from_service_account()
    sh = gc.open_by_key(args.sheet)

    db = SessionLocal()

    # Create/update Form entry
    form = upsert(
        db,
        models.Form,
        {"slug": args.slug},
        {
            "version": args.version,
            "is_active": True,
            "title_en": sh.title,
            "description_en": f"{sh.title} – imported from Google Sheets",
        },
    )
    db.commit()

    # Loop languages
    for lang in args.langs:
        if lang not in [ws.title for ws in sh.worksheets()]:
            print(f"[WARN] sheet {lang} not found, skipping")
            continue
        ws = sh.worksheet(lang)
        df = pd.DataFrame(ws.get_all_records())
        ingest_tab(db, df, lang, form)
        db.commit()
        print(f"✓ {lang} imported")

    db.close()
    print("✓ Import complete.")


if __name__ == "__main__":
    main()