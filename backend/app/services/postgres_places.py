"""Live place repository; no schema creation, fixture loading or error fallback."""

from sqlmodel import select

from app.database import Database
from app.models import PlaceDetailRecord
from app.schemas import PlaceDetail


class PostgresPlaceRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_places(self, campus_id: str) -> list[PlaceDetail]:
        with self.database.session() as session:
            rows = session.exec(select(PlaceDetailRecord).where(PlaceDetailRecord.campus_id == campus_id)).all()
            return [PlaceDetail.model_validate(row.record) for row in rows]

    def get_place(self, place_id: str) -> PlaceDetail | None:
        with self.database.session() as session:
            row = session.get(PlaceDetailRecord, place_id)
            return PlaceDetail.model_validate(row.record) if row is not None else None
