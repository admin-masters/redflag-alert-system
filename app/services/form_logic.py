# app/services/form_logic.py
"""
Shared logic for loading a form + evaluating answers against red-flag rules.
This MVP version covers:
• fetch-by-slug
• localisation of questions/options
• evaluate() → list[RedFlag]   (empty list if none)
"""

from typing import Dict, List
from sqlalchemy.orm import Session, joinedload

from app.db import models


class FormPack:
    """Bundle of metadata, questions, and rules for a single form."""

    def __init__(self, meta: models.Form, questions: list[models.Question]):
        self.meta = meta
        self.questions = questions

        # Build quick look-ups
        self.q_by_key = {q.question_key: q for q in questions}
        self.rule_lookup: Dict[str, models.RedFlag | None] = {}

        for q in questions:
            for opt in q.options:  # option relationship set below
                key = f"{q.question_key}:{opt.option_key}"
                self.rule_lookup[key] = opt.redflag  # may be None

    # --------------------------------------------------------------------- #
    # Static constructors
    # --------------------------------------------------------------------- #
    @staticmethod
    def by_slug(db: Session, slug: str) -> "FormPack":
        meta: models.Form = (
            db.query(models.Form)
            .filter(models.Form.slug == slug, models.Form.is_active.is_(True))
            .options(
                joinedload(models.Form.questions)
                .joinedload(models.Question.options)
                .joinedload(models.Option.redflag)
            )
            .one_or_none()
        )
        if meta is None:
            raise ValueError(f"Form slug '{slug}' not found")

        return FormPack(meta, meta.questions)

    # --------------------------------------------------------------------- #
    # Localisation helpers
    # --------------------------------------------------------------------- #
    def localised(self, lang: str = "EN") -> list[dict]:
        """
        Returns a list of dicts → [{ text, question_key, options:[{text, option_key}] }]
        """
        out = []
        for q in sorted(self.questions, key=lambda x: x.order_idx):
            qloc = next(
                (l for l in q.localisations if l.lang_code == lang), None
            )
            q_text = qloc.text if qloc else q.question_key  # fallback

            opts = []
            for opt in sorted(q.options, key=lambda x: x.order_idx):
                oloc = next(
                    (l for l in opt.localisations if l.lang_code == lang), None
                )
                opt_text = oloc.text if oloc else opt.option_key
                opts.append(
                    {
                        "option_key": opt.option_key,
                        "text": opt_text,
                        "is_redflag": opt.is_redflag,
                    }
                )

            out.append(
                {
                    "question_key": q.question_key,
                    "text": q_text,
                    "options": opts,
                }
            )
        return out

    # --------------------------------------------------------------------- #
    # Evaluation
    # --------------------------------------------------------------------- #
    def evaluate(self, answers: Dict[str, str]) -> List[models.RedFlag]:
        """answers = {question_key: option_key}"""
        triggered: list[models.RedFlag] = []
        for q_key, opt_key in answers.items():
            rf = self.rule_lookup.get(f"{q_key}:{opt_key}")
            if rf is not None and rf not in triggered:
                triggered.append(rf)
        return triggered