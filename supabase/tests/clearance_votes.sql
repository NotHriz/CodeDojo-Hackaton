-- Illustrative test policy and fictional records, not deployed trust settings.
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
INSERT INTO public.campuses (id, name) VALUES ('clear-vote-campus', 'Fictional clearing vote campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('clear-vote-building', 'clear-vote-campus', 'Fictional clearing vote building', 'study', 3.25, 101.73);
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest) VALUES (
    '00000000-0000-0000-0000-000000000001', 'clear-vote-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional first barrier',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000003', repeat('a', 64)
), (
    '00000000-0000-0000-0000-000000000009', 'clear-vote-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional other barrier',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000010', repeat('b', 64)
);
INSERT INTO public.clearance_observations (id, report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest) VALUES (
    '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000005',
    'Fictional first clearing claim', now() - interval '1 hour',
    '00000000-0000-0000-0000-000000000006', repeat('c', 64)
), (
    '00000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000001',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000005',
    'Fictional second clearing claim', now() - interval '1 hour',
    '00000000-0000-0000-0000-000000000007', repeat('d', 64)
);

-- The original barrier reporter may vote on another member's clearing claim.
INSERT INTO public.clearance_votes (clearance_id, report_id, clearance_author_id, voter_id,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight) VALUES (
    '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000002',
    'corroborate', 2, 'fictional-test-policy-v1', 3, 3, 0.67, 2
);

SELECT pg_temp.expect_error($q$INSERT INTO public.clearance_votes SELECT * FROM public.clearance_votes$q$, '23505');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET voter_id = clearance_author_id$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET clearance_author_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET report_id = '00000000-0000-0000-0000-000000000009'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET clearance_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET stance = 'agree'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET weight = 0.99$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET weight = 2.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET weight = 'NaN'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET weight = 'Infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET weight = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_version = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_version = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_minimum_supporters = 1$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_minimum_supporters = 21$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_minimum_weight = 0$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_minimum_weight = 41$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_support_ratio = 0.5$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_support_ratio = 1.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_maximum_vote_weight = 2.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET policy_maximum_vote_weight = 1.5$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_votes SET updated_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET author_id = '00000000-0000-0000-0000-000000000099'$q$, '23001');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET report_id = '00000000-0000-0000-0000-000000000009'$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.clearance_observations$q$, '23001');

-- The same member may vote independently on another clearing observation.
INSERT INTO public.clearance_votes (clearance_id, report_id, clearance_author_id, voter_id,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight)
SELECT '00000000-0000-0000-0000-000000000008', report_id, clearance_author_id, voter_id,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight FROM public.clearance_votes;

INSERT INTO public.clearance_votes (clearance_id, report_id, clearance_author_id, voter_id,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight)
SELECT clearance_id, report_id, clearance_author_id, voter_id, 'dispute', 1.25,
    'fictional-test-policy-v2', 2, 2, 0.75, 1.5 FROM public.clearance_votes
WHERE clearance_id = '00000000-0000-0000-0000-000000000004'
ON CONFLICT (clearance_id, voter_id) DO UPDATE SET
    stance = EXCLUDED.stance, weight = EXCLUDED.weight,
    policy_version = EXCLUDED.policy_version,
    policy_minimum_supporters = EXCLUDED.policy_minimum_supporters,
    policy_minimum_weight = EXCLUDED.policy_minimum_weight,
    policy_support_ratio = EXCLUDED.policy_support_ratio,
    policy_maximum_vote_weight = EXCLUDED.policy_maximum_vote_weight,
    updated_at = EXCLUDED.updated_at;

DO $$
BEGIN
    IF (SELECT count(*) FROM public.clearance_votes) <> 2 OR NOT EXISTS (
        SELECT 1 FROM public.clearance_votes
        WHERE clearance_id = '00000000-0000-0000-0000-000000000004'
            AND stance = 'dispute' AND weight = 1.25 AND policy_version = 'fictional-test-policy-v2'
            AND policy_minimum_supporters = 2 AND policy_minimum_weight = 2
            AND policy_support_ratio = 0.75 AND policy_maximum_vote_weight = 1.5
            AND updated_at = transaction_timestamp()
    ) OR NOT EXISTS (
        SELECT 1 FROM public.clearance_votes
        WHERE clearance_id = '00000000-0000-0000-0000-000000000008' AND stance = 'corroborate'
    ) THEN
        RAISE EXCEPTION 'Vote replacement must update only the selected observation and snapshot';
    END IF;
    IF EXISTS (SELECT 1 FROM public.barrier_reports WHERE status <> 'unverified')
        OR EXISTS (SELECT 1 FROM public.clearance_observations WHERE status <> 'unverified') THEN
        RAISE EXCEPTION 'Vote storage alone must not activate aggregation or resolve reports';
    END IF;
END;
$$;
RESET ROLE;

DO $$
DECLARE
    role_name text;
    operation text;
BEGIN
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.clearance_votes'::regclass) THEN
        RAISE EXCEPTION 'RLS disabled on clearance_votes';
    END IF;
    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
            IF has_table_privilege(role_name, 'public.clearance_votes', operation) THEN
                RAISE EXCEPTION '% has unexpected % access to clearing votes', role_name, operation;
            END IF;
        END LOOP;
    END LOOP;
END;
$$;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT * FROM public.clearance_votes', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT voter_id, weight FROM public.clearance_votes', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Clearing vote checks passed (fixtures rolled back).'
