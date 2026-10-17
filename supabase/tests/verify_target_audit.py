"""Exercise the read-only deployment audit against the disposable cluster."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'supabase'))
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from app.database import Database
from inspect_target import inspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, type=int)
    args = parser.parse_args()
    db = Database(f'postgresql://postgres@127.0.0.1:{args.port}/postgres')

    @event.listens_for(db.engine, 'connect')
    def service_role(connection, _):
        with connection.cursor() as cursor:
            cursor.execute('SET ROLE service_role')
        connection.commit()

    try:
        with db.session() as session:
            report = inspect(session)
            assert report['server']['read_only'] == 'on'
            assert not report['missing_relations'] and not report['access_issues'], report['access_issues']
            assert not report['missing_roles'] and report['custom_policy_count'] == 0
            assert not report['mapped_column_issues']
            assert not report['unexpected_public_relations']
            assert len(report['local_migrations']) == 13
            assert report['public_record_samples']['place_detail_records']['checked'] == 1
            assert all(sample['exact_public_fields'] for sample in report['public_record_samples'].values())
            # The local runner intentionally does not impersonate CLI migration history.
            assert report['requires_review'] and not report['migration_history']['present']
            assert session.execute(text("SELECT current_setting('transaction_read_only')")).scalar_one() == 'on'
            try:
                with session.begin_nested():
                    session.execute(text("INSERT INTO public.campuses(id,name) VALUES ('must-not-write','must-not-write')"))
            except DBAPIError as error:
                assert error.orig.sqlstate == '25006', 'Expected read-only transaction enforcement'
            else:
                raise AssertionError('Audit transaction allowed a write')
        admin = Database(f'postgresql://postgres@127.0.0.1:{args.port}/postgres')
        try:
            with admin.transaction() as session:
                session.execute(text('GRANT SELECT ON public.barrier_reports TO anon'))
            with db.session() as session:
                drift = inspect(session)
                assert any(issue.get('relation') == 'barrier_reports' and issue.get('role') == 'anon'
                           for issue in drift['access_issues']), 'Must detect browser grant drift'
        finally:
            with admin.transaction() as session:
                session.execute(text('REVOKE SELECT ON public.barrier_reports FROM anon'))
            admin.close()
        print('Target-audit checks passed: enforced read-only mode, grant-drift detection, migration inventory, role grants, RLS/invoker views and public DTO fields.')
    finally:
        db.close()


if __name__ == '__main__':
    main()
