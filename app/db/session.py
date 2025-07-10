# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.settings import db_url

engine = create_engine(db_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and guarantees close/rollback.
    """
    db = SessionLocal()
    try:
        yield db                # <-- FastAPI gets a real Session here
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()