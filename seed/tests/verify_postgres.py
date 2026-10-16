"""Called only by the disposable-cluster runner, never application DB settings."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from seed.import_places import load_dataset, render_sql
from seed.tests.test_import_places import fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--port", required=True)
    args = parser.parse_args()
    command = [str(Path(args.pg_bin) / "psql.exe"), "-X", "-h", "127.0.0.1", "-p", args.port,
               "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-qAt"]

    def sql(text, success=True):
        result = subprocess.run(command, input=text, encoding="utf-8", capture_output=True,
                                env={**os.environ, "PGCLIENTENCODING": "UTF8"})
        assert (result.returncode == 0) == success, result.stderr
        return result

    records = fixture()
    records["buildings"][0]["description"] = "Fictional '; DROP TABLE public.buildings; -- \\ unicode: 学习"
    plan = render_sql(load_dataset(json.dumps(records)))
    sql(plan)
    sql("""INSERT INTO public.barrier_reports (building_id, author_id, barrier_type, description,
        observed_at, idempotency_key, payload_digest)
        VALUES ('seed-test-building', '10000000-0000-0000-0000-000000000010', 'obstruction',
        'Fictional preserved report', now(), '10000000-0000-0000-0000-000000000011', repeat('a',64));""")
    sql(plan)
    row = json.loads(sql("""SELECT json_build_object('name', name, 'description', description,
        'facility', step_free_entrance, 'records', (SELECT count(*) FROM public.buildings),
        'reports', (SELECT count(*) FROM public.barrier_reports),
        'entrances', (SELECT count(*) FROM public.entrances),
        'observations', (SELECT count(*) FROM public.facility_observations),
        'missing_time', (SELECT observed_at IS NULL FROM public.facility_observations),
        'missing_entrance_coordinates', (SELECT latitude IS NULL AND longitude IS NULL FROM public.entrances),
        'evidence', (SELECT json_agg(url ORDER BY position) FROM public.observation_evidence))
        FROM public.buildings WHERE id = 'seed-test-building';""").stdout)
    assert row == {"name": records["buildings"][0]["name"], "description": records["buildings"][0]["description"],
                   "facility": "unknown", "records": 1, "reports": 1, "entrances": 1, "observations": 1,
                   "missing_time": True, "missing_entrance_coordinates": True,
                   "evidence": records["observations"][0]["evidence_urls"]}, row

    # Adding a campus before a later conflict must roll the entire import back.
    changed = copy.deepcopy(records)
    changed["campuses"].append({"id": "must-rollback", "name": "Fictional rollback campus"})
    changed["buildings"][0]["name"] = "Conflicting changed building"
    result = sql(render_sql(load_dataset(json.dumps(changed))), success=False)
    assert "Seed conflict in buildings" in result.stderr, result.stderr
    assert sql("SELECT count(*) FROM public.campuses WHERE id = 'must-rollback';").stdout.strip() == "0"
    assert sql("SELECT count(*) FROM public.barrier_reports;").stdout.strip() == "1"

    # A changed evidence reference conflicts rather than overwriting prior evidence.
    changed = copy.deepcopy(records)
    changed["observations"][0]["evidence_urls"][0] = "https://example.com/changed.jpg"
    result = sql(render_sql(load_dataset(json.dumps(changed))), success=False)
    assert "Seed conflict in observation_evidence" in result.stderr, result.stderr
    assert sql("SELECT url FROM public.observation_evidence WHERE position = 0;").stdout.strip() == "https://example.com/first.jpg"
    print("Seed PostgreSQL integration passed: repeat import, exact text, preserved report, conflict rollback and evidence integrity.")


if __name__ == "__main__":
    main()
