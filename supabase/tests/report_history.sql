BEGIN;
CREATE FUNCTION pg_temp.expect_error(statement text, expected_state text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = expected_state THEN RETURN; END IF;
        RAISE;
    END;
    RAISE EXCEPTION 'Expected SQLSTATE % for %', expected_state, statement;
END;
$$;

SET LOCAL ROLE service_role;
INSERT INTO public.campuses (id, name) VALUES ('history-campus', 'Fictional history campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('history-building', 'history-campus', 'Fictional history building', 'study', 3.25, 101.73);
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest)
SELECT id, 'history-building', '00000000-0000-0000-0000-000000000002',
    'obstruction', 'Fictional history barrier', now() - interval '1 hour', id, repeat('a', 64)
FROM unnest(ARRAY['00000000-0000-0000-0000-000000000001'::uuid,
    '00000000-0000-0000-0000-000000000009'::uuid]) AS ids(id);
INSERT INTO public.clearance_observations (id, report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest) VALUES (
    '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',
    now() - interval '1 hour', '00000000-0000-0000-0000-000000000005',
    'Fictional clearing claim', now(), '00000000-0000-0000-0000-000000000006', repeat('b', 64)
);
INSERT INTO public.report_events (report_id, action, new_status, supporters, disputes, actor_id)
VALUES ('00000000-0000-0000-0000-000000000001', 'report_created', 'unverified', 0, 0,
    '00000000-0000-0000-0000-000000000002');
INSERT INTO public.report_events (report_id, action, previous_status, new_status, supporters, disputes,
    actor_id, clearance_id, clearance_new_status, clearance_supporters, clearance_disputes)
VALUES ('00000000-0000-0000-0000-000000000001', 'clearance_submitted', 'unverified', 'unverified', 0, 0,
    '00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000004', 'unverified', 0, 0);

-- Explicit illustrative policy only; inserting history does not aggregate statuses.
INSERT INTO public.report_events (report_id, action, previous_status, new_status, supporters, disputes,
    actor_id, stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight)
VALUES ('00000000-0000-0000-0000-000000000001', 'vote_updated', 'unverified', 'unverified', 1, 0,
    '00000000-0000-0000-0000-000000000007', 'corroborate', 1, 'fictional-test-policy-v1', 3, 3, 0.67, 2);
INSERT INTO public.report_events (report_id, action, previous_status, new_status, supporters, disputes,
    actor_id, clearance_id, clearance_previous_status, clearance_new_status, clearance_supporters, clearance_disputes,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight)
VALUES ('00000000-0000-0000-0000-000000000001', 'clearance_vote_updated', 'unverified', 'unverified', 1, 0,
    '00000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000004', 'unverified', 'disputed', 0, 1,
    'dispute', 1.25, 'fictional-test-policy-v2', 2, 2, 0.75, 1.5);

DO $$
BEGIN
    IF (SELECT array_agg(action ORDER BY occurred_at, sequence) FROM public.report_events) <>
        ARRAY['report_created', 'clearance_submitted', 'vote_updated', 'clearance_vote_updated'] THEN
        RAISE EXCEPTION 'Equal-time events must retain insertion order';
    END IF;
    IF (SELECT count(DISTINCT policy_version) FROM public.report_events) <> 2 THEN
        RAISE EXCEPTION 'Historical policy snapshots must remain independent';
    END IF;
END;
$$;
SELECT pg_temp.expect_error('UPDATE public.report_events SET supporters = 99', '42501');
SELECT pg_temp.expect_error('DELETE FROM public.report_events', '42501');
SELECT pg_temp.expect_error('TRUNCATE public.report_events', '42501');
RESET ROLE;

SELECT pg_temp.expect_error($q$UPDATE public.report_events SET supporters = -1$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET action = 'unknown'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET new_status = 'confirmed'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET previous_status = NULL WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET occurred_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET actor_id = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET clearance_id = NULL WHERE action = 'clearance_submitted'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET report_id = '00000000-0000-0000-0000-000000000009' WHERE action = 'clearance_submitted'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET policy_version = NULL WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET policy_version = ' ' WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET weight = 2.1 WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET weight = 'NaN' WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET policy_support_ratio = 0.5 WHERE action = 'vote_updated'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_events SET weight = 1 WHERE action = 'report_created'$q$, '23514');
SELECT pg_temp.expect_error($q$
    INSERT INTO public.report_events (report_id, action, new_status, supporters, disputes, actor_id)
    SELECT report_id, action, new_status, supporters, disputes, actor_id FROM public.report_events WHERE action = 'report_created'
$q$, '23505');
SELECT pg_temp.expect_error($q$
    INSERT INTO public.report_events (report_id, action, previous_status, new_status, supporters, disputes,
        actor_id, clearance_id, clearance_new_status, clearance_supporters, clearance_disputes)
    SELECT report_id, action, previous_status, new_status, supporters, disputes,
        actor_id, clearance_id, clearance_new_status, clearance_supporters, clearance_disputes
    FROM public.report_events WHERE action = 'clearance_submitted'
$q$, '23505');

-- A failed mutation rolls its newly appended event back with its data changes.
DO $$
DECLARE prior_count bigint;
BEGIN
    SELECT count(*) INTO prior_count FROM public.report_events;
    BEGIN
        INSERT INTO public.report_events (report_id, action, new_status, supporters, disputes, actor_id)
        VALUES ('00000000-0000-0000-0000-000000000009', 'report_created', 'unverified', 0, 0,
            '00000000-0000-0000-0000-000000000002');
        UPDATE public.barrier_reports SET status = 'invalid';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    IF (SELECT count(*) FROM public.report_events) <> prior_count THEN
        RAISE EXCEPTION 'Failed transaction retained an audit event';
    END IF;
END;
$$;

DO $$
DECLARE role_name text; operation text;
BEGIN
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.report_events'::regclass) THEN
        RAISE EXCEPTION 'RLS disabled on history';
    END IF;
    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
            IF has_table_privilege(role_name, 'public.report_events', operation) THEN
                RAISE EXCEPTION '% has unexpected % history access', role_name, operation;
            END IF;
        END LOOP;
        IF has_sequence_privilege(role_name, 'public.report_events_sequence_seq', 'USAGE') THEN
            RAISE EXCEPTION '% has unexpected sequence access', role_name;
        END IF;
    END LOOP;
END;
$$;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT * FROM public.report_events', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT actor_id, weight FROM public.report_events', '42501');
RESET ROLE;
ROLLBACK;
\echo 'Report history checks passed (fixtures rolled back).'
