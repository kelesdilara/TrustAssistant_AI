from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.app.core.config import settings


SQLITE_FALLBACK_PATH = Path(__file__).resolve().parents[1] / "trustassistant_local.db"


def _create_primary_engine():
    return create_engine(settings.database_url, pool_pre_ping=True)


def _create_sqlite_fallback_engine():
    return create_engine(
        f"sqlite:///{SQLITE_FALLBACK_PATH}",
        connect_args={"check_same_thread": False},
    )


engine = _create_primary_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def activate_sqlite_fallback():
    global engine
    engine = _create_sqlite_fallback_engine()
    SessionLocal.configure(bind=engine)
    return engine


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
