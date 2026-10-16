-- The explicit policy below is an illustrative test input, not an active policy.
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
INSERT INTO public.campuses (id, name) VALUES ('vote-campus', 'Fictional vote campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('vote-building', 'vote-campus', 'Fictional vote building', 'study', 3.25, 101.73);
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest) VALUES (
    '00000000-0000-0000-0000-000000000001', 'vote-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional test obstruction',
    now(), '00000000-0000-0000-0000-000000000003', repeat('a', 64)
);
INSERT INTO public.report_votes (report_id, report_author_id, voter_id, stance, weight,
    policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight) VALUES (
    '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000004', 'corroborate', 2, 'fictional-test-policy-v1', 3, 3, 0.67, 2
);

SELECT pg_temp.expect_error($q$INSERT INTO public.report_votes SELECT * FROM public.report_votes$q$, '23505');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET voter_id = report_author_id$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET report_author_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET report_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET stance = 'agree'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET weight = 0.99$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET weight = 2.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET weight = 'NaN'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET weight = 'Infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET weight = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_version = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_version = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_minimum_supporters = 1$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_minimum_supporters = 21$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_minimum_weight = 0$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_minimum_weight = 41$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_support_ratio = 0.5$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_support_ratio = 1.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_maximum_vote_weight = 2.01$q$, '23514');
-- Even a globally valid weight must obey this vote's narrower explicit policy.
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET policy_maximum_vote_weight = 1.5$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.report_votes SET updated_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET author_id = '00000000-0000-0000-0000-000000000099'$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.barrier_reports$q$, '23001');

-- A changed stance replaces the member's row rather than counting another vote.
INSERT INTO public.report_votes (report_id, report_author_id, voter_id, stance, weight,
    policy_version, policy_minimum_supporters, policy_minimum_weight,
    policy_support_ratio, policy_maximum_vote_weight)
SELECT report_id, report_author_id, voter_id, 'dispute', 1.25,
    'fictional-test-policy-v2', 2, 2, 0.75, 1.5 FROM public.report_votes
ON CONFLICT (report_id, voter_id) DO UPDATE SET
    stance = EXCLUDED.stance, weight = EXCLUDED.weight,
    policy_version = EXCLUDED.policy_version,
    policy_minimum_supporters = EXCLUDED.policy_minimum_supporters,
    policy_minimum_weight = EXCLUDED.policy_minimum_weight,
    policy_support_ratio = EXCLUDED.policy_support_ratio,
    policy_maximum_vote_weight = EXCLUDED.policy_maximum_vote_weight,
    updated_at = EXCLUDED.updated_at;

DO $$
BEGIN
    IF (SELECT count(*) FROM public.report_votes) <> 1 OR NOT EXISTS (
        SELECT 1 FROM public.report_votes WHERE stance = 'dispute' AND weight = 1.25
            AND policy_version = 'fictional-test-policy-v2' AND policy_minimum_supporters = 2
            AND policy_minimum_weight = 2 AND policy_support_ratio = 0.75
            AND policy_maximum_vote_weight = 1.5 AND updated_at = transaction_timestamp()
    ) THEN
        RAISE EXCEPTION 'Vote replacement must preserve one row and update its full snapshot';
    END IF;
    IF (SELECT status FROM public.barrier_reports) <> 'unverified' THEN
        RAISE EXCEPTION 'Vote storage must not activate an aggregation policy';
    END IF;
END;
$$;
RESET ROLE;

DO $$
DECLARE
    role_name text;
    operation text;
BEGIN
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.report_votes'::regclass) THEN
        RAISE EXCEPTION 'RLS disabled on report_votes';
    END IF;
    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
            IF has_table_privilege(role_name, 'public.report_votes', operation) THEN
                RAISE EXCEPTION '% has unexpected % access to votes', role_name, operation;
            END IF;
        END LOOP;
    END LOOP;
END;
$$;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT * FROM public.report_votes', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT voter_id, weight FROM public.report_votes', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Report vote checks passed (fixtures rolled back).'
