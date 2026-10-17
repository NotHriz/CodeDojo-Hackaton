"""Signed-in contributions; clients cannot set identity, weights, or status."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request

from app.routers.auth import CurrentUser
from app.schemas import ErrorResponse
from app.services.community import (
    ClearanceCreate, ClearanceResponse, ContributionDenied, ContributionTargetMissing, IdempotencyConflict,
    InvalidObservationTime, PolicyConflict, PolicyUnavailable,
    ReportCreate, ReportHistoryResponse, ReportListResponse, ReportResponse, VoteInput, eligible_weight,
    utc_now, validate_observation_time,
)

router = APIRouter(prefix="/reports", tags=["community"], responses={
    status: {"model": ErrorResponse} for status in (401, 403, 404, 409, 422, 429, 503)
})


def repository(request: Request):
    adapter = request.app.state.community_repository
    if adapter is None:
        raise HTTPException(503, "Community data is not connected yet.")
    return adapter


def get_record(adapter, report_id):
    record = adapter.get_report(report_id)
    if record is None or record.public.campus_id != "iium-gombak":
        raise HTTPException(404, "Report not found.")
    return record


def contribution(request: Request, adapter, user_id, *, voting=False):
    policy = request.app.state.trust_policy
    if voting and policy is None:
        raise HTTPException(503, "Community verification policy awaits review.")
    try:
        weight = eligible_weight(adapter.get_contributor(user_id), policy)
    except ContributionDenied:
        raise HTTPException(403, "Contributions are temporarily restricted for this account.") from None
    budget = request.app.state.contribution_budget
    if not budget.reserve(str(user_id)):
        raise HTTPException(429, "Contribution request limit reached. Please retry later.", headers={"Retry-After": str(budget.retry_after())})
    return weight, policy


def mutate(operation):
    try:
        return operation()
    except IdempotencyConflict:
        raise HTTPException(409, "This submission key was already used for different content.") from None
    except ContributionDenied:
        # The adapter rechecks restrictions/self-votes inside the transaction.
        raise HTTPException(403, "This contribution is not permitted.") from None
    except ContributionTargetMissing:
        raise HTTPException(404, "Contribution target not found.") from None
    except InvalidObservationTime:
        raise HTTPException(422, "Observation time is invalid for this event.") from None
    except PolicyUnavailable:
        raise HTTPException(503, "Community verification policy and version await configuration.") from None
    except PolicyConflict:
        raise HTTPException(409, "This report requires a reviewed policy migration before further voting.") from None


@router.get("", response_model=ReportListResponse)
def list_reports(
    request: Request,
    place_id: Annotated[str, Query(min_length=1, max_length=128)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    adapter = repository(request)
    records = [record.public for record in adapter.list_reports(place_id) if record.public.campus_id == "iium-gombak" and record.public.place_id == place_id]
    records.sort(key=lambda record: (record.submitted_at, str(record.id)), reverse=True)
    return ReportListResponse(items=records[offset:offset + limit], total=len(records), limit=limit, offset=offset)


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: UUID, request: Request):
    return get_record(repository(request), report_id).public


@router.get("/{report_id}/history", response_model=ReportHistoryResponse)
def report_history(
    report_id: UUID, request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    adapter = repository(request)
    get_record(adapter, report_id)
    events = [event for event in adapter.list_history(report_id) if event.report_id == report_id]
    # Stable sorting retains the repository's sequence order for equal times.
    events.sort(key=lambda event: event.occurred_at)
    return ReportHistoryResponse(items=events[offset:offset + limit], total=len(events), limit=limit, offset=offset)


@router.post("", response_model=ReportResponse, status_code=201)
def create_report(
    body: ReportCreate, request: Request, user: CurrentUser,
    key: Annotated[UUID, Header(alias="Idempotency-Key")],
):
    adapter = repository(request)
    contribution(request, adapter, user.id)
    places = request.app.state.place_repository
    if places is None:
        raise HTTPException(503, "Building data is not connected yet.")
    place = places.get_place(body.place_id)
    if place is None or place.campus_id != "iium-gombak":
        raise HTTPException(404, "Building not found.")
    now = utc_now()
    if not validate_observation_time(body.observed_at, now):
        raise HTTPException(422, "Observation time cannot be in the future.")
    return mutate(lambda: adapter.create_report(user.id, body, now, key)).public


@router.post("/{report_id}/votes", response_model=ReportResponse)
def vote(report_id: UUID, body: VoteInput, request: Request, user: CurrentUser):
    adapter = repository(request)
    record = get_record(adapter, report_id)
    if record.author_id == user.id:
        raise HTTPException(403, "You cannot vote on your own report.")
    weight, policy = contribution(request, adapter, user.id, voting=True)
    return mutate(lambda: adapter.cast_vote(report_id, user.id, body.stance, weight, policy)).public


@router.post("/{report_id}/clearance-observations", response_model=ClearanceResponse, status_code=201)
def clearance(
    report_id: UUID, body: ClearanceCreate, request: Request, user: CurrentUser,
    key: Annotated[UUID, Header(alias="Idempotency-Key")],
):
    adapter = repository(request)
    report = get_record(adapter, report_id)
    contribution(request, adapter, user.id)
    now = utc_now()
    if not validate_observation_time(body.observed_at, now) or body.observed_at < report.public.observed_at:
        raise HTTPException(422, "Clearing observations must follow the reported event and cannot be in the future.")
    return mutate(lambda: adapter.create_clearance(report_id, user.id, body, now, key)).public


@router.post("/{report_id}/clearance-observations/{clearance_id}/votes", response_model=ReportResponse)
def clearance_vote(report_id: UUID, clearance_id: UUID, body: VoteInput, request: Request, user: CurrentUser):
    adapter = repository(request)
    get_record(adapter, report_id)
    observation = adapter.get_clearance(report_id, clearance_id)
    if observation is None or observation.report_id != report_id:
        raise HTTPException(404, "Clearing observation not found.")
    if observation.author_id == user.id:
        raise HTTPException(403, "You cannot vote on your own clearing observation.")
    weight, policy = contribution(request, adapter, user.id, voting=True)
    return mutate(lambda: adapter.cast_clearance_vote(report_id, clearance_id, user.id, body.stance, weight, policy)).public
