"""Credential redaction and migration inventory checks; no database connection."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inspect_target
from pydantic import SecretStr


class TargetAuditTests(unittest.TestCase):
    def test_inventory_matches_versioned_source(self):
        migrations, tables, views = inspect_target.inventory()
        self.assertEqual(len(migrations), 13)
        self.assertEqual(len(tables), 14)
        self.assertEqual(len(views), 7)
        self.assertEqual(len({row['version'] for row in migrations}), 13)
        self.assertTrue(all(len(row['sha256']) == 64 for row in migrations))

    def test_maintain_is_checked_only_on_supported_servers(self):
        for version in (150000, 160011):
            self.assertNotIn('MAINTAIN', inspect_target.table_privileges(version))
        for version in (170000, 170011, 180000):
            self.assertIn('MAINTAIN', inspect_target.table_privileges(version))

    def test_connection_error_never_prints_driver_message_or_secret(self):
        settings = SimpleNamespace(database_url=SecretStr('postgresql://user:super-private-password@localhost/postgres'),
                                   demo_data_enabled=False, supabase_url='')
        output = io.StringIO()
        with patch.object(inspect_target, 'Settings', return_value=settings), \
             patch.object(inspect_target, 'Database', side_effect=RuntimeError('password authentication failed: super-private-password')), \
             patch.object(sys, 'argv', ['inspect_target.py']), redirect_stdout(output):
            self.assertEqual(inspect_target.main(), 1)
        report = json.loads(output.getvalue())
        self.assertEqual(report['error'], 'authentication_failed')
        self.assertNotIn('super-private-password', output.getvalue())
        self.assertNotIn('postgresql://', output.getvalue())

    def test_invalid_settings_are_sanitized(self):
        output = io.StringIO()
        with patch.object(inspect_target, 'Settings', side_effect=ValueError('secret invalid configuration')), \
             patch.object(sys, 'argv', ['inspect_target.py']), redirect_stdout(output):
            self.assertEqual(inspect_target.main(), 1)
        self.assertEqual(json.loads(output.getvalue()), {'connected': False, 'error': 'ValueError'})

    def test_empty_configuration_does_not_connect(self):
        settings = SimpleNamespace(database_url=SecretStr(''))
        output = io.StringIO()
        with patch.object(inspect_target, 'Settings', return_value=settings), \
             patch.object(inspect_target, 'Database') as database, \
             patch.object(sys, 'argv', ['inspect_target.py']), redirect_stdout(output):
            self.assertEqual(inspect_target.main(), 1)
        database.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['error'], 'DATABASE_URL_not_configured')


if __name__ == '__main__':
    unittest.main()
