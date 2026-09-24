from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()


class Feature(Base):

    __tablename__ = "features"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    geometry_type = Column(
        String,
        nullable=False
    )

    geometry = Column(
        Text,
        nullable=False
    )

    name = Column(
        String,
        nullable=False
    )

    asset_type = Column(
        String,
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    status = Column(
        String,
        default="Active"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )