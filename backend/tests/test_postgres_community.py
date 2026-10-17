"""Real transactions/concurrency against an explicitly disposable LOCAL database.

Set COMMUNITY_TEST_DATABASE_URL to a fresh akses_community_test database.
No fallback to DATABASE_URL or developer credentials is allowed.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.services.community import (
    ClearanceCreate, ContributionDenied, ContributionTargetMissing, IdempotencyConflict,
    InvalidObservationTime, PolicyConflict, PolicyUnavailable, ReportCreate,
    TrustPolicy, VoteStance, utc_now,
)
from app.services.postgres_community import PostgresCommunityRepository, payload_digest
from app.services.auth import AuthenticatedUser
from app.services.postgres_places import PostgresPlaceRepository
from app.services.trust_policies import PILOT_POLICY, PILOT_POLICY_VERSION

POLICY = TrustPolicy(minimum_supporters=3, minimum_weight=3, support_ratio=.67, maximum_vote_weight=2)
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def local_database():
    url = os.environ.get("COMMUNITY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Disposable local PostgreSQL not configured")
    parsed = make_url(url)
    if parsed.host not in {"127.0.0.1", "localhost", "::1"} or parsed.database != "akses_community_test":
        pytest.fail("Integration tests require a disposable local akses_community_test database")
    # Initialization is allowed only on this explicitly named, empty local DB.
    with psycopg.connect(url) as connection:
        assert connection.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0] == 0
        connection.execute((ROOT / "supabase/tests/roles.sql").read_text())
        for migration in sorted((ROOT / "supabase/migrations").glob("*.sql")):
            connection.execute(migration.read_text())
    admin = Database(url)
    database = Database(url)

    @event.listens_for(database.engine, "connect")
    def service_role(connection, _):
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE service_role")
        connection.commit()

    yield admin, database
    database.close()
    admin.close()


@pytest.fixture
def connected(local_database):
    admin, database = local_database
    place = "transaction-test-" + uuid4().hex
    with admin.transaction() as session:
        session.execute(text("INSERT INTO public.campuses(id,name) VALUES ('iium-gombak','Fictional test campus') ON CONFLICT DO NOTHING"))
        session.execute(text("""INSERT INTO public.buildings(id,campus_id,name,category,latitude,longitude)
            VALUES (:id,'iium-gombak','Fictional test building','study',3.25,101.73)"""), {"id": place})
    repository = PostgresCommunityRepository(database, policy=POLICY, policy_version="test-only-v1")
    now = utc_now()
    body = ReportCreate(place_id=place, barrier_type="blocked_ramp", description="Fictional barrier",
                        observed_at=now - timedelta(minutes=2), evidence_urls=["https://example.com/test.jpg"])
    return admin, repository, body, now


def parallel(functions):
    barrier = Barrier(len(functions))
    def run(function):
        barrier.wait(timeout=10)
        return function()
    with ThreadPoolExecutor(max_workers=len(functions)) as pool:
        futures = [pool.submit(run, f) for f in functions]
        return [future.result(timeout=20) for future in futures]


def scalar(admin, sql, **params):
    with admin.session() as session:
        return session.execute(text(sql), params).scalar_one()


def test_concurrent_report_retries_persist_one_record_event_and_evidence(connected):
    admin, repo, body, now = connected
    actor, key = uuid4(), uuid4()
    results = parallel([lambda i=i: repo.create_report(actor, body, now + timedelta(seconds=i), key) for i in range(4)])
    assert len({r.public.id for r in results}) == 1
    assert len({r.public.submitted_at for r in results}) == 1
    report = results[0].public
    assert len(repo.list_history(report.id)) == 1
    assert scalar(admin, "SELECT count(*) FROM public.barrier_report_evidence WHERE report_id=:id", id=report.id) == 1
    assert repo.list_reports(body.place_id)[0].public.id == report.id
    other = PostgresCommunityRepository(repo.database)
    assert other.get_report(report.id).public == report
    with pytest.raises(IdempotencyConflict):
        repo.create_report(actor, body.model_copy(update={"description": "Changed"}), now, key)


def test_concurrent_conflicting_retries_have_one_winner(connected):
    _, repo, body, now = connected
    actor, key = uuid4(), uuid4()
    def submit(description):
        try:
            return repo.create_report(actor, body.model_copy(update={"description": description}), now, key)
        except IdempotencyConflict:
            return None
    results = parallel([lambda: submit("One"), lambda: submit("Two")])
    assert sum(r is not None for r in results) == 1
    assert len(repo.list_reports(body.place_id)) == 1


def test_concurrent_votes_recompute_counts_without_lost_updates(connected):
    admin, repo, body, now = connected
    report = repo.create_report(uuid4(), body, now, uuid4()).public
    voters = [uuid4() for _ in range(6)]
    parallel([lambda voter=v: repo.cast_vote(report.id, voter, VoteStance.CORROBORATE, 999, POLICY) for v in voters])
    current = repo.get_report(report.id).public
    assert current.status == "community_corroborated"
    assert current.community.supporters == 6
    assert len(repo.list_history(report.id)) == 7
    assert scalar(admin, "SELECT max(weight) FROM public.report_votes WHERE report_id=:id", id=report.id) == 1
    assert scalar(admin, "SELECT count(DISTINCT policy_version) FROM public.report_events WHERE report_id=:id AND stance IS NOT NULL", id=report.id) == 1
    parallel([lambda: repo.cast_vote(report.id, voters[0], VoteStance.DISPUTE, 99, POLICY) for _ in range(3)])
    changed = repo.get_report(report.id).public
    assert (changed.community.supporters, changed.community.disputes) == (5, 1)
    assert len(repo.list_history(report.id)) == 10
    assert repo.database.engine.pool.checkedout() == 0


def test_clearance_retries_resolution_reversal_and_original_vote(connected):
    admin, repo, body, now = connected
    author = uuid4()
    report = repo.create_report(author, body, now, uuid4()).public
    for _ in range(3):
        repo.cast_vote(report.id, uuid4(), VoteStance.CORROBORATE, 1, POLICY)
    clearing_body = ClearanceCreate(description="Fictional clearing", observed_at=now)
    key, clearing_author = uuid4(), uuid4()
    claims = parallel([lambda: repo.create_clearance(report.id, clearing_author, clearing_body, now, key) for _ in range(3)])
    clearing = claims[0].public
    assert len({r.public.id for r in claims}) == 1
    with pytest.raises(IdempotencyConflict):
        repo.create_clearance(report.id, clearing_author, clearing_body.model_copy(update={"description": "Different"}), now, key)
    voters = [author, uuid4(), uuid4()]
    parallel([lambda voter=v: repo.cast_clearance_vote(report.id, clearing.id, voter, VoteStance.CORROBORATE, 1, POLICY) for v in voters])
    assert repo.get_report(report.id).public.status == "resolved"
    assert repo.cast_vote(report.id, uuid4(), VoteStance.CORROBORATE, 1, POLICY).public.status == "resolved"
    changed = repo.cast_clearance_vote(report.id, clearing.id, voters[0], VoteStance.DISPUTE, 1, POLICY).public
    assert changed.status == "community_corroborated"
    assert changed.clearance_observations[0].status == "disputed"
    history = repo.list_history(report.id)
    assert sum(e.action == "clearance_submitted" for e in history) == 1
    assert history[-1].previous_status == "resolved"
    assert history[-1].new_status == "community_corroborated"
    assert repo.get_clearance(uuid4(), clearing.id) is None
    assert scalar(admin, "SELECT count(*) FROM public.clearance_observations WHERE report_id=:id", id=report.id) == 1


@pytest.mark.parametrize("operation", ["create", "vote", "clearance", "clearance_vote"])
def test_failure_after_event_insert_rolls_back_entire_mutation(connected, monkeypatch, operation):
    admin, repo, body, now = connected
    actor = uuid4()
    report = repo.create_report(uuid4(), body, now, uuid4()).public
    clearing = repo.create_clearance(report.id, uuid4(), ClearanceCreate(description="Clear", observed_at=now), now, uuid4()).public
    before = repo.get_report(report.id).public
    history_before = repo.list_history(report.id)
    append = repo._event
    def fail_after_insert(*args, **kwargs):
        append(*args, **kwargs)
        raise RuntimeError("Injected transaction failure")
    monkeypatch.setattr(repo, "_event", fail_after_insert)
    operations = {
        "create": lambda: repo.create_report(actor, body, now, uuid4()),
        "vote": lambda: repo.cast_vote(report.id, actor, VoteStance.DISPUTE, 1, POLICY),
        "clearance": lambda: repo.create_clearance(report.id, actor, ClearanceCreate(description="Another", observed_at=now), now, uuid4()),
        "clearance_vote": lambda: repo.cast_clearance_vote(report.id, clearing.id, actor, VoteStance.DISPUTE, 1, POLICY),
    }
    with pytest.raises(RuntimeError, match="Injected"):
        operations[operation]()
    assert repo.get_report(report.id).public == before
    assert repo.list_history(report.id) == history_before
    assert len(repo.list_reports(body.place_id)) == 1
    assert repo.get_contributor(actor) is None
    assert repo.database.engine.pool.checkedout() == 0


@pytest.mark.parametrize("existing", [False, True])
def test_restriction_race_rechecks_locked_contributor(connected, existing):
    admin, repo, body, now = connected
    actor = uuid4()
    if existing:
        with admin.transaction() as session:
            session.execute(text("INSERT INTO public.contributor_state(user_id) VALUES (:id)"), {"id": actor})
    started = Event()
    def submit():
        started.set()
        with pytest.raises(ContributionDenied):
            repo.create_report(actor, body, now, uuid4())
    with ThreadPoolExecutor(max_workers=1) as pool:
        with admin.transaction() as session:
            session.execute(text("""INSERT INTO public.contributor_state(user_id,can_contribute,restriction_reason)
                VALUES (:id,false,'Test restriction') ON CONFLICT (user_id) DO UPDATE SET
                can_contribute=false, restriction_reason='Test restriction'"""), {"id": actor})
            future = pool.submit(submit)
            assert started.wait(5)
        future.result(timeout=15)
    assert repo.list_reports(body.place_id) == []


def test_private_weight_reloaded_and_policy_changes_rejected(connected):
    admin, repo, body, now = connected
    report = repo.create_report(uuid4(), body, now, uuid4()).public
    actor = uuid4()
    with admin.transaction() as session:
        session.execute(text("INSERT INTO public.contributor_state(user_id,vote_weight) VALUES (:id,2)"), {"id": actor})
    repo.cast_vote(report.id, actor, VoteStance.CORROBORATE, .1, POLICY)
    assert scalar(admin, "SELECT weight FROM public.report_votes WHERE report_id=:id", id=report.id) == 2
    with pytest.raises(PolicyUnavailable):
        PostgresCommunityRepository(repo.database).cast_vote(report.id, uuid4(), VoteStance.DISPUTE, 1, POLICY)
    with pytest.raises(PolicyConflict):
        PostgresCommunityRepository(repo.database, policy=POLICY, policy_version="different-version").cast_vote(report.id, uuid4(), VoteStance.DISPUTE, 1, POLICY)
    assert len(repo.list_history(report.id)) == 2


def test_membership_chronology_self_votes_and_private_dto_exclusion(connected):
    admin, repo, body, now = connected
    actor = uuid4()
    report = repo.create_report(actor, body, now, uuid4()).public
    with pytest.raises(ContributionDenied):
        repo.cast_vote(report.id, actor, VoteStance.CORROBORATE, 1, POLICY)
    with pytest.raises(ContributionTargetMissing):
        repo.create_report(actor, body.model_copy(update={"place_id": "missing"}), now, uuid4())
    with pytest.raises(InvalidObservationTime):
        repo.create_clearance(report.id, actor, ClearanceCreate(description="Too early", observed_at=body.observed_at-timedelta(seconds=1)), now, uuid4())
    with pytest.raises(InvalidObservationTime):
        repo.create_report(actor, body.model_copy(update={"observed_at": now+timedelta(minutes=6)}), now, uuid4())
    with admin.transaction() as session:
        session.execute(text("INSERT INTO public.campuses(id,name) VALUES ('other-test','Other') ON CONFLICT DO NOTHING"))
        session.execute(text("UPDATE public.buildings SET campus_id='other-test' WHERE id=:id"), {"id": body.place_id})
    assert repo.get_report(report.id) is None
    assert repo.list_reports(body.place_id) == []
    assert repo.list_history(report.id) == []
    with pytest.raises(ContributionTargetMissing):
        repo.cast_vote(report.id, uuid4(), VoteStance.DISPUTE, 1, POLICY)
    assert "author_id" not in report.model_dump()


def test_normalized_digest_excludes_submission_time_and_timezone_spelling():
    now = utc_now()
    a = ReportCreate(place_id="x", barrier_type="ramp", description=" Trimmed ", observed_at=now)
    b = ReportCreate(place_id="x", barrier_type="ramp", description="Trimmed", observed_at=now.astimezone(timezone(timedelta(hours=8))))
    assert payload_digest(a) == payload_digest(b)


def test_configured_http_reads_survive_app_recreation(connected):
    _, repo, body, now = connected
    report = repo.create_report(uuid4(), body, now, uuid4()).public
    for _ in range(2):
        app = create_app(Settings(_env_file=None), community_repository=repo)
        with TestClient(app) as client:
            assert client.get(f"/api/reports/{report.id}").json() == report.model_dump(mode="json")
            history = client.get(f"/api/reports/{report.id}/history").json()["items"]
            assert len(history) == 1
            assert "actor_id" not in history[0] and "weight" not in history[0]


def test_http_mutations_persist_and_failure_codes_are_explicit(connected):
    _, repo, body, now = connected
    actor, voter = uuid4(), uuid4()
    class Verifier:
        def verify(self, token):
            from uuid import UUID
            return AuthenticatedUser(UUID(token))
    app = create_app(Settings(_env_file=None), community_repository=repo,
                     place_repository=PostgresPlaceRepository(repo.database), token_verifier=Verifier(),
                     trust_policy=POLICY, trust_policy_version="test-only-v1")
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {actor}", "Idempotency-Key": str(uuid4())}
        first = client.post("/api/reports", json=body.model_dump(mode="json"), headers=headers)
        retry = client.post("/api/reports", json=body.model_dump(mode="json"), headers=headers)
        assert first.status_code == retry.status_code == 201
        assert first.json() == retry.json()
        report = first.json()
        changed = body.model_dump(mode="json") | {"description": "Changed"}
        assert client.post("/api/reports", json=changed, headers=headers).status_code == 409
        vote_url = f"/api/reports/{report['id']}/votes"
        assert client.post(vote_url, json={"stance": "corroborate"}, headers=headers).status_code == 403
        result = client.post(vote_url, json={"stance": "dispute"}, headers={"Authorization": f"Bearer {voter}"})
        assert result.status_code == 200
        assert result.json()["community"]["disputes"] == 1
        assert "author_id" not in result.json()
        warning = client.get(f"/api/places/{body.place_id}").json()["active_warnings"]
        assert str(report["id"]) in {w["report_id"] for w in warning}
        assert len(client.get(f"/api/reports/{report['id']}/history").json()["items"]) == 2


def test_named_policy_writes_exact_version_and_threshold_snapshots(connected):
    admin, original, body, now = connected
    repo = PostgresCommunityRepository(original.database, policy=PILOT_POLICY.policy, policy_version=PILOT_POLICY_VERSION)
    report = repo.create_report(uuid4(), body, now, uuid4()).public
    for _ in range(3):
        repo.cast_vote(report.id, uuid4(), VoteStance.CORROBORATE, 1, PILOT_POLICY.policy)
    assert repo.get_report(report.id).public.status == "community_corroborated"
    clearing = repo.create_clearance(report.id, uuid4(), ClearanceCreate(description="Cleared", observed_at=now), now, uuid4()).public
    for _ in range(3):
        repo.cast_clearance_vote(report.id, clearing.id, uuid4(), VoteStance.CORROBORATE, 1, PILOT_POLICY.policy)
    assert repo.get_report(report.id).public.status == "resolved"
    for table in ("report_votes", "clearance_votes", "report_events"):
        with admin.session() as session:
            rows = session.execute(text(f"SELECT * FROM public.{table} WHERE report_id=:id AND policy_version IS NOT NULL"), {"id": report.id}).mappings().all()
        assert len(rows) == (6 if table == "report_events" else 3)
        for row in rows:
            assert row["policy_version"] == PILOT_POLICY_VERSION
            for name, value in PILOT_POLICY.policy.model_dump().items():
                assert float(row[f"policy_{name}"]) == value
    # A new deployment cannot silently relabel existing snapshots.
    with pytest.raises(PolicyConflict):
        original.cast_vote(report.id, uuid4(), VoteStance.CORROBORATE, 1, POLICY)


def test_cloud_default_grants_are_narrowed_to_application_contract(local_database):
    admin, _ = local_database
    assert scalar(admin, """SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','v')
        AND has_table_privilege('service_role', c.oid, 'TRUNCATE,REFERENCES,TRIGGER,MAINTAIN')""") == 0
    assert scalar(admin, """SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind='r' AND c.relname NOT IN ('contributor_state','report_events')
        AND has_table_privilege('service_role',c.oid,'SELECT')
        AND has_table_privilege('service_role',c.oid,'INSERT')
        AND has_table_privilege('service_role',c.oid,'UPDATE')
        AND has_table_privilege('service_role',c.oid,'DELETE')""") == 13


def test_audit_detects_maintain_drift_on_real_postgres(local_database):
    import sys
    sys.path.insert(0, str(ROOT / 'supabase'))
    from inspect_target import inspect
    admin, _ = local_database
    with admin.session() as session:
        assert not inspect(session)['access_issues']
    try:
        with admin.transaction() as session:
            session.execute(text('GRANT MAINTAIN ON public.campuses TO service_role'))
        with admin.session() as session:
            report = inspect(session)
        issues = [issue for issue in report['access_issues']
                  if issue.get('relation') == 'campuses' and issue.get('role') == 'service_role']
        assert len(issues) == 1
        assert 'MAINTAIN' in issues[0]['actual']
        assert 'MAINTAIN' not in issues[0]['expected']
        assert report['requires_review']
    finally:
        with admin.transaction() as session:
            session.execute(text('REVOKE MAINTAIN ON public.campuses FROM service_role'))
