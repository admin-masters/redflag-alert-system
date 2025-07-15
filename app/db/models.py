# app/db/models.py
from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Enum, ForeignKey, Index, UniqueConstraint,
    Boolean, Column, DateTime, Integer, String, Text, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase): ...


# ---------- simple enums ----------
class UserRole(str, enum.Enum):
    DOCTOR = "doctor"
    STAFF = "staff"
    ADMIN = "admin"


class VideoHost(str, enum.Enum):
    VIMEO = "vimeo"
    YOUTUBE = "youtube"


class VideoType(str, enum.Enum):
    MINI_CME = "mini_cme"
    LONG_CME = "long_cme"
    PATIENT = "patient"


# ---------- core tables ----------
class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(60))
    city: Mapped[str] = mapped_column(String(60))
    phone_whatsapp: Mapped[str] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)

    users: Mapped[list["User"]] = relationship(back_populates="clinic")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"))
    phone_e164: Mapped[str] = mapped_column(String(20))
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))

    clinic: Mapped["Clinic"] = relationship(back_populates="users")


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)
    native_name: Mapped[str] = mapped_column(String(60))


class Form(Base):
    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    version: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    title_en: Mapped[str] = mapped_column(String(120))
    description_en: Mapped[str] = mapped_column(Text)
    questions: Mapped[list["Question"]] = relationship(
        back_populates="form",
        cascade="all, delete-orphan",
        order_by="Question.order_idx",
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("form_id", "order_idx", name="uq_question_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"))
    order_idx: Mapped[int] = mapped_column(Integer)
    question_key: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,  # ← was False
        unique=False  # drop any uniqueness you may have added
    )

    form: Mapped["Form"] = relationship(back_populates="questions")

    # one question ↔ many options
    options: Mapped[list["Option"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.order_idx",
    )

    # localised copies
    localisations: Mapped[list["QuestionLocalised"]] = relationship(
        cascade="all, delete-orphan"
    )


class QuestionLocalised(Base):
    __tablename__ = "question_localised"
    __table_args__ = (
        UniqueConstraint("question_id", "lang_code", name="uq_q_loc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    lang_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    text: Mapped[str] = mapped_column(Text)


class Option(Base):
    __tablename__ = "options"
    __table_args__ = (
        UniqueConstraint("question_id", "order_idx", name="uq_opt_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    order_idx: Mapped[int] = mapped_column(Integer)
    option_key: Mapped[str] = mapped_column(String(64))
    is_redflag: Mapped[bool] = mapped_column(Boolean, default=False)
    redflag_id: Mapped[Optional[int]] = mapped_column(ForeignKey("redflags.id"))

    redflag: Mapped[Optional["RedFlag"]] = relationship()

    question: Mapped["Question"] = relationship(back_populates="options")
    localisations: Mapped[list["OptionLocalised"]] = relationship(
        cascade="all, delete-orphan"
    )


class OptionLocalised(Base):
    __tablename__ = "option_localised"
    __table_args__ = (
        UniqueConstraint("option_id", "lang_code", name="uq_opt_loc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    option_id: Mapped[int] = mapped_column(ForeignKey("options.id"))
    lang_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    text: Mapped[str] = mapped_column(Text)


class RedFlag(Base):
    __tablename__ = "redflags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name_en: Mapped[str] = mapped_column(String(120))
    ataglance_en: Mapped[str] = mapped_column(Text)
    # inline fallback links (used if not normalised in redflag_videos)
    mini_cme_vimeo: Mapped[Optional[str]] = mapped_column(String(255))
    long_cme_vimeo: Mapped[Optional[str]] = mapped_column(String(255))
    references_json: Mapped[Optional[dict]] = mapped_column(JSON)


class RedFlagLocalised(Base):
    __tablename__ = "redflag_localised"
    __table_args__ = (
        UniqueConstraint("redflag_id", "lang_code", name="uq_rf_loc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    redflag_id: Mapped[int] = mapped_column(ForeignKey("redflags.id"))
    lang_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    name: Mapped[str] = mapped_column(String(120))
    ataglance_text: Mapped[str] = mapped_column(Text)
    patient_video_youtube: Mapped[Optional[str]] = mapped_column(String(255))


# ---------- references & videos ----------
class Reference(Base):
    __tablename__ = "references"

    id: Mapped[int] = mapped_column(primary_key=True)
    citation_text: Mapped[str] = mapped_column(Text)
    doi_or_url: Mapped[str] = mapped_column(String(512))


class RedFlagReference(Base):
    __tablename__ = "redflag_references"
    __table_args__ = (
        UniqueConstraint("redflag_id", "reference_id", name="uq_rf_ref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    redflag_id: Mapped[int] = mapped_column(ForeignKey("redflags.id"))
    reference_id: Mapped[int] = mapped_column(ForeignKey("references.id"))


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[VideoHost] = mapped_column(Enum(VideoHost))
    video_id: Mapped[str] = mapped_column(String(64))
    title_en: Mapped[str] = mapped_column(String(255))
    duration_sec: Mapped[int] = mapped_column(Integer)


class RedFlagVideo(Base):
    __tablename__ = "redflag_videos"
    __table_args__ = (
        UniqueConstraint("redflag_id", "video_id", "type", name="uq_rf_video"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    redflag_id: Mapped[int] = mapped_column(ForeignKey("redflags.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    type: Mapped[VideoType] = mapped_column(Enum(VideoType))


# ---------- patient flow ----------
class PatientSession(Base):
    __tablename__ = "patient_sessions"
    __table_args__ = (
        Index("ix_patient_day", "patient_phone_e164", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clinic_id: Mapped[int] = mapped_column(ForeignKey("clinics.id"))
    patient_phone_e164: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class FormSubmission(Base):
    __tablename__ = "form_submissions"
    __table_args__ = (
        Index("ix_session_day", "session_id", "submitted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("patient_sessions.id"))
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    lang_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("form_submissions.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    option_key: Mapped[str] = mapped_column(String(64))


class SubmissionRedFlag(Base):
    __tablename__ = "submission_redflags"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("form_submissions.id"))
    redflag_id: Mapped[int] = mapped_column(ForeignKey("redflags.id"))