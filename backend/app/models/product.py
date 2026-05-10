from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from backend.app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    url = Column(String, nullable=True)
    seller_name = Column(String, nullable=True)
    source_platform = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())