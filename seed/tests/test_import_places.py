import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from seed.import_places import load_dataset, render_sql


def fixture():
    """Fictional tests only; not a deployable campus dataset."""
    return {
        "campuses": [{"id": "seed-test-campus", "name": "Fictional seed campus"}],
        "buildings": [{"id": "seed-test-building", "campus_id": "seed-test-campus",
                       "name": "Fictional O'Brien \\ $akses_seed$ building", "category": "study",
                       "coordinates": {"latitude": 3.25, "longitude": 101.73}}],
        "entrances": [{"id": "10000000-0000-0000-0000-000000000001",
                       "building_id": "seed-test-building", "description": "Fictional east entrance",
                       "photo_urls": ["https://example.com/east.jpg"]}],
        "observations": [{"id": "10000000-0000-0000-0000-000000000002",
                          "building_id": "seed-test-building", "facility": "step_free_entrance",
                          "value": "unknown", "observed_at": None, "source": "Fictional test only",
                          "evidence_urls": ["https://example.com/first.jpg", "https://example.com/second.jpg"]}]
    }


class ImportValidationTests(unittest.TestCase):
    def load(self, data):
        return load_dataset(json.dumps(data))

    def test_unknown_defaults_and_absent_coordinates_dates(self):
        result = self.load(fixture())
        self.assertEqual(result.buildings[0].facilities.step_free_entrance, "unknown")
        self.assertIsNone(result.entrances[0].coordinates)
        self.assertIsNone(result.observations[0].observed_at)

    def test_duplicate_ids(self):
        for collection in ("campuses", "buildings", "entrances", "observations"):
            with self.subTest(collection=collection):
                data = fixture()
                data[collection].append(copy.deepcopy(data[collection][0]))
                with self.assertRaises(ValueError):
                    self.load(data)

    def test_dangling_references(self):
        for collection, key in (("buildings", "campus_id"), ("entrances", "building_id"), ("observations", "building_id")):
            data = fixture()
            data[collection][0][key] = "missing"
            with self.subTest(collection=collection), self.assertRaises(ValueError):
                self.load(data)

    def test_private_unknown_and_demo_fields_rejected(self):
        for collection, key in (("buildings", "is_demo"), ("observations", "author_id"),
                                ("campuses", "service_role_key"), ("entrances", "vote_weight")):
            data = fixture()
            data[collection][0][key] = "must-not-import"
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load(data)

    def test_nested_unknown_fields_rejected(self):
        data = fixture()
        data["buildings"][0]["coordinates"]["secret"] = "hidden"
        with self.assertRaises(ValueError):
            self.load(data)

    def test_invalid_facility_coordinate_and_url(self):
        for collection, key, value in (("observations", "facility", "lift"),
                                       ("observations", "value", "maybe"),
                                       ("entrances", "photo_urls", ["file:///private"])):
            data = fixture()
            data[collection][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load(data)
        data = fixture()
        data["buildings"][0]["coordinates"]["latitude"] = 91
        with self.assertRaises(ValueError):
            self.load(data)

    def test_naive_dates_rejected_offset_dates_preserved(self):
        data = fixture()
        data["observations"][0]["observed_at"] = "2026-10-17T12:00:00"
        with self.assertRaises(ValueError):
            self.load(data)
        data["observations"][0]["observed_at"] += "+08:00"
        self.assertIsNotNone(self.load(data).observations[0].observed_at.tzinfo)

    def test_json_duplicates_nonfinite_and_nul_rejected(self):
        for text in ('{"campuses": [], "campuses": [], "buildings": []}',
                     '{"campuses": [], "buildings": [], "bad": NaN}'):
            with self.assertRaises(ValueError):
                load_dataset(text)
        data = fixture()
        data["observations"][0]["notes"] = "bad\x00text"
        with self.assertRaises(ValueError):
            self.load(data)

    def test_sql_is_deterministic_and_does_not_target_community_state(self):
        dataset = self.load(fixture())
        self.assertEqual(render_sql(dataset), render_sql(dataset))
        for private_table in ("barrier_reports", "report_votes", "report_events", "contributor_state"):
            self.assertNotIn("public." + private_table, render_sql(dataset))

    def test_cli_validation_and_error_do_not_echo_input(self):
        script = Path(__file__).resolve().parents[1] / "import_places.py"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(json.dumps(fixture()), encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No database writes", result.stdout)
            path.write_text('{"private_key":"sensitive-test-value"}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(script), str(path), "--sql"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("sensitive-test-value", result.stderr)


if __name__ == "__main__":
    unittest.main()
