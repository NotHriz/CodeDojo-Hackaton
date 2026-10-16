-- Fictional test observations; all changes roll back.
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
INSERT INTO public.campuses (id, name) VALUES ('clearance-campus', 'Fictional clearance campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('clearance-building', 'clearance-campus', 'Fictional clearance building', 'study', 3.25, 101.73);
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest) VALUES (
    '00000000-0000-0000-0000-000000000001', 'clearance-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional ramp obstruction',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000003', repeat('a', 64)
), (
    '00000000-0000-0000-0000-000000000009', 'clearance-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional second obstruction',
    now() - interval '2 hours', '00000000-0000-0000-0000-000000000008', repeat('b', 64)
);
INSERT INTO public.clearance_observations (id, report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest)
SELECT '00000000-0000-0000-0000-000000000004', id, observed_at,
    '00000000-0000-0000-0000-000000000005', 'Fictional clearing claim',
    now() - interval '1 hour', '00000000-0000-0000-0000-000000000006', repeat('c', 64)
FROM public.barrier_reports WHERE id = '00000000-0000-0000-0000-000000000001';
INSERT INTO public.clearance_evidence (clearance_id, position, url) VALUES
    ('00000000-0000-0000-0000-000000000004', 2, 'https://example.com/third.jpg'),
    ('00000000-0000-0000-0000-000000000004', 0, 'https://example.com/first.jpg'),
    ('00000000-0000-0000-0000-000000000004', 1, 'https://example.com/second.jpg');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.clearance_observations WHERE status = 'unverified'
            AND submitted_at = transaction_timestamp()
            AND observed_at = transaction_timestamp() - interval '1 hour'
    ) OR EXISTS (SELECT 1 FROM public.barrier_reports WHERE status <> 'unverified') THEN
        RAISE EXCEPTION 'A clearing claim must preserve timestamps and leave its parent unresolved';
    END IF;
    IF (SELECT array_agg(url ORDER BY position) FROM public.clearance_evidence) <>
        ARRAY['https://example.com/first.jpg', 'https://example.com/second.jpg', 'https://example.com/third.jpg'] THEN
        RAISE EXCEPTION 'Clearing evidence order was lost';
    END IF;
END;
$$;

SELECT pg_temp.expect_error($q$
    INSERT INTO public.clearance_observations (report_id, report_observed_at, author_id,
        description, observed_at, idempotency_key, payload_digest)
    SELECT report_id, report_observed_at, author_id, description, observed_at,
        idempotency_key, repeat('d', 64) FROM public.clearance_observations
$q$, '23505');

-- Identical keys may be used for a different report or by a different member.
INSERT INTO public.clearance_observations (report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest)
SELECT '00000000-0000-0000-0000-000000000009', report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest FROM public.clearance_observations;
INSERT INTO public.clearance_observations (report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest)
SELECT report_id, report_observed_at, '00000000-0000-0000-0000-000000000007',
    description, observed_at, idempotency_key, payload_digest
FROM public.clearance_observations WHERE id = '00000000-0000-0000-0000-000000000004';

-- Equality satisfies the contract's "cannot predate" rule; the future bound is inclusive.
UPDATE public.clearance_observations SET observed_at = report_observed_at;
UPDATE public.clearance_observations SET observed_at = submitted_at + interval '5 minutes';
RESET ROLE;
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET observed_at = report_observed_at - interval '1 second'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET report_observed_at = report_observed_at - interval '1 hour'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET observed_at = submitted_at + interval '5 minutes 1 second'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET observed_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET submitted_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET observed_at = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET author_id = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET idempotency_key = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET payload_digest = 'bad'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET description = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET description = repeat('x', 2001)$q$, '22001');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET status = 'confirmed'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_observations SET report_id = '00000000-0000-0000-0000-000000000099' WHERE id = '00000000-0000-0000-0000-000000000004'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET observed_at = observed_at - interval '1 minute'$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.barrier_reports$q$, '23001');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET position = 3$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET position = -1$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET url = 'file:///private'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET url = 'https://'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET url = 'https://example.com/a b'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.clearance_evidence SET clearance_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$INSERT INTO public.clearance_evidence SELECT * FROM public.clearance_evidence$q$, '23505');
SELECT pg_temp.expect_error($q$DELETE FROM public.clearance_observations WHERE id = '00000000-0000-0000-0000-000000000004'$q$, '23001');

DO $$
DECLARE
    table_name text;
    role_name text;
    operation text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['clearance_observations', 'clearance_evidence'] LOOP
        IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = ('public.' || table_name)::regclass) THEN
            RAISE EXCEPTION 'RLS disabled on %', table_name;
        END IF;
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
                IF has_table_privilege(role_name, 'public.' || table_name, operation) THEN
                    RAISE EXCEPTION '% has unexpected % access to %', role_name, operation, table_name;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;
END;
$$;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT author_id, payload_digest FROM public.clearance_observations', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT * FROM public.clearance_evidence', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Clearing observation checks passed (fixtures rolled back).'
