from backend.app.db.database import Base, engine

from backend.app.models.product import Product
from backend.app.models.analysis import Analysis
from backend.app.models.agent_output import AgentOutput
from backend.app.models.user import User


def init_db():
    Base.metadata.create_all(bind=engine)