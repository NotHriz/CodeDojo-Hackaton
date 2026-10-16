"""Database-independent building query logic and the persistence handoff interface."""

from collections.abc import Sequence
from typing import Protocol

from app.schemas import FacilityValue, PlaceDetail, PlaceListResponse, PlaceSummary


class PlaceRepository(Protocol):
    """Adapter returns validated public records, never private contributor data.

    The database teammate supplies persistence; no runtime mock is provided.
    For the small pilot, list_places returns the campus dataset before filtering.
    """

    def list_places(self, campus_id: str) -> Sequence[PlaceDetail]: ...

    def get_place(self, place_id: str) -> PlaceDetail | None: ...


def search_places(
    repository: PlaceRepository,
    *,
    campus_id: str,
    q: str | None,
    category: str | None,
    step_free_entrance: bool,
    accessible_toilet: bool,
    designated_parking: bool,
    limit: int,
    offset: int,
) -> PlaceListResponse:
    required = {
        "step_free_entrance": step_free_entrance,
        "accessible_toilet": accessible_toilet,
        "designated_parking": designated_parking,
    }
    query = (q or "").strip().casefold()
    category_query = (category or "").strip().casefold()
    matches = []
    for place in repository.list_places(campus_id):
        # Enforce campus boundaries even if the adapter accidentally over-fetches.
        if place.campus_id != campus_id:
            continue
        if query and query not in place.name.casefold():
            continue
        if category_query and place.category.casefold() != category_query:
            continue
        if any(
            enabled and getattr(place.facilities, facility) != FacilityValue.YES
            for facility, enabled in required.items()
        ):
            continue
        matches.append(place)

    matches.sort(key=lambda place: (place.name.casefold(), place.id))
    return PlaceListResponse(
        items=[
            PlaceSummary(**place.model_dump())
            for place in matches[offset : offset + limit]
        ],
        total=len(matches),
        limit=limit,
        offset=offset,
    )
