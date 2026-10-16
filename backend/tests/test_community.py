"""Community contracts and policy tests using explicit test-only persistence."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import PlaceDetail
from app.services.auth import AuthenticatedUser, InvalidAccessToken
from app.services.chat import ChatBudget
from app.services.community import (
    ClearanceRecord, ClearanceResponse, ContributorState, IdempotencyConflict,
    ReportEventResponse, ReportRecord, ReportResponse, ReportStatus, TrustPolicy, VoteSnapshot, VoteStance,
    aggregate_votes, derive_report_status,
)

POLICY = TrustPolicy(minimum_supporters=3, minimum_weight=3, support_ratio=0.67, maximum_vote_weight=2)
AUTHOR = uuid4()


class Verifier:
    def verify(self, token):
        try:
            return AuthenticatedUser(UUID(token))
        except ValueError:
            raise InvalidAccessToken() from None


class Places:
    def get_place(self, place_id):
        if place_id != "test-building":
            return None
        return PlaceDetail(id=place_id, campus_id="iium-gombak", name="Test building", category="study", coordinates={"latitude": 3, "longitude": 101}, is_demo=True)


class Store:
    """Single-threaded lifecycle test adapter; it does not prove SQL atomicity."""

    def __init__(self):
        self.states, self.records, self.votes, self.clearances, self.clearance_votes, self.keys = {}, {}, {}, {}, {}, {}
        self.now = datetime.now(timezone.utc)
        report = ReportResponse(id=uuid4(), place_id="test-building", campus_id="iium-gombak", barrier_type="ramp_blocked", description="Test ramp obstruction", observed_at=self.now - timedelta(minutes=30), submitted_at=self.now - timedelta(minutes=20))
        self.original = ReportRecord(report, AUTHOR)
        self.records[report.id] = self.original
        self.history = [ReportEventResponse(id=uuid4(), report_id=report.id, occurred_at=report.submitted_at, action="report_created", new_status=ReportStatus.UNVERIFIED)]

    def get_contributor(self, user_id):
        return self.states.get(user_id)

    def get_report(self, report_id):
        return self.records.get(report_id)

    def list_reports(self, place_id):
        return list(self.records.values())

    def list_history(self, report_id):
        return self.history

    def append_event(self, report, previous_status, action):
        self.history.append(ReportEventResponse(
            id=uuid4(), report_id=report.id, occurred_at=datetime.now(timezone.utc),
            action=action, previous_status=previous_status, new_status=report.status,
            community=report.community.model_copy(deep=True),
        ))

    def refresh_report(self, report_id, policy, action):
        report = self.records[report_id]
        observations = [item.public for item in self.clearances.values() if item.report_id == report_id]
        status, counts = derive_report_status(
            [vote for (rid, _), vote in self.votes.items() if rid == report_id],
            author_id=report.author_id, policy=policy,
            clearance_states=[item.status for item in observations],
        )
        result = ReportRecord(report.public.model_copy(update={
            "status": status, "community": counts, "clearance_observations": observations,
        }), report.author_id)
        self.records[report_id] = result
        self.append_event(result.public, report.public.status, action)
        return result

    def create_report(self, author_id, body, submitted_at, key):
        key = ("report", author_id, key)
        encoded = body.model_dump_json()
        if key in self.keys:
            previous, result = self.keys[key]
            if encoded != previous:
                raise IdempotencyConflict()
            return result
        report = ReportResponse(id=uuid4(), campus_id="iium-gombak", submitted_at=submitted_at, **body.model_dump())
        result = ReportRecord(report, author_id)
        self.records[report.id] = result
        self.history.append(ReportEventResponse(
            id=uuid4(), report_id=report.id, occurred_at=submitted_at,
            action="report_created", new_status=ReportStatus.UNVERIFIED,
        ))
        self.keys[key] = (encoded, result)
        return result

    def cast_vote(self, report_id, voter_id, stance, weight, policy):
        self.votes[(report_id, voter_id)] = VoteSnapshot(voter_id, stance, weight)
        return self.refresh_report(report_id, policy, "vote_updated")

    def create_clearance(self, report_id, author_id, body, submitted_at, key):
        key = ("clearance", report_id, author_id, key)
        encoded = body.model_dump_json()
        if key in self.keys:
            previous, result = self.keys[key]
            if encoded != previous:
                raise IdempotencyConflict()
            return result
        observation = ClearanceResponse(id=uuid4(), submitted_at=submitted_at, **body.model_dump())
        result = ClearanceRecord(observation, author_id, report_id)
        self.clearances[observation.id] = result
        report = self.records[report_id]
        updated_report = report.public.model_copy(update={
            "clearance_observations": [item.public for item in self.clearances.values() if item.report_id == report_id],
        })
        self.records[report_id] = ReportRecord(updated_report, report.author_id)
        self.append_event(updated_report, report.public.status, "clearance_submitted")
        self.keys[key] = (encoded, result)
        return result

    def get_clearance(self, report_id, clearance_id):
        observation = self.clearances.get(clearance_id)
        return observation if observation and observation.report_id == report_id else None

    def cast_clearance_vote(self, report_id, clearance_id, voter_id, stance, weight, policy):
        self.clearance_votes[(clearance_id, voter_id)] = VoteSnapshot(voter_id, stance, weight)
        observation = self.clearances[clearance_id]
        status, counts = aggregate_votes([v for (cid, _), v in self.clearance_votes.items() if cid == clearance_id], author_id=observation.author_id, policy=policy)
        updated = ClearanceRecord(observation.public.model_copy(update={"status": status, "community": counts}), observation.author_id, report_id)
        self.clearances[clearance_id] = updated
        return self.refresh_report(report_id, policy, "clearance_vote_updated")


def headers(user=AUTHOR, *, key=None):
    result = {"Authorization": "Bearer " + str(user)}
    if key is not None:
        result["Idempotency-Key"] = str(key)
    return result


def report_body(**updates):
    return {"place_id": "test-building", "barrier_type": "ramp_blocked", "description": "Observed obstruction", "observed_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), **updates}


@pytest.fixture
def connected():
    store = Store()
    api = create_app(Settings(_env_file=None, supabase_url="", ai_api_key=""), token_verifier=Verifier(), community_repository=store, place_repository=Places(), trust_policy=POLICY)
    with TestClient(api) as client:
        yield client, store


def test_create_requires_authentication_and_idempotency_header(connected):
    client, _ = connected
    assert client.post("/api/reports", json=report_body()).status_code == 401
    assert client.post("/api/reports", json=report_body(), headers=headers()).status_code == 422


def test_creation_is_unverified_private_and_idempotent(connected):
    client, store = connected
    key, body = uuid4(), report_body()
    first = client.post("/api/reports", json=body, headers=headers(key=key))
    second = client.post("/api/reports", json=body, headers=headers(key=key))
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert first.json()["status"] == "unverified"
    assert "author_id" not in first.json()
    conflict = client.post("/api/reports", json={**body, "description": "Different payload"}, headers=headers(key=key))
    assert conflict.status_code == 409


@pytest.mark.parametrize("updates", [
    {"author_id": str(uuid4())}, {"status": "resolved"}, {"weight": 99},
    {"description": "   "}, {"barrier_type": " "}, {"observed_at": "2026-01-01T00:00:00"},
    {"observed_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
    {"evidence_urls": ["file:///private"]},
])
def test_invalid_or_privileged_report_fields_cannot_be_submitted(connected, updates):
    client, _ = connected
    response = client.post("/api/reports", json=report_body(**updates), headers=headers(key=uuid4()))
    assert response.status_code == 422


def test_unknown_building_and_restricted_contributor(connected):
    client, store = connected
    assert client.post("/api/reports", json=report_body(place_id="missing"), headers=headers(key=uuid4())).status_code == 404
    store.states[AUTHOR] = ContributorState(can_contribute=False)
    response = client.post("/api/reports", json=report_body(), headers=headers(key=uuid4()))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_votes_require_distinct_members_and_cannot_accept_client_weight(connected):
    client, store = connected
    report_id = store.original.public.id
    url = f"/api/reports/{report_id}/votes"
    assert client.post(url, json={"stance": "corroborate"}, headers=headers()).status_code == 403
    assert client.post(url, json={"stance": "corroborate", "weight": 100}, headers=headers(uuid4())).status_code == 422
    voter = uuid4()
    for _ in range(2):
        response = client.post(url, json={"stance": "corroborate"}, headers=headers(voter))
        assert response.status_code == 200
    assert response.json()["community"]["supporters"] == 1
    assert response.json()["status"] == "unverified"


def test_new_member_quorum_and_bounded_trusted_weight(connected):
    client, store = connected
    report_id = store.original.public.id
    for number in range(3):
        voter = uuid4()
        if number == 0:
            store.states[voter] = ContributorState(vote_weight=100)
        response = client.post(f"/api/reports/{report_id}/votes", json={"stance": "corroborate"}, headers=headers(voter))
        assert response.status_code == 200
        if number == 0:
            assert store.votes[(report_id, voter)].weight == 2
            assert response.json()["status"] == "unverified"
    assert response.json()["status"] == "community_corroborated"
    assert "vote_weight" not in response.text


def test_vote_update_does_not_inflate_counts(connected):
    client, store = connected
    voter, report_id = uuid4(), store.original.public.id
    url = f"/api/reports/{report_id}/votes"
    client.post(url, json={"stance": "corroborate"}, headers=headers(voter))
    updated = client.post(url, json={"stance": "dispute"}, headers=headers(voter))
    assert updated.json()["community"] == {"supporters": 0, "disputes": 1}
    assert updated.json()["status"] == "disputed"


def test_clearance_requires_separate_corroboration_and_keeps_original_truth(connected):
    client, store = connected
    report_id = store.original.public.id
    original_time = store.original.public.observed_at
    created = client.post(f"/api/reports/{report_id}/clearance-observations", json={"description": "Ramp is clear now", "observed_at": (store.now - timedelta(minutes=1)).isoformat()}, headers=headers(key=uuid4()))
    assert created.status_code == 201
    clearance_id = created.json()["id"]
    url = f"/api/reports/{report_id}/clearance-observations/{clearance_id}/votes"
    assert client.post(url, json={"stance": "corroborate"}, headers=headers()).status_code == 403
    for _ in range(3):
        response = client.post(url, json={"stance": "corroborate"}, headers=headers(uuid4()))
        assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert datetime.fromisoformat(response.json()["observed_at"]) == original_time
    assert AUTHOR not in store.states  # No reputation penalty or fabricated learning.


def test_clearance_before_original_event_is_rejected(connected):
    client, store = connected
    response = client.post(f"/api/reports/{store.original.public.id}/clearance-observations", json={"description": "Old observation", "observed_at": (store.now - timedelta(days=1)).isoformat()}, headers=headers(key=uuid4()))
    assert response.status_code == 422


def test_public_listing_excludes_other_campus_and_private_fields(connected):
    client, store = connected
    other = store.original.public.model_copy(update={"id": uuid4(), "campus_id": "other-campus"})
    store.records[other.id] = ReportRecord(other, uuid4())
    response = client.get("/api/reports?place_id=test-building")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert "author_id" not in response.text
    assert client.get(f"/api/reports/{other.id}").status_code == 404
    assert client.get(f"/api/reports/{uuid4()}").status_code == 404


def test_missing_adapter_and_unreviewed_policy_fail_explicitly():
    store = Store()
    with TestClient(create_app(Settings(_env_file=None, supabase_url=""), token_verifier=Verifier())) as client:
        assert client.get("/api/reports?place_id=test-building").status_code == 503
    with TestClient(create_app(token_verifier=Verifier(), community_repository=store)) as client:
        response = client.post(f"/api/reports/{store.original.public.id}/votes", json={"stance": "corroborate"}, headers=headers(uuid4()))
        assert response.status_code == 503


def test_contribution_limit_is_by_verified_identity(connected):
    _, store = connected
    budget = ChatBudget(per_minute=1, per_day=10)
    with TestClient(create_app(token_verifier=Verifier(), community_repository=store, place_repository=Places(), trust_policy=POLICY, contribution_budget=budget)) as client:
        voter, url = uuid4(), f"/api/reports/{store.original.public.id}/votes"
        assert client.post(url, json={"stance": "corroborate"}, headers=headers(voter)).status_code == 200
        limited = client.post(url, json={"stance": "dispute"}, headers=headers(voter))
        assert limited.status_code == 429
        assert limited.headers["retry-after"]
        assert client.post(url, json={"stance": "dispute"}, headers=headers(uuid4())).status_code == 200


def test_one_trusted_member_cannot_establish_consensus():
    status, counts = aggregate_votes([VoteSnapshot(uuid4(), VoteStance.CORROBORATE, 999)], author_id=AUTHOR, policy=POLICY)
    assert status == ReportStatus.UNVERIFIED
    assert counts.supporters == 1


def test_weighted_opposition_and_neutral_bootstrap():
    votes = [VoteSnapshot(uuid4(), VoteStance.CORROBORATE, 1) for _ in range(3)]
    assert aggregate_votes(votes, author_id=AUTHOR, policy=POLICY)[0] == ReportStatus.CORROBORATED
    votes.append(VoteSnapshot(uuid4(), VoteStance.DISPUTE, 2))
    assert aggregate_votes(votes, author_id=AUTHOR, policy=POLICY)[0] == ReportStatus.DISPUTED


@pytest.mark.parametrize("kind", ["self", "duplicate", "nan", "negative"])
def test_invalid_vote_snapshots_fail_closed(kind):
    voter = AUTHOR if kind == "self" else uuid4()
    weight = float("nan") if kind == "nan" else -1 if kind == "negative" else 1
    votes = [VoteSnapshot(voter, VoteStance.CORROBORATE, weight)]
    if kind == "duplicate":
        votes.append(votes[0])
    with pytest.raises(ValueError):
        aggregate_votes(votes, author_id=AUTHOR, policy=POLICY)


def test_policy_requires_explicit_bounded_thresholds():
    with pytest.raises(ValueError):
        TrustPolicy()
    with pytest.raises(ValueError):
        TrustPolicy(minimum_supporters=1, minimum_weight=1, support_ratio=0.5, maximum_vote_weight=99)


def test_cors_allows_idempotent_submission_header():
    with TestClient(create_app(Settings(_env_file=None, allowed_origins="http://localhost:5173"))) as client:
        response = client.options("/api/reports", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type,idempotency-key"})
        assert response.status_code == 200


def test_public_history_is_scoped_ordered_paginated_and_private(connected):
    client, store = connected
    report_id = store.original.public.id
    store.history.insert(0, ReportEventResponse(id=uuid4(), report_id=report_id, occurred_at=store.now, action="vote_updated", previous_status=ReportStatus.UNVERIFIED, new_status=ReportStatus.CORROBORATED, community={"supporters": 3, "disputes": 0}))
    store.history.append(ReportEventResponse(id=uuid4(), report_id=uuid4(), occurred_at=store.now, action="report_created", new_status=ReportStatus.UNVERIFIED))
    response = client.get(f"/api/reports/{report_id}/history?limit=1&offset=1")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["new_status"] == "community_corroborated"
    assert "author_id" not in response.text
    assert "weight" not in response.text


def test_history_cannot_access_missing_report_or_invalid_pagination(connected):
    client, store = connected
    assert client.get(f"/api/reports/{uuid4()}/history").status_code == 404
    assert client.get(f"/api/reports/{store.original.public.id}/history?limit=101").status_code == 422


def corroborate_clearance(client, store):
    report_id = store.original.public.id
    response = client.post(
        f"/api/reports/{report_id}/clearance-observations",
        json={"description": "Clear now", "observed_at": (store.now - timedelta(minutes=1)).isoformat()},
        headers=headers(key=uuid4()),
    )
    assert response.status_code == 201
    clearance_id = response.json()["id"]
    voters = [uuid4() for _ in range(3)]
    url = f"/api/reports/{report_id}/clearance-observations/{clearance_id}/votes"
    for voter in voters:
        response = client.post(url, json={"stance": "corroborate"}, headers=headers(voter))
        assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    return url, voters


def test_resolution_survives_later_vote_on_original_report(connected):
    client, store = connected
    corroborate_clearance(client, store)
    report_id = store.original.public.id
    response = client.post(f"/api/reports/{report_id}/votes", json={"stance": "corroborate"}, headers=headers(uuid4()))
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    history = client.get(f"/api/reports/{report_id}/history").json()["items"]
    assert history[-1]["previous_status"] == history[-1]["new_status"] == "resolved"


def test_create_and_idempotent_retry_record_exactly_one_history_event(connected):
    client, store = connected
    key, body = uuid4(), report_body()
    first = client.post("/api/reports", json=body, headers=headers(key=key))
    client.post("/api/reports", json=body, headers=headers(key=key))
    report_id = first.json()["id"]
    history = client.get(f"/api/reports/{report_id}/history").json()
    assert history["total"] == 1
    assert history["items"][0]["action"] == "report_created"
    assert history["items"][0]["occurred_at"] == first.json()["submitted_at"]


def test_clearing_vote_reversal_restores_original_corroboration_and_records_history(connected):
    client, store = connected
    report_id = store.original.public.id
    for _ in range(3):
        client.post(f"/api/reports/{report_id}/votes", json={"stance": "corroborate"}, headers=headers(uuid4()))
    url, voters = corroborate_clearance(client, store)
    response = client.post(url, json={"stance": "dispute"}, headers=headers(voters[0]))
    assert response.status_code == 200
    assert response.json()["status"] == "community_corroborated"
    assert response.json()["clearance_observations"][0]["status"] == "disputed"
    history = client.get(f"/api/reports/{report_id}/history").json()["items"]
    assert history[-1]["action"] == "clearance_vote_updated"
    assert history[-1]["previous_status"] == "resolved"
    assert history[-1]["new_status"] == "community_corroborated"
