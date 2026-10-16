"""Public building discovery; persistence is injected by the app composition root."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.schemas import ErrorResponse, PlaceDetail, PlaceListResponse
from app.services.places import PlaceRepository, search_places

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
    campus_id: Annotated[str, Query(min_length=1, max_length=128)] = "iium-gombak",
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=64)] = None,
    step_free_entrance: bool = False,
    accessible_toilet: bool = False,
    designated_parking: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PlaceListResponse:
    return search_places(
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
