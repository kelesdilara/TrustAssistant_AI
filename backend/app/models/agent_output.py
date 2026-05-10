from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from backend.app.db.database import Base


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    output_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())