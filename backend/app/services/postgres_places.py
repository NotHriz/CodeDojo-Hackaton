"""Live place repository; no schema creation, fixture loading or error fallback."""

import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlmodel import select

from app.database import Database
from app.models import PlaceDetailRecord
from app.schemas import ObservationCreate, PlaceDetail


class ObservationIdempotencyConflict(Exception):
    """The retry key was already used for different observation content."""


class ObservationTargetMissing(Exception):
    """The requested building does not exist."""


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

    def create_observation(
        self, building_id: str, author_id: UUID, body: ObservationCreate,
        idempotency_key: UUID, now: datetime,
    ) -> PlaceDetail:
        payload = body.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        with self.database.transaction() as session:
            target = session.execute(
                text("SELECT id FROM public.buildings WHERE id = :building_id FOR UPDATE"),
                {"building_id": building_id},
            ).first()
            if target is None:
                raise ObservationTargetMissing()
            existing = session.execute(
                text("""
                    SELECT payload_digest
                    FROM public.facility_observation_submissions
                    WHERE author_id = :author_id AND building_id = :building_id
                      AND idempotency_key = :idempotency_key
                """),
                {"author_id": author_id, "building_id": building_id, "idempotency_key": idempotency_key},
            ).first()
            if existing is not None:
                if existing.payload_digest != digest:
                    raise ObservationIdempotencyConflict()
            else:
                observation_id = uuid4()
                session.execute(
                    text("""
                        INSERT INTO public.facility_observations
                            (id, building_id, facility, value, observed_at, notes, recorded_at)
                        VALUES (:id, :building_id, :facility, :value, :observed_at, :notes, :recorded_at)
                    """),
                    {"id": observation_id, "building_id": building_id, "facility": body.facility,
                     "value": body.value.value, "observed_at": body.observed_at,
                     "notes": body.notes, "recorded_at": now},
                )
                for position, url in enumerate(body.evidence_urls):
                    session.execute(
                        text("""
                            INSERT INTO public.observation_evidence (observation_id, position, url)
                            VALUES (:observation_id, :position, :url)
                        """),
                        {"observation_id": observation_id, "position": position, "url": str(url)},
                    )
                session.execute(
                    text("""
                        INSERT INTO public.facility_observation_submissions
                            (author_id, building_id, idempotency_key, payload_digest, observation_id)
                        VALUES (:author_id, :building_id, :idempotency_key, :payload_digest, :observation_id)
                    """),
                    {"author_id": author_id, "building_id": building_id,
                     "idempotency_key": idempotency_key, "payload_digest": digest,
                     "observation_id": observation_id},
                )
            row = session.get(PlaceDetailRecord, building_id)
            if row is None:
                raise ObservationTargetMissing()
            return PlaceDetail.model_validate(row.record)
