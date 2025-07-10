"""
Populate a tiny data set so /patient/open/... works.
Run with:  INDITECH_CFG=~/redflag-alert-system/dev_secrets.toml  \
           python scripts/seed_sample.py
"""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db import models


# ---- helper ---------------------------------------------------------------
def add_if_missing(db: Session, model, defaults: dict, **lookup):
    obj = db.query(model).filter_by(**lookup).one_or_none()
    if obj:
        return obj
    obj = model(**lookup, **defaults)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def main() -> None:
    db = SessionLocal()

    # 1) languages ----------------------------------------------------------
    en = add_if_missing(
        db,
        models.Language,
        {"native_name": "English"},
        code="EN",
    )

    # 2) clinic + doctor ----------------------------------------------------
    clinic = add_if_missing(
        db,
        models.Clinic,
        {
            "state": "Maharashtra",
            "city": "Mumbai",
            "phone_whatsapp": "919999999999",
            "address": "123 Demo Street",
        },
        name="Demo Children’s Clinic",
    )

    doctor = add_if_missing(
        db,
        models.User,
        {
            "role": models.UserRole.DOCTOR,
            "clinic_id": clinic.id,
            "phone_e164": "919999999998",
            "display_name": "Dr Demo",
            "email": "demo@clinic.test",
        },
        google_sub="demo-google-sub",
    )

    # 3) red-flag & videos --------------------------------------------------
    rf = add_if_missing(
        db,
        models.RedFlag,
        {
            "name_en": "Purpuric rash",
            "ataglance_en": "Could indicate meningococcemia—needs urgent review.",
            "mini_cme_vimeo": "https://vimeo.com/123456",
            "long_cme_vimeo": None,
            "references_json": {"1": "Nelson Textbook of Pediatrics, 22e"},
        },
        slug="purpuric_rash",
    )

    # 4) form ---------------------------------------------------------------
    form = add_if_missing(
        db,
        models.Form,
        {
            "version": "1",
            "is_active": True,
            "title_en": "Rash on Body",
            "description_en": "Use when a child presents with a body rash.",
        },
        slug="rash_body",
    )

    # 5) question -----------------------------------------------------------
    q = add_if_missing(
        db,
        models.Question,
        {
            "form_id": form.id,
            "order_idx": 1,
        },
        question_key="rash_color",
    )

    add_if_missing(
        db,
        models.QuestionLocalised,
        {"text": "What colour is the rash?"},
        question_id=q.id,
        lang_code=en.code,
    )

    # 6) two options --------------------------------------------------------
    opt1 = add_if_missing(
        db,
        models.Option,
        {
            "question_id": q.id,
            "order_idx": 1,
            "is_redflag": False,
            "redflag_id": None,
        },
        option_key="red",
    )
    add_if_missing(
        db,
        models.OptionLocalised,
        {"text": "Red / pink"},
        option_id=opt1.id,
        lang_code=en.code,
    )

    opt2 = add_if_missing(
        db,
        models.Option,
        {
            "question_id": q.id,
            "order_idx": 2,
            "is_redflag": True,
            "redflag_id": rf.id,
        },
        option_key="purpuric",
    )
    add_if_missing(
        db,
        models.OptionLocalised,
        {"text": "Purplish or bruised (purpura)"},
        option_id=opt2.id,
        lang_code=en.code,
    )

    db.close()
    print("✓ Sample data inserted.")


if __name__ == "__main__":
    main()