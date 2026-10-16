"""Building persistence mappings. Versioned SQL owns schema creation/migrations."""

from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Campus(SQLModel, table=True):
    __tablename__ = "campuses"
    __table_args__ = {"schema": "public"}
    id: str = Field(primary_key=True, max_length=128)
    name: str = Field(max_length=200)


class Building(SQLModel, table=True):
    __tablename__ = "buildings"
    __table_args__ = {"schema": "public"}
    id: str = Field(primary_key=True, max_length=128)
    campus_id: str = Field(foreign_key="public.campuses.id", max_length=128)
    name: str = Field(max_length=200)
    category: str = Field(max_length=64)
    description: str | None = None
    latitude: float
    longitude: float
    step_free_entrance: str = "unknown"
    accessible_toilet: str = "unknown"
    designated_parking: str = "unknown"


class PlaceDetailRecord(SQLModel, table=True):
    """Read-only view mapping; never call metadata.create_all for this view."""
    __tablename__ = "place_detail_records"
    __table_args__ = {"schema": "public"}
    id: str = Field(primary_key=True, max_length=128)
    campus_id: str = Field(max_length=128)
    record: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
