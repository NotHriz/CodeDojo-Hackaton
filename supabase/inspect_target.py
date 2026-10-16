"""Read-only, credential-safe audit of the configured PostgreSQL target.

Uses the existing backend Settings (ignored .env); never accepts credentials as
CLI arguments, changes a role, applies SQL migrations, or imports records.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.config import Settings
from app.database import Database
from app.models import (Building, Campus, ClearancePublicRecord, ContributorStateRecord,
                        PlaceDetailRecord, ReportHistoryRecord, ReportPublicRecord)
from app.schemas import PlaceDetail
from app.services.community import ClearanceResponse, ReportEventResponse, ReportResponse


def inventory():
    migrations, tables, views = [], set(), set()
    for path in sorted((ROOT / "supabase/migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        migrations.append({"version": path.name.split("_", 1)[0], "file": path.name,
                           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        tables.update(re.findall(r"CREATE TABLE public\.(\w+)", sql))
        views.update(re.findall(r"CREATE VIEW public\.(\w+)", sql))
    return migrations, tables, views


def failure_category(error):
    # Classify locally, but never echo driver messages, URLs or SQL parameters.
    message = str(getattr(error, "orig", error)).lower()
    for needle, category in (("password authentication failed", "authentication_failed"),
                             ("permission denied", "permission_denied"),
                             ("timeout", "connection_timeout"),
                             ("could not translate", "dns_failed"),
                             ("connection refused", "connection_refused"),
                             ("network is unreachable", "network_unreachable")):
        if needle in message:
            return category
    return type(error).__name__


def inspect(session):
    # This must be the first SQL statement, before the first catalog/data read.
    session.execute(text("SET TRANSACTION READ ONLY"))
    session.execute(text("SET LOCAL statement_timeout = '15s'"))
    session.execute(text("SET LOCAL lock_timeout = '3s'"))
    migrations, tables, views = inventory()
    expected = tables | views
    result = {"connected": True, "local_migrations": migrations}
    result["server"] = dict(session.execute(text("""
        SELECT current_setting('server_version_num')::int AS version_num,
            current_user AS runtime_role, current_setting('transaction_read_only') AS read_only,
            r.rolsuper AS superuser, r.rolbypassrls AS bypass_rls
        FROM pg_roles r WHERE r.rolname = current_user
    """)).mappings().one())
    result["server"]["supports_invoker_views"] = result["server"]["version_num"] >= 150000
    result["tls_in_use"] = session.execute(text(
        "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
    )).scalar_one_or_none()
    history_present = session.execute(text(
        "SELECT to_regclass('supabase_migrations.schema_migrations') IS NOT NULL"
    )).scalar_one()
    result["migration_history"] = {"present": history_present}
    applied = None
    if history_present:
        try:
            with session.begin_nested():
                applied = session.execute(text(
                    "SELECT version FROM supabase_migrations.schema_migrations ORDER BY version"
                )).scalars().all()
            local_versions = {row["version"] for row in migrations}
            result["migration_history"].update(applied_versions=applied,
                pending_versions=sorted(local_versions - set(applied)),
                unrecognized_versions=sorted(set(applied) - local_versions))
        except Exception as error:
            result["migration_history"]["inspection_error"] = failure_category(error)
    relations = session.execute(text("""
        SELECT c.oid, c.relname AS name, c.relkind AS kind, c.relrowsecurity AS rls,
            COALESCE(c.reloptions, ARRAY[]::text[]) AS options
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r','p','v','m')
    """)).mappings().all()
    by_name = {row["name"]: row for row in relations}
    result["missing_relations"] = sorted(expected - set(by_name))
    result["unexpected_public_relations"] = sorted(set(by_name) - expected)
    roles = set(session.execute(text(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated','service_role')"
    )).scalars())
    result["missing_roles"] = sorted({"anon", "authenticated", "service_role"} - roles)
    issues = []
    for name in sorted(expected & set(by_name)):
        row = by_name[name]
        if name in tables and (row["kind"] not in ('r', 'p') or not row["rls"]):
            issues.append({"relation": name, "issue": "table_kind_or_rls"})
        if name in views and (row["kind"] != 'v' or 'security_invoker=true' not in row["options"]):
            issues.append({"relation": name, "issue": "view_kind_or_invoker_security"})
        for role in sorted(roles):
            privileges = session.execute(text("""
                SELECT privilege FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE',
                    'TRUNCATE','REFERENCES','TRIGGER']) privilege
                WHERE has_table_privilege(:role, CAST(:oid AS oid), privilege)
            """), {"role": role, "oid": row["oid"]}).scalars().all()
            allowed = {'SELECT'} if name in views else {'SELECT', 'INSERT', 'UPDATE', 'DELETE'}
            if name == 'report_events':
                allowed = {'SELECT', 'INSERT'}
            elif name == 'contributor_state':
                allowed = {'SELECT', 'INSERT', 'UPDATE'}
            expected_permissions = allowed if role == 'service_role' else set()
            if set(privileges) != expected_permissions:
                issues.append({"relation": name, "role": role, "issue": "effective_permissions",
                               "actual": privileges, "expected": sorted(expected_permissions)})
    result["access_issues"] = issues
    sequence = session.execute(text(
        "SELECT to_regclass('public.report_events_sequence_seq')"
    )).scalar_one_or_none()
    result["event_sequence_permissions"] = {}
    if sequence is None:
        issues.append({"relation": "report_events_sequence_seq", "issue": "missing_sequence"})
    else:
        for role in sorted(roles):
            permissions = session.execute(text("""
                SELECT privilege FROM unnest(ARRAY['USAGE','SELECT','UPDATE']) privilege
                WHERE has_sequence_privilege(:role, 'public.report_events_sequence_seq', privilege)
            """), {"role": role}).scalars().all()
            result["event_sequence_permissions"][role] = permissions
            expected_permissions = {'USAGE', 'SELECT'} if role == 'service_role' else set()
            if set(permissions) != expected_permissions:
                issues.append({"relation": "report_events_sequence_seq", "role": role,
                               "issue": "effective_permissions", "actual": permissions,
                               "expected": sorted(expected_permissions)})
    result["runtime_role_warning"] = (
        'administrative_role_do_not_use_for_deployed_application'
        if result['server']['superuser'] or result['server']['runtime_role'] in ('postgres', 'supabase_admin')
        else None)
    result["custom_policy_count"] = session.execute(text("""
        SELECT count(*) FROM pg_policies WHERE schemaname = 'public'
            AND tablename = ANY(:tables)
    """), {"tables": sorted(tables)}).scalar_one()
    result["columns"] = [dict(row) for row in session.execute(text("""
        SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns
        WHERE table_schema = 'public' ORDER BY table_name, ordinal_position
    """)).mappings() if row["table_name"] in expected]
    mapped_column_issues = []
    for model in (Campus, Building, PlaceDetailRecord, ReportPublicRecord,
                  ClearancePublicRecord, ReportHistoryRecord, ContributorStateRecord):
        name = model.__tablename__
        actual = {column['column_name'] for column in result['columns'] if column['table_name'] == name}
        required = set(model.__table__.columns.keys())
        if actual != required:
            mapped_column_issues.append({'relation': name, 'missing': sorted(required - actual),
                                         'unexpected': sorted(actual - required)})
    result['mapped_column_issues'] = mapped_column_issues
    # Validate samples without printing data, authors, votes, URLs or descriptions.
    samples = {}
    for view, model in (("place_detail_records", PlaceDetail), ("report_public_records", ReportResponse),
                        ("clearance_public_records", ClearanceResponse), ("report_history_records", ReportEventResponse)):
        if view not in by_name:
            continue
        try:
            with session.begin_nested():
                records = session.execute(text(f"SELECT record FROM public.{view} LIMIT 100")).scalars().all()
                valid = all(set(record) == set(model.model_fields) for record in records)
                for record in records:
                    model.model_validate(record)
                samples[view] = {"checked": len(records), "exact_public_fields": valid}
        except Exception as error:
            samples[view] = {"inspection_error": failure_category(error)}
    result["public_record_samples"] = samples
    result["requires_review"] = bool(result["missing_relations"] or issues or mapped_column_issues or result["missing_roles"]
        or result["unexpected_public_relations"] or applied is None
        or result["migration_history"].get("pending_versions")
        or result["migration_history"].get("unrecognized_versions")
        or not result["server"]["supports_invoker_views"] or result["custom_policy_count"]
        or result['runtime_role_warning']
        or any(item.get('inspection_error') or not item.get('exact_public_fields', False) for item in samples.values()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    database = None
    metadata = {}
    try:
        settings = Settings()
        value = settings.database_url.get_secret_value()
        if not value:
            print(json.dumps({"connected": False, "error": "DATABASE_URL_not_configured"}))
            return 1
        url = make_url(value)
        link = ROOT / 'supabase/.temp/project-ref'
        metadata = {"target_fingerprint": hashlib.sha256(
            f"{url.host}:{url.port or 5432}/{url.database}".encode()).hexdigest()[:16],
            "local_target": url.host in ('127.0.0.1', 'localhost', '::1'),
            "demo_data_enabled": settings.demo_data_enabled}
        if link.exists():
            ref = link.read_text().strip()
            metadata["cli_matches_auth_project"] = urlsplit(settings.supabase_url).hostname == ref + '.supabase.co'
            metadata["cli_matches_database_project"] = ref in (url.host or '') or ref in (url.username or '')
        database = Database(value)
        with database.session() as session:
            report = inspect(session)
        report.update(metadata)
        if metadata.get('cli_matches_auth_project') is False or metadata.get('cli_matches_database_project') is False:
            report['requires_review'] = True
        print(json.dumps(report, indent=2, default=str))
        return 2 if report['requires_review'] else 0
    except Exception as error:
        print(json.dumps({**metadata, "connected": False, "error": failure_category(error)}))
        return 1
    finally:
        if database is not None:
            database.close()


if __name__ == '__main__':
    raise SystemExit(main())
