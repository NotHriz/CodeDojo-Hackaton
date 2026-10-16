"""Validate owned mappings and atomic session lifecycle on disposable SQL only."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.database import Database
from app.models import (Campus, ClearancePublicRecord, ContributorStateRecord,
                        ReportHistoryRecord, ReportPublicRecord)
from app.services.community import ClearanceResponse, ReportEventResponse, ReportResponse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, type=int)
    args = parser.parse_args()
    database = Database(f'postgresql://postgres@127.0.0.1:{args.port}/postgres')

    @event.listens_for(database.engine, 'connect')
    def service_role(connection, _):
        with connection.cursor() as cursor:
            cursor.execute('SET ROLE service_role')
        connection.commit()

    marker = f'session-test-{uuid4()}'
    user, clearance = uuid4(), uuid4()
    class RollBackFixture(Exception):
        pass

    try:
        # Real commit survives a new session; this is an isolated fixture campus.
        with database.transaction() as session:
            session.add(Campus(id=marker, name='Fictional disposable transaction fixture'))
        with database.session() as session:
            assert session.get(Campus, marker).name.startswith('Fictional')
        failed_marker = f'rollback-{uuid4()}'
        try:
            with database.transaction() as session:
                session.add(Campus(id=failed_marker, name='Fictional rolled-back fixture'))
                session.flush()
                session.execute(text("""INSERT INTO public.contributor_state(user_id,vote_weight)
                    VALUES (:user,99)"""), {'user': user})
        except IntegrityError:
            pass
        else:
            raise AssertionError('Expected a real database constraint failure')
        with database.session() as session:
            assert session.get(Campus, failed_marker) is None
        try:
            with database.transaction() as session:
                session.add(ContributorStateRecord(user_id=user, updated_at=datetime.now(timezone.utc)))
                session.flush()
                row = session.get(ContributorStateRecord, user)
                assert row.can_contribute and row.vote_weight == 1 and row.restriction_reason is None
                raw = session.exec(select(ReportPublicRecord)).one()
                report = ReportResponse.model_validate(raw.record)
                assert set(raw.record) == set(ReportResponse.model_fields)
                assert raw.building_id == report.place_id and raw.campus_id == report.campus_id
                session.execute(text("""INSERT INTO public.clearance_observations
                    (id,report_id,report_observed_at,author_id,description,observed_at,idempotency_key,payload_digest)
                    VALUES (:id,:parent,:observed,:user,'Fictional mapping fixture',:observed,:key,:digest)
                """), {'id': clearance, 'parent': report.id, 'observed': report.observed_at,
                       'user': user, 'key': uuid4(), 'digest': 'a' * 64})
                projected = session.get(ClearancePublicRecord, clearance)
                child = ClearanceResponse.model_validate(projected.record)
                assert set(projected.record) == set(ClearanceResponse.model_fields)
                assert child.status == 'unverified' and projected.report_id == report.id
                # A creation event avoids introducing any policy/version input.
                session.execute(text("""INSERT INTO public.report_events
                    (report_id,action,new_status,supporters,disputes,actor_id)
                    VALUES (:parent,'report_created','unverified',0,0,:user)
                """), {'parent': report.id, 'user': user})
                history = session.exec(select(ReportHistoryRecord).where(
                    ReportHistoryRecord.report_id == report.id).order_by(
                    ReportHistoryRecord.occurred_at, ReportHistoryRecord.sequence)).one()
                assert set(history.record) == set(ReportEventResponse.model_fields)
                assert ReportEventResponse.model_validate(history.record).report_id == report.id
                assert history.sequence > 0
                raise RollBackFixture()
        except RollBackFixture:
            pass
        with database.session() as session:
            assert session.get(ContributorStateRecord, user) is None
            assert session.get(ClearancePublicRecord, clearance) is None
            assert session.exec(select(ReportHistoryRecord)).all() == []
        assert database.engine.pool.checkedout() == 0
        print('Session/mapping checks passed: service-role DTO privacy, scoped community reads, commit, exception/constraint rollback and connection release.')
    finally:
        # Delete only our uniquely named campus inside the disposable database.
        with database.transaction() as session:
            row = session.get(Campus, marker)
            if row is not None:
                session.delete(row)
        database.close()


if __name__ == '__main__':
    main()
