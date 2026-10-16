"""Building persistence mappings. Versioned SQL owns schema creation/migrations."""

from typing import Any
from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, Numeric
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


class ReportPublicRecord(SQLModel, table=True):
    """Read-only DTO projection; author IDs require a separate private lookup."""
    __tablename__ = "report_public_records"
    __table_args__ = {"schema": "public"}
    id: UUID = Field(primary_key=True)
    building_id: str
    campus_id: str
    submitted_at: datetime
    record: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))


class ClearancePublicRecord(SQLModel, table=True):
    """Read-only DTO projection, scoped to its parent report."""
    __tablename__ = "clearance_public_records"
    __table_args__ = {"schema": "public"}
    id: UUID = Field(primary_key=True)
    report_id: UUID
    submitted_at: datetime
    record: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))


class ReportHistoryRecord(SQLModel, table=True):
    """Read-only history projection; sequence orders equal-time events."""
    __tablename__ = "report_history_records"
    __table_args__ = {"schema": "public"}
    id: UUID = Field(primary_key=True)
    report_id: UUID
    campus_id: str
    occurred_at: datetime
    sequence: int
    record: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))


class ContributorStateRecord(SQLModel, table=True):
    """Private eligibility storage, never a public response model."""
    __tablename__ = "contributor_state"
    __table_args__ = {"schema": "public"}
    user_id: UUID = Field(primary_key=True)
    can_contribute: bool = True
    vote_weight: float = Field(default=1.0, sa_column=Column(Numeric(asdecimal=False), nullable=False))
    restriction_reason: str | None = None
    updated_at: datetime
