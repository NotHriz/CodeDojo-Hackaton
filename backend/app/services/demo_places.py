"""Explicit local-only fictional records. Never a fallback for database failures."""

from app.schemas import PlaceDetail


class DemoPlaceRepository:
    def __init__(self):
        self._records = [
            PlaceDetail.model_validate({
                "id": "demo-study-hub", "campus_id": "iium-gombak",
                "name": "DEMO Study Hub (fictional)", "category": "study",
                "coordinates": {"latitude": 3.2500, "longitude": 101.7300},
                "description": "LOCAL DEMO ONLY. Fictional building and approximate example coordinates; not an inspected IIUM facility.",
                "facilities": {"step_free_entrance": "yes", "accessible_toilet": "yes", "designated_parking": "no"},
                "entrances": [{"description": "Fictional east entrance, ground floor"}],
                "observations": [
                    {"facility": "step_free_entrance", "value": "yes", "source": "Fictional local demo", "notes": "No real inspection or verification."},
                    {"facility": "accessible_toilet", "value": "yes", "source": "Fictional local demo"},
                ],
                "is_demo": True,
            }),
            PlaceDetail.model_validate({
                "id": "demo-study-annex", "campus_id": "iium-gombak",
                "name": "DEMO Study Annex (fictional)", "category": "study",
                "coordinates": {"latitude": 3.2510, "longitude": 101.7310},
                "description": "LOCAL DEMO ONLY. Fictional building for testing warning presentation; not a real campus accessibility claim.",
                "facilities": {"step_free_entrance": "yes", "accessible_toilet": "yes", "designated_parking": "unknown"},
                "entrances": [{"description": "Fictional north-side ramp"}],
                "active_warnings": [{
                    "report_id": "demo-warning-ramp", "description": "FICTIONAL DEMO: ramp reported blocked; not a real incident.",
                    "status": "unverified",
                }],
                "observations": [{"facility": "step_free_entrance", "value": "yes", "source": "Fictional local demo"}],
                "is_demo": True,
            }),
            PlaceDetail.model_validate({
                "id": "demo-library", "campus_id": "iium-gombak",
                "name": "DEMO Library (fictional)", "category": "library",
                "coordinates": {"latitude": 3.2520, "longitude": 101.7320},
                "description": "LOCAL DEMO ONLY. Fictional building for testing missing information; not the real IIUM library.",
                "facilities": {"step_free_entrance": "unknown", "accessible_toilet": "no", "designated_parking": "yes"},
                "is_demo": True,
            }),
        ]

    def list_places(self, campus_id: str) -> list[PlaceDetail]:
        return [record.model_copy(deep=True) for record in self._records if record.campus_id == campus_id]

    def get_place(self, place_id: str) -> PlaceDetail | None:
        return next((record.model_copy(deep=True) for record in self._records if record.id == place_id), None)
