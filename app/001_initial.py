"""Initial tables for Inditech RFA v1

Revision ID: 001_initial
Revises:
Create Date: 2025-07-05

"""
from alembic import op
import sqlalchemy as sa
import enum


# --- helpers ---
userrole = sa.Enum("doctor", "staff", "admin", name="userrole")
videohost = sa.Enum("vimeo", "youtube", name="videohost")
videotype = sa.Enum("mini_cme", "long_cme", "patient", name="videotype")


def upgrade() -> None:
    userrole.create(op.get_bind(), checkfirst=True)
    videohost.create(op.get_bind(), checkfirst=True)
    videotype.create(op.get_bind(), checkfirst=True)

    # clinics & users ---------------------------------------------------------
    op.create_table(
        "clinics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120)),
        sa.Column("state", sa.String(60)),
        sa.Column("city", sa.String(60)),
        sa.Column("phone_whatsapp", sa.String(20)),
        sa.Column("address", sa.Text),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("google_sub", sa.String(255), unique=True),
        sa.Column("role", userrole, nullable=False),
        sa.Column("clinic_id", sa.Integer, sa.ForeignKey("clinics.id")),
        sa.Column("phone_e164", sa.String(20)),
        sa.Column("display_name", sa.String(120)),
        sa.Column("email", sa.String(255)),
    )

    # languages ---------------------------------------------------------------
    op.create_table(
        "languages",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("native_name", sa.String(60)),
    )

    # forms + questions -------------------------------------------------------
    op.create_table(
        "forms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(60), unique=True),
        sa.Column("version", sa.String(20)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("title_en", sa.String(120)),
        sa.Column("description_en", sa.Text),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("forms.id")),
        sa.Column("order_idx", sa.Integer),
        sa.Column("question_key", sa.String(64)),
        sa.UniqueConstraint("form_id", "order_idx", name="uq_question_order"),
    )

    op.create_table(
        "question_localised",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id")),
        sa.Column("lang_code", sa.String(8), sa.ForeignKey("languages.code")),
        sa.Column("text", sa.Text),
        sa.UniqueConstraint("question_id", "lang_code", name="uq_q_loc"),
    )

    # options -----------------------------------------------------------------
    op.create_table(
        "options",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id")),
        sa.Column("order_idx", sa.Integer),
        sa.Column("option_key", sa.String(64)),
        sa.Column("is_redflag", sa.Boolean, default=False),
        sa.Column("redflag_id", sa.Integer, sa.ForeignKey("redflags.id")),
        sa.UniqueConstraint("question_id", "order_idx", name="uq_opt_order"),
    )

    op.create_table(
        "option_localised",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("option_id", sa.Integer, sa.ForeignKey("options.id")),
        sa.Column("lang_code", sa.String(8), sa.ForeignKey("languages.code")),
        sa.Column("text", sa.Text),
        sa.UniqueConstraint("option_id", "lang_code", name="uq_opt_loc"),
    )

    # redflags / references / videos -----------------------------------------
    op.create_table(
        "redflags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(64), unique=True),
        sa.Column("name_en", sa.String(120)),
        sa.Column("ataglance_en", sa.Text),
        sa.Column("mini_cme_vimeo", sa.String(255)),
        sa.Column("long_cme_vimeo", sa.String(255)),
        sa.Column("references_json", sa.JSON),
    )

    op.create_table(
        "redflag_localised",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("redflag_id", sa.Integer, sa.ForeignKey("redflags.id")),
        sa.Column("lang_code", sa.String(8), sa.ForeignKey("languages.code")),
        sa.Column("name", sa.String(120)),
        sa.Column("ataglance_text", sa.Text),
        sa.Column("patient_video_youtube", sa.String(255)),
        sa.UniqueConstraint("redflag_id", "lang_code", name="uq_rf_loc"),
    )

    op.create_table(
        "references",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("citation_text", sa.Text),
        sa.Column("doi_or_url", sa.String(512)),
    )

    op.create_table(
        "redflag_references",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("redflag_id", sa.Integer, sa.ForeignKey("redflags.id")),
        sa.Column("reference_id", sa.Integer, sa.ForeignKey("references.id")),
        sa.UniqueConstraint("redflag_id", "reference_id", name="uq_rf_ref"),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("host", videohost, nullable=False),
        sa.Column("video_id", sa.String(64)),
        sa.Column("title_en", sa.String(255)),
        sa.Column("duration_sec", sa.Integer),
    )

    op.create_table(
        "redflag_videos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("redflag_id", sa.Integer, sa.ForeignKey("redflags.id")),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("videos.id")),
        sa.Column("type", videotype, nullable=False),
        sa.UniqueConstraint("redflag_id", "video_id", "type", name="uq_rf_video"),
    )

    # patient flow ------------------------------------------------------------
    op.create_table(
        "patient_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("clinic_id", sa.Integer, sa.ForeignKey("clinics.id")),
        sa.Column("patient_phone_e164", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patient_day", "patient_sessions",
                    ["patient_phone_e164", "created_at"])

    op.create_table(
        "form_submissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("patient_sessions.id")),
        sa.Column("form_id", sa.Integer, sa.ForeignKey("forms.id")),
        sa.Column("lang_code", sa.String(8), sa.ForeignKey("languages.code")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_session_day", "form_submissions",
                    ["session_id", "submitted_at"])

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submission_id", sa.Integer, sa.ForeignKey("form_submissions.id")),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id")),
        sa.Column("option_key", sa.String(64)),
    )

    op.create_table(
        "submission_redflags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("submission_id", sa.Integer, sa.ForeignKey("form_submissions.id")),
        sa.Column("redflag_id", sa.Integer, sa.ForeignKey("redflags.id")),
    )


def downgrade() -> None:
    op.drop_table("submission_redflags")
    op.drop_table("answers")
    op.drop_index("ix_session_day", table_name="form_submissions")
    op.drop_table("form_submissions")
    op.drop_index("ix_patient_day", table_name="patient_sessions")
    op.drop_table("patient_sessions")
    op.drop_table("redflag_videos")
    op.drop_table("videos")
    op.drop_table("redflag_references")
    op.drop_table("references")
    op.drop_table("redflag_localised")
    op.drop_table("redflags")
    op.drop_table("option_localised")
    op.drop_table("options")
    op.drop_table("question_localised")
    op.drop_table("questions")
    op.drop_table("forms")
    op.drop_table("languages")
    op.drop_table("users")
    op.drop_table("clinics")
    videotype.drop(op.get_bind(), checkfirst=True)
    videohost.drop(op.get_bind(), checkfirst=True)
    userrole.drop(op.get_bind(), checkfirst=True)