import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db import database

from backend.app.models.product import Product
from backend.app.models.analysis import Analysis
from backend.app.models.agent_output import AgentOutput
from backend.app.models.user import User

logger = logging.getLogger(__name__)


def init_db() -> bool:
    try:
        database.Base.metadata.create_all(bind=database.engine)
        _run_lightweight_migrations(database.engine)
        return True
    except SQLAlchemyError as exc:
        logger.warning("Primary database unavailable, using SQLite fallback: %s", exc)
        fallback_engine = database.activate_sqlite_fallback()
        database.Base.metadata.create_all(bind=fallback_engine)
        _run_lightweight_migrations(fallback_engine)
        return True


def _run_lightweight_migrations(engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("analyses"):
        return

    analysis_columns = {column["name"] for column in inspector.get_columns("analyses")}

    pending = []
    if "user_id" not in analysis_columns:
        pending.append("ALTER TABLE analyses ADD COLUMN user_id INTEGER")
    if "analysis_payload" not in analysis_columns:
        pending.append("ALTER TABLE analyses ADD COLUMN analysis_payload JSON")

    for sql in pending:
        try:
            with engine.begin() as connection:
                connection.execute(text(sql))
        except SQLAlchemyError as exc:
            logger.warning("Migration skipped (already applied): %s", exc)
