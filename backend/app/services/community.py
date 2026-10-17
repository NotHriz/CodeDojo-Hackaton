"""Contribution contracts and deterministic, explicitly configured trust rules."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from math import isfinite
from typing import Literal, Protocol, Sequence
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ContributionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(min_length=1, max_length=2000)
    observed_at: AwareDatetime
    evidence_urls: list[HttpUrl] = Field(default_factory=list, max_length=3)

    @field_validator("description")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Describe the observation.")
        return value.strip()


class ReportCreate(ContributionInput):
    place_id: str = Field(min_length=1, max_length=128)
    barrier_type: str = Field(min_length=1, max_length=64)

    @field_validator("barrier_type")
    @classmethod
    def nonblank_type(cls, value):
        if not value.strip():
            raise ValueError("Specify a barrier type.")
        return value.strip()


class ClearanceCreate(ContributionInput):
    pass


class VoteStance(StrEnum):
    CORROBORATE = "corroborate"
    DISPUTE = "dispute"


class VoteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stance: VoteStance


class ReportStatus(StrEnum):
    UNVERIFIED = "unverified"
    CORROBORATED = "community_corroborated"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class CommunityCounts(BaseModel):
    supporters: int = Field(default=0, ge=0)
    disputes: int = Field(default=0, ge=0)


class ClearanceResponse(BaseModel):
    id: UUID
    description: str
    observed_at: AwareDatetime
    submitted_at: AwareDatetime
    evidence_urls: list[HttpUrl] = Field(default_factory=list)
    status: ReportStatus = ReportStatus.UNVERIFIED
    community: CommunityCounts = Field(default_factory=CommunityCounts)


class ReportResponse(BaseModel):
    id: UUID
    place_id: str
    campus_id: str
    barrier_type: str
    description: str
    observed_at: AwareDatetime
    submitted_at: AwareDatetime
    evidence_urls: list[HttpUrl] = Field(default_factory=list)
    status: ReportStatus = ReportStatus.UNVERIFIED
    community: CommunityCounts = Field(default_factory=CommunityCounts)
    clearance_observations: list[ClearanceResponse] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    limit: int
    offset: int


class ReportEventResponse(BaseModel):
    id: UUID
    report_id: UUID
    occurred_at: AwareDatetime
    action: Literal["report_created", "vote_updated", "clearance_submitted", "clearance_vote_updated"]
    previous_status: ReportStatus | None = None
    new_status: ReportStatus
    community: CommunityCounts = Field(default_factory=CommunityCounts)


class ReportHistoryResponse(BaseModel):
    items: list[ReportEventResponse]
    total: int
    limit: int
    offset: int


class TrustPolicy(BaseModel):
    """No active defaults: reviewers must choose an explicit experimental policy."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)
    minimum_supporters: int = Field(ge=2, le=20)
    minimum_weight: float = Field(gt=0, le=40)
    support_ratio: float = Field(gt=0.5, le=1)
    maximum_vote_weight: float = Field(ge=1, le=2)


@dataclass(frozen=True)
class VoteSnapshot:
    voter_id: UUID
    stance: VoteStance
    weight: float


@dataclass(frozen=True)
class ContributorState:
    can_contribute: bool = True
    vote_weight: float = 1.0


@dataclass(frozen=True)
class ReportRecord:
    public: ReportResponse
    author_id: UUID


@dataclass(frozen=True)
class ClearanceRecord:
    public: ClearanceResponse
    author_id: UUID
    report_id: UUID


class IdempotencyConflict(Exception):
    pass


class ContributionDenied(Exception):
    pass


class ContributionTargetMissing(Exception):
    pass


class InvalidObservationTime(Exception):
    pass


class PolicyUnavailable(Exception):
    pass


class PolicyConflict(Exception):
    pass


class CommunityRepository(Protocol):
    """Persistence handoff; mutation methods MUST enforce the atomic rules in docs."""

    def get_contributor(self, user_id: UUID) -> ContributorState | None: ...
    def get_report(self, report_id: UUID) -> ReportRecord | None: ...
    def list_reports(self, place_id: str) -> Sequence[ReportRecord]: ...
    def list_history(self, report_id: UUID) -> Sequence[ReportEventResponse]: ...
    def create_report(self, author_id: UUID, body: ReportCreate, submitted_at: datetime, key: UUID) -> ReportRecord: ...
    def cast_vote(self, report_id: UUID, voter_id: UUID, stance: VoteStance, weight: float, policy: TrustPolicy) -> ReportRecord: ...
    def create_clearance(self, report_id: UUID, author_id: UUID, body: ClearanceCreate, submitted_at: datetime, key: UUID) -> ClearanceRecord: ...
    def get_clearance(self, report_id: UUID, clearance_id: UUID) -> ClearanceRecord | None: ...
    def cast_clearance_vote(self, report_id: UUID, clearance_id: UUID, voter_id: UUID, stance: VoteStance, weight: float, policy: TrustPolicy) -> ReportRecord: ...


def eligible_weight(state: ContributorState | None, policy: TrustPolicy | None) -> float:
    state = state if state is not None else ContributorState()
    if not state.can_contribute:
        raise ContributionDenied()
    if not isfinite(state.vote_weight) or state.vote_weight <= 0:
        raise ValueError("Invalid private voting weight.")
    # New accounts are neutral, and score-based advantage is always bounded.
    return min(max(1.0, state.vote_weight), policy.maximum_vote_weight if policy else 1.0)


def validate_observation_time(observed_at: datetime, now: datetime) -> bool:
    return observed_at <= now + timedelta(minutes=5)


def aggregate_votes(votes: Sequence[VoteSnapshot], *, author_id: UUID, policy: TrustPolicy) -> tuple[ReportStatus, CommunityCounts]:
    seen = set()
    supporters = disputes = 0
    support_weight = dispute_weight = 0.0
    for vote in votes:
        if vote.voter_id == author_id or vote.voter_id in seen:
            raise ValueError("Votes must be distinct and cannot include the author.")
        if not isfinite(vote.weight) or vote.weight <= 0:
            raise ValueError("Invalid vote snapshot.")
        seen.add(vote.voter_id)
        weight = min(max(vote.weight, 1.0), policy.maximum_vote_weight)
        if vote.stance == VoteStance.CORROBORATE:
            supporters += 1
            support_weight += weight
        elif vote.stance == VoteStance.DISPUTE:
            disputes += 1
            dispute_weight += weight
        else:
            raise ValueError("Invalid vote stance.")
    counts = CommunityCounts(supporters=supporters, disputes=disputes)
    total_weight = support_weight + dispute_weight
    if (
        supporters >= policy.minimum_supporters
        and support_weight >= policy.minimum_weight
        and total_weight > 0
        and support_weight / total_weight >= policy.support_ratio
    ):
        return ReportStatus.CORROBORATED, counts
    if disputes:
        return ReportStatus.DISPUTED, counts
    return ReportStatus.UNVERIFIED, counts


def derive_report_status(votes: Sequence[VoteSnapshot], *, author_id: UUID, policy: TrustPolicy, clearance_states: Sequence[ReportStatus] = ()) -> tuple[ReportStatus, CommunityCounts]:
    status, counts = aggregate_votes(votes, author_id=author_id, policy=policy)
    # A later clearing event is independent of whether the original report was true.
    if ReportStatus.CORROBORATED in clearance_states:
        return ReportStatus.RESOLVED, counts
    return status, counts


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
