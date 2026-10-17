"""Validate collected records and emit insert-only SQL; never connect to a DB."""

import argparse
import json
from pathlib import Path
import sys
from uuid import UUID

# Reuse backend field constraints without adding another dependency manifest.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from app.schemas import Coordinates, Entrance, Facilities, FacilityObservation


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SeedCoordinates(Coordinates, StrictModel):
    pass


class SeedFacilities(Facilities, StrictModel):
    pass


class Campus(StrictModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)

    @field_validator("id", "name", check_fields=False)
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("Use nonblank text without NUL characters.")
        return value


class Building(Campus):
    campus_id: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    description: str | None = None
    coordinates: SeedCoordinates
    facilities: SeedFacilities = Field(default_factory=SeedFacilities)

    @field_validator("category", "campus_id")
    @classmethod
    def nonblank_field(cls, value):
        return cls.nonblank(value)


class SeedEntrance(Entrance, StrictModel):
    id: UUID
    building_id: str = Field(min_length=1, max_length=128)
    coordinates: SeedCoordinates | None = None

    @field_validator("description")
    @classmethod
    def nonblank(cls, value):
        return Campus.nonblank(value)


class Observation(FacilityObservation, StrictModel):
    id: UUID
    building_id: str = Field(min_length=1, max_length=128)


class Dataset(StrictModel):
    campuses: list[Campus]
    buildings: list[Building]
    entrances: list[SeedEntrance] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)

    @model_validator(mode="after")
    def references(self):
        for rows in (self.campuses, self.buildings, self.entrances, self.observations):
            if len({row.id for row in rows}) != len(rows):
                raise ValueError("Duplicate record identities are not allowed.")
        campus_ids = {row.id for row in self.campuses}
        building_ids = {row.id for row in self.buildings}
        if any(row.campus_id not in campus_ids for row in self.buildings):
            raise ValueError("Every building must reference a campus in this dataset.")
        if any(row.building_id not in building_ids for row in self.entrances + self.observations):
            raise ValueError("Every entrance/observation must reference a building in this dataset.")
        return self


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def load_dataset(text: str) -> Dataset:
    raw = json.loads(text, object_pairs_hook=_unique_object,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON number.")))
    # PostgreSQL text/JSON cannot store NUL, including escaped NUL in free text.
    if "\\u0000" in json.dumps(raw, ensure_ascii=True):
        raise ValueError("NUL characters are not allowed.")
    return Dataset.model_validate(raw)


def _insert(table, rows, keys):
    if not rows:
        return ""
    # Only hardcoded table/column identifiers reach this function. All record
    # values are inside a standard-conforming, escaped JSON SQL literal.
    columns = list(rows[0])
    names = ", ".join(columns)
    literal = json.dumps(rows, ensure_ascii=True, allow_nan=False).replace("\\", "\\\\").replace("'", "''")
    incoming = f"jsonb_populate_recordset(NULL::public.{table}, E'{literal}'::jsonb)"
    delimiter = _delimiter(literal)
    matches = " AND ".join(f"stored.{name} IS NOT DISTINCT FROM incoming.{name}" for name in columns)
    return f"""INSERT INTO public.{table} ({names})
SELECT {names} FROM {incoming}
ON CONFLICT ({', '.join(keys)}) DO NOTHING;
DO {delimiter}
BEGIN
    IF EXISTS (
        SELECT 1 FROM {incoming} AS incoming
        WHERE NOT EXISTS (SELECT 1 FROM public.{table} AS stored WHERE {matches})
    ) THEN
        RAISE EXCEPTION 'Seed conflict in {table}; existing records were not overwritten';
    END IF;
END;
{delimiter};
"""


def _delimiter(literal):
    delimiter = "$akses_seed$"
    while delimiter in literal:
        delimiter = delimiter[:-1] + "_next$"
    return delimiter


def render_sql(dataset: Dataset) -> str:
    tables = {name: [] for name in ("campuses", "buildings", "entrances", "facility_observations",
                                    "entrance_photos", "observation_evidence")}
    tables["campuses"] = [row.model_dump(mode="json") for row in dataset.campuses]
    for row in dataset.buildings:
        item = row.model_dump(mode="json")
        item.update(item.pop("coordinates"))
        item.update(item.pop("facilities"))
        tables["buildings"].append(item)
    for row in dataset.entrances:
        item = row.model_dump(mode="json")
        coordinates = item.pop("coordinates") or {"latitude": None, "longitude": None}
        item.update(coordinates)
        urls = item.pop("photo_urls")
        tables["entrances"].append(item)
        tables["entrance_photos"].extend(
            {"entrance_id": str(row.id), "position": n, "url": url} for n, url in enumerate(urls))
    for row in dataset.observations:
        item = row.model_dump(mode="json")
        urls = item.pop("evidence_urls")
        tables["facility_observations"].append(item)
        tables["observation_evidence"].extend(
            {"observation_id": str(row.id), "position": n, "url": url} for n, url in enumerate(urls))
    parts = ["-- Reviewed collection import; execute with psql -X -v ON_ERROR_STOP=1.\n",
             "BEGIN;\nSET LOCAL standard_conforming_strings = on;\nSET LOCAL search_path = pg_catalog, public;\n"]
    for name, rows in tables.items():
        keys = ("entrance_id", "position") if name == "entrance_photos" else (
            ("observation_id", "position") if name == "observation_evidence" else ("id",))
        parts.append(_insert(name, rows, keys))
    return "".join(parts) + "COMMIT;\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--sql", action="store_true", help="Emit SQL instead of validation counts.")
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.dataset.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError, ValidationError):
        print("Invalid dataset: check JSON keys, fields, identities, references, dates and URLs.", file=sys.stderr)
        return 1
    if args.sql:
        print(render_sql(dataset), end="")
    else:
        print(f"Valid: {len(dataset.campuses)} campuses, {len(dataset.buildings)} buildings, "
              f"{len(dataset.entrances)} entrances, {len(dataset.observations)} observations. No database writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
