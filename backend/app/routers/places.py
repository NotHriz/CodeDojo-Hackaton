"""Public building discovery; persistence is injected by the app composition root."""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request

from app.routers.auth import CurrentUser
from app.schemas import ErrorResponse, ObservationCreate, PlaceDetail, PlaceListResponse
from app.services.places import PlaceRepository, search_places
from app.services.postgres_places import ObservationIdempotencyConflict, ObservationTargetMissing

router = APIRouter(prefix="/places", tags=["places"])


def get_place_repository(request: Request) -> PlaceRepository:
    repository = request.app.state.place_repository
    if repository is None:
        raise HTTPException(
            status_code=503,
            detail="Building data is not connected yet. Please try again later.",
        )
    return repository


Repository = Annotated[PlaceRepository, Depends(get_place_repository)]


@router.get(
    "",
    response_model=PlaceListResponse,
    responses={503: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def list_places(
    repository: Repository,
    request: Request,
    campus_id: Annotated[str, Query(min_length=1, max_length=128)] = "iium-gombak",
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=64)] = None,
    step_free_entrance: bool = False,
    accessible_toilet: bool = False,
    designated_parking: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceListResponse:
    result = search_places(
        repository,
        campus_id=campus_id,
        q=q,
        category=category,
        step_free_entrance=step_free_entrance,
        accessible_toilet=accessible_toilet,
        designated_parking=designated_parking,
        limit=limit,
        offset=offset,
    )
    result.data_mode = "demo" if request.app.state.demo_mode else "live"
    return result


@router.get(
    "/{place_id}",
    response_model=PlaceDetail,
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def get_place(
    place_id: Annotated[str, Path(min_length=1, max_length=128)],
    repository: Repository,
) -> PlaceDetail:
    place = repository.get_place(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Building not found.")
    return place


@router.post(
    "/{place_id}/observations",
    response_model=PlaceDetail,
    status_code=201,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def create_observation(
    place_id: Annotated[str, Path(min_length=1, max_length=128)],
    body: ObservationCreate,
    request: Request,
    user: CurrentUser,
    key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> PlaceDetail:
    adapter = get_place_repository(request)
    writer = getattr(adapter, "create_observation", None)
    if writer is None:
        raise HTTPException(503, "Building observations are not connected yet.")
    place = adapter.get_place(place_id)
    if place is None or place.campus_id != "iium-gombak":
        raise HTTPException(404, "Building not found.")
    now = datetime.now(timezone.utc)
    if body.observed_at > now:
        raise HTTPException(422, "Observation time cannot be in the future.")
    try:
        return writer(place_id, user.id, body, key, now)
    except ObservationTargetMissing:
        raise HTTPException(404, "Building not found.") from None
    except ObservationIdempotencyConflict:
        raise HTTPException(409, "This submission key was already used for different content.") from None
