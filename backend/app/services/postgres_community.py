"""Transactional community persistence over the accepted PostgreSQL schema.

Lock order: contributor -> building/report -> clearing observation. Restriction
writers must upsert/lock the same contributor row before taking target locks.
No schema creation, remote setup, default voting policy, or error fallback.
"""

import hashlib
import json
from datetime import timezone
from uuid import uuid4

from sqlalchemy import text

from app.database import Database
from app.services.community import (
    ClearanceRecord, ClearanceResponse, ContributionDenied, ContributionTargetMissing,
    ContributorState, IdempotencyConflict, InvalidObservationTime, PolicyConflict,
    PolicyUnavailable, ReportEventResponse, ReportRecord, ReportResponse, ReportStatus,
    TrustPolicy, VoteSnapshot, VoteStance, aggregate_votes, derive_report_status,
    eligible_weight, utc_now, validate_observation_time,
)

PILOT = "iium-gombak"
POLICY_FIELDS = tuple(TrustPolicy.model_fields)


def payload_digest(body):
    data = body.model_dump(mode="json")
    # Equivalent timezone representations are the same normalized observation.
    data["observed_at"] = body.observed_at.astimezone(timezone.utc).isoformat()
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PostgresCommunityRepository:
    def __init__(self, database: Database, *, policy: TrustPolicy | None = None, policy_version: str | None = None):
        if (policy is None) != (policy_version is None):
            raise ValueError("Voting requires both an explicit policy and version.")
        if policy_version is not None and (not policy_version.strip() or len(policy_version) > 128):
            raise ValueError("Policy version must contain 1–128 characters.")
        self.database = database
        self.policy = policy
        self.policy_version = policy_version

    @staticmethod
    def _row(session, sql, **params):
        return session.execute(text(sql), params).mappings().one_or_none()

    def get_contributor(self, user_id):
        with self.database.session() as session:
            row = self._row(session, "SELECT can_contribute, vote_weight FROM public.contributor_state WHERE user_id=:id", id=user_id)
            return ContributorState(row["can_contribute"], float(row["vote_weight"])) if row else None

    def _actor(self, session, actor, policy=None):
        # INSERT handles the absent-row race; ON CONFLICT waits for concurrent
        # creation/restriction, then FOR UPDATE rechecks the committed state.
        session.execute(text("INSERT INTO public.contributor_state(user_id) VALUES (:id) ON CONFLICT DO NOTHING"), {"id": actor})
        row = self._row(session, "SELECT can_contribute, vote_weight FROM public.contributor_state WHERE user_id=:id FOR UPDATE", id=actor)
        return eligible_weight(ContributorState(row["can_contribute"], float(row["vote_weight"])), policy)

    def _report(self, session, report_id):
        row = self._row(session, """SELECT v.record, r.author_id FROM public.report_public_records v
            JOIN public.barrier_reports r ON r.id=v.id WHERE v.id=:id AND v.campus_id=:campus""", id=report_id, campus=PILOT)
        return ReportRecord(ReportResponse.model_validate(row["record"]), row["author_id"]) if row else None

    def get_report(self, report_id):
        with self.database.session() as session:
            return self._report(session, report_id)

    def list_reports(self, place_id):
        with self.database.session() as session:
            rows = session.execute(text("""SELECT v.record, r.author_id FROM public.report_public_records v
                JOIN public.barrier_reports r ON r.id=v.id WHERE v.building_id=:id AND v.campus_id=:campus
                ORDER BY v.submitted_at DESC, v.id DESC"""), {"id": place_id, "campus": PILOT}).mappings()
            return [ReportRecord(ReportResponse.model_validate(r["record"]), r["author_id"]) for r in rows]

    def list_history(self, report_id):
        with self.database.session() as session:
            rows = session.execute(text("""SELECT record FROM public.report_history_records
                WHERE report_id=:id AND campus_id=:campus ORDER BY occurred_at, sequence"""), {"id": report_id, "campus": PILOT}).scalars()
            return [ReportEventResponse.model_validate(r) for r in rows]

    def _clearance(self, session, report_id, clearance_id):
        row = self._row(session, """SELECT v.record, c.author_id FROM public.clearance_public_records v
            JOIN public.clearance_observations c ON c.id=v.id
            JOIN public.report_public_records r ON r.id=v.report_id
            WHERE v.id=:id AND v.report_id=:report AND r.campus_id=:campus""", id=clearance_id, report=report_id, campus=PILOT)
        return ClearanceRecord(ClearanceResponse.model_validate(row["record"]), row["author_id"], report_id) if row else None

    def get_clearance(self, report_id, clearance_id):
        with self.database.session() as session:
            return self._clearance(session, report_id, clearance_id)

    def _lock_report(self, session, report_id):
        row = self._row(session, """SELECT r.*, b.campus_id FROM public.barrier_reports r
            JOIN public.buildings b ON b.id=r.building_id WHERE r.id=:id AND b.campus_id=:campus
            FOR UPDATE OF r FOR SHARE OF b""", id=report_id, campus=PILOT)
        if row is None:
            raise ContributionTargetMissing()
        return row

    @staticmethod
    def _time(body, submitted_at, parent_time=None):
        if (submitted_at.tzinfo is None or not validate_observation_time(body.observed_at, submitted_at)
                or (parent_time is not None and body.observed_at < parent_time)):
            raise InvalidObservationTime()

    @staticmethod
    def _evidence(session, table, column, target, urls):
        # Table/column names are internal constants, never request arguments.
        for position, url in enumerate(urls):
            session.execute(text(f"INSERT INTO public.{table}({column}, position, url) VALUES (:id, :position, :url)"),
                            {"id": target, "position": position, "url": str(url)})

    def _event(self, session, *, report, actor, action, previous, status, counts,
               when=None, clearance=None, clearance_previous=None, clearance_status=None,
               clearance_counts=None, stance=None, weight=None):
        params = {"report": report, "actor": actor, "action": action, "previous": previous,
                  "status": status, "supporters": counts.supporters, "disputes": counts.disputes,
                  "when": when or utc_now(), "clearance": clearance,
                  "clearance_previous": clearance_previous, "clearance_status": clearance_status,
                  "clearance_supporters": clearance_counts.supporters if clearance_counts else None,
                  "clearance_disputes": clearance_counts.disputes if clearance_counts else None,
                  "stance": stance, "weight": weight, "version": self.policy_version if stance else None}
        params.update({f"policy_{name}": getattr(self.policy, name) if stance else None for name in POLICY_FIELDS})
        session.execute(text("""INSERT INTO public.report_events(report_id, actor_id, action,
            previous_status, new_status, supporters, disputes, occurred_at, clearance_id,
            clearance_previous_status, clearance_new_status, clearance_supporters, clearance_disputes,
            stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
            policy_support_ratio, policy_maximum_vote_weight)
            VALUES (:report, :actor, :action, :previous, :status, :supporters, :disputes, :when,
            :clearance, :clearance_previous, :clearance_status, :clearance_supporters, :clearance_disputes,
            :stance, :weight, :version, :policy_minimum_supporters, :policy_minimum_weight,
            :policy_support_ratio, :policy_maximum_vote_weight)"""), params)

    def create_report(self, author_id, body, submitted_at, key):
        digest = payload_digest(body)
        with self.database.transaction() as session:
            self._actor(session, author_id)
            place = self._row(session, "SELECT id FROM public.buildings WHERE id=:id AND campus_id=:campus FOR SHARE", id=body.place_id, campus=PILOT)
            if place is None:
                raise ContributionTargetMissing()
            existing = self._row(session, """SELECT id, payload_digest FROM public.barrier_reports
                WHERE author_id=:actor AND building_id=:place AND idempotency_key=:key""", actor=author_id, place=body.place_id, key=key)
            if existing:
                if existing["payload_digest"] != digest:
                    raise IdempotencyConflict()
                return self._report(session, existing["id"])
            self._time(body, submitted_at)
            report_id = uuid4()
            session.execute(text("""INSERT INTO public.barrier_reports(id, building_id, author_id,
                barrier_type, description, observed_at, submitted_at, idempotency_key, payload_digest)
                VALUES (:id, :place, :actor, :type, :description, :observed, :submitted, :key, :digest)"""),
                {"id": report_id, "place": body.place_id, "actor": author_id, "type": body.barrier_type,
                 "description": body.description, "observed": body.observed_at, "submitted": submitted_at, "key": key, "digest": digest})
            self._evidence(session, "barrier_report_evidence", "report_id", report_id, body.evidence_urls)
            result = self._report(session, report_id)
            self._event(session, report=report_id, actor=author_id, action="report_created", previous=None,
                        status=result.public.status, counts=result.public.community, when=submitted_at)
            return result

    def create_clearance(self, report_id, author_id, body, submitted_at, key):
        digest = payload_digest(body)
        with self.database.transaction() as session:
            self._actor(session, author_id)
            report = self._lock_report(session, report_id)
            existing = self._row(session, """SELECT id, payload_digest FROM public.clearance_observations
                WHERE author_id=:actor AND report_id=:report AND idempotency_key=:key""", actor=author_id, report=report_id, key=key)
            if existing:
                if existing["payload_digest"] != digest:
                    raise IdempotencyConflict()
                return self._clearance(session, report_id, existing["id"])
            self._time(body, submitted_at, report["observed_at"])
            clearance_id = uuid4()
            session.execute(text("""INSERT INTO public.clearance_observations(id, report_id, report_observed_at,
                author_id, description, observed_at, submitted_at, idempotency_key, payload_digest)
                VALUES (:id, :report, :parent_time, :actor, :description, :observed, :submitted, :key, :digest)"""),
                {"id": clearance_id, "report": report_id, "parent_time": report["observed_at"], "actor": author_id,
                 "description": body.description, "observed": body.observed_at, "submitted": submitted_at, "key": key, "digest": digest})
            self._evidence(session, "clearance_evidence", "clearance_id", clearance_id, body.evidence_urls)
            result = self._clearance(session, report_id, clearance_id)
            parent = self._report(session, report_id).public
            self._event(session, report=report_id, actor=author_id, action="clearance_submitted", previous=report["status"],
                        status=parent.status, counts=parent.community, clearance=clearance_id,
                        clearance_status=result.public.status, clearance_counts=result.public.community)
            return result

    def _check_policy(self, session, report_id, policy):
        if self.policy is None or self.policy_version is None or self.policy != policy:
            raise PolicyUnavailable()
        rows = session.execute(text("""SELECT policy_version, policy_minimum_supporters,
            policy_minimum_weight, policy_support_ratio, policy_maximum_vote_weight
            FROM public.report_votes WHERE report_id=:id UNION ALL
            SELECT policy_version, policy_minimum_supporters, policy_minimum_weight,
            policy_support_ratio, policy_maximum_vote_weight FROM public.clearance_votes WHERE report_id=:id"""), {"id": report_id}).mappings()
        for row in rows:
            snapshot = TrustPolicy.model_validate({name: row[f"policy_{name}"] for name in POLICY_FIELDS})
            if row["policy_version"] != self.policy_version or snapshot != policy:
                # Policy migration/reaggregation requires a separate reviewed task.
                raise PolicyConflict()

    def _votes(self, session, table, column, target):
        rows = session.execute(text(f"SELECT voter_id, stance, weight FROM public.{table} WHERE {column}=:id"), {"id": target}).mappings()
        return [VoteSnapshot(r["voter_id"], VoteStance(r["stance"]), float(r["weight"])) for r in rows]

    def _refresh(self, session, report):
        states = session.execute(text("SELECT status FROM public.clearance_observations WHERE report_id=:id"), {"id": report["id"]}).scalars().all()
        status, counts = derive_report_status(self._votes(session, "report_votes", "report_id", report["id"]),
            author_id=report["author_id"], policy=self.policy, clearance_states=states)
        session.execute(text("UPDATE public.barrier_reports SET status=:status WHERE id=:id"), {"id": report["id"], "status": status})
        return status, counts

    def _cast(self, report_id, actor, stance, policy, clearance_id=None):
        with self.database.transaction() as session:
            weight = self._actor(session, actor, policy)
            report = self._lock_report(session, report_id)
            self._check_policy(session, report_id, policy)
            clearing = None
            if clearance_id is not None:
                clearing = self._row(session, "SELECT * FROM public.clearance_observations WHERE id=:id AND report_id=:report FOR UPDATE", id=clearance_id, report=report_id)
                if clearing is None:
                    raise ContributionTargetMissing()
            author = clearing["author_id"] if clearing else report["author_id"]
            if author == actor:
                raise ContributionDenied()
            table = "clearance_votes" if clearing else "report_votes"
            target_column = "clearance_id" if clearing else "report_id"
            author_column = "clearance_author_id" if clearing else "report_author_id"
            target = clearance_id if clearing else report_id
            params = {"target": target, "author": author, "actor": actor, "stance": stance,
                      "weight": weight, "version": self.policy_version, "when": utc_now(), "report": report_id}
            params.update({f"policy_{name}": getattr(policy, name) for name in POLICY_FIELDS})
            columns = [target_column, author_column, "voter_id", "stance", "weight", "policy_version", "updated_at"]
            values = [":target", ":author", ":actor", ":stance", ":weight", ":version", ":when"]
            if clearing:
                columns.append("report_id")
                values.append(":report")
            columns.extend(f"policy_{name}" for name in POLICY_FIELDS)
            values.extend(f":policy_{name}" for name in POLICY_FIELDS)
            updates = ", ".join(f"{name}=EXCLUDED.{name}" for name in columns if name not in (target_column, "voter_id"))
            session.execute(text(f"INSERT INTO public.{table} ({', '.join(columns)}) VALUES ({', '.join(values)}) ON CONFLICT ({target_column}, voter_id) DO UPDATE SET {updates}"), params)
            clearance_status = clearance_counts = None
            if clearing:
                clearance_status, clearance_counts = aggregate_votes(self._votes(session, table, target_column, target), author_id=author, policy=policy)
                session.execute(text("UPDATE public.clearance_observations SET status=:status WHERE id=:id"), {"id": target, "status": clearance_status})
            status, counts = self._refresh(session, report)
            self._event(session, report=report_id, actor=actor, action="clearance_vote_updated" if clearing else "vote_updated",
                        previous=report["status"], status=status, counts=counts, stance=stance, weight=weight,
                        clearance=clearance_id, clearance_previous=clearing["status"] if clearing else None,
                        clearance_status=clearance_status, clearance_counts=clearance_counts)
            return self._report(session, report_id)

    def cast_vote(self, report_id, voter_id, stance, weight, policy):
        # The route's earlier weight is advisory only; reload it under the lock.
        return self._cast(report_id, voter_id, stance, policy)

    def cast_clearance_vote(self, report_id, clearance_id, voter_id, stance, weight, policy):
        return self._cast(report_id, voter_id, stance, policy, clearance_id)
