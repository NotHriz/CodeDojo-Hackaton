"""Public foundation/building DTOs; see contracts/places.md for the handoff."""

from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["akses-campus-api"] = "akses-campus-api"


class APIError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: APIError


class FacilityValue(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class Facilities(BaseModel):
    step_free_entrance: FacilityValue = FacilityValue.UNKNOWN
    accessible_toilet: FacilityValue = FacilityValue.UNKNOWN
    designated_parking: FacilityValue = FacilityValue.UNKNOWN


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ActiveWarning(BaseModel):
    report_id: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=2000)
    status: Literal["unverified", "community_corroborated", "disputed"]
    observed_at: AwareDatetime | None = None


class Entrance(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    coordinates: Coordinates | None = None
    photo_urls: list[HttpUrl] = Field(default_factory=list)


class FacilityObservation(BaseModel):
    facility: Literal["step_free_entrance", "accessible_toilet", "designated_parking"]
    value: FacilityValue
    observed_at: AwareDatetime | None = None
    source: str | None = None
    notes: str | None = None
    evidence_urls: list[HttpUrl] = Field(default_factory=list)


class PlaceSummary(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    campus_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=64)
    coordinates: Coordinates
    facilities: Facilities = Field(default_factory=Facilities)
    active_warnings: list[ActiveWarning] = Field(default_factory=list)
    is_demo: bool = False


class PlaceDetail(PlaceSummary):
    description: str | None = None
    entrances: list[Entrance] = Field(default_factory=list)
    observations: list[FacilityObservation] = Field(default_factory=list)


class PlaceListResponse(BaseModel):
    data_mode: Literal["live", "demo"] = "live"
    items: list[PlaceSummary]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
