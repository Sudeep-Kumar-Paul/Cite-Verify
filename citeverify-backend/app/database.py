from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")
engine_kwargs = {"echo": settings.debug}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(db_url, **engine_kwargs)

# Enable WAL mode for SQLite for better concurrency
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from app.models import document, claim, citation, source, verification  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Safe migration check for existing SQLite tables
    if is_sqlite:
        try:
            with engine.connect() as conn:
                # Check user_id in documents
                res = conn.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
                doc_cols = [c[1] for c in res]
                if "user_id" not in doc_cols:
                    conn.exec_driver_sql("ALTER TABLE documents ADD COLUMN user_id VARCHAR(128)")
                    conn.commit()

                # Check matching_status in citations
                cit_res = conn.exec_driver_sql("PRAGMA table_info(citations)").fetchall()
                cit_cols = [c[1] for c in cit_res]
                if "matching_status" not in cit_cols:
                    conn.exec_driver_sql("ALTER TABLE citations ADD COLUMN matching_status VARCHAR(50)")
                    conn.commit()
        except Exception as e:
            logger.warning(f"Database migration check notice: {e}")

    logger.info("Database tables created/verified.")
