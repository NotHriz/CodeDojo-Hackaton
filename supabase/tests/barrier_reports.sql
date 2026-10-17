-- Creation constraints only; not a CommunityRepository implementation.
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
INSERT INTO public.campuses (id, name) VALUES ('report-campus', 'Fictional report campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude) VALUES
    ('report-building', 'report-campus', 'Fictional report building', 'study', 3.25, 101.73),
    ('other-building', 'report-campus', 'Fictional other building', 'study', 3.25, 101.73);
INSERT INTO public.barrier_reports (
    id, building_id, author_id, barrier_type, description, observed_at, idempotency_key, payload_digest
) VALUES (
    '00000000-0000-0000-0000-000000000001', 'report-building',
    '00000000-0000-0000-0000-000000000002', 'obstruction', 'Fictional ramp obstruction',
    now() - interval '1 hour', '00000000-0000-0000-0000-000000000003', repeat('a', 64)
);
INSERT INTO public.barrier_report_evidence (report_id, position, url) VALUES
    ('00000000-0000-0000-0000-000000000001', 2, 'https://example.com/third.jpg'),
    ('00000000-0000-0000-0000-000000000001', 0, 'https://example.com/first.jpg'),
    ('00000000-0000-0000-0000-000000000001', 1, 'https://example.com/second.jpg');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.barrier_reports WHERE status = 'unverified'
            AND submitted_at = transaction_timestamp()
            AND observed_at = transaction_timestamp() - interval '1 hour'
    ) THEN
        RAISE EXCEPTION 'Reports must start unverified and preserve separate observation/submission times';
    END IF;
    IF (SELECT array_agg(url ORDER BY position) FROM public.barrier_report_evidence) <>
        ARRAY['https://example.com/first.jpg', 'https://example.com/second.jpg', 'https://example.com/third.jpg'] THEN
        RAISE EXCEPTION 'Evidence order was lost';
    END IF;
END;
$$;

-- A retry's unique scope includes actor and building, independently of payload.
SELECT pg_temp.expect_error($q$
    INSERT INTO public.barrier_reports (building_id, author_id, barrier_type, description,
        observed_at, idempotency_key, payload_digest)
    SELECT building_id, author_id, barrier_type, description, observed_at,
        idempotency_key, repeat('b', 64) FROM public.barrier_reports
$q$, '23505');

-- The same key on a different target or from a different actor is independent.
INSERT INTO public.barrier_reports (building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest)
SELECT 'other-building', author_id, barrier_type, description, observed_at, idempotency_key, payload_digest
FROM public.barrier_reports WHERE id = '00000000-0000-0000-0000-000000000001';
INSERT INTO public.barrier_reports (building_id, author_id, barrier_type, description,
    observed_at, idempotency_key, payload_digest)
SELECT building_id, '00000000-0000-0000-0000-000000000004', barrier_type, description,
    observed_at, idempotency_key, payload_digest
FROM public.barrier_reports WHERE id = '00000000-0000-0000-0000-000000000001';

UPDATE public.barrier_reports SET observed_at = submitted_at + interval '5 minutes';
RESET ROLE;
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET observed_at = submitted_at + interval '5 minutes 1 second'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET observed_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET submitted_at = 'infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET observed_at = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET author_id = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET idempotency_key = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET payload_digest = 'not-a-digest'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET payload_digest = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET building_id = 'missing' WHERE id = '00000000-0000-0000-0000-000000000001'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET barrier_type = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET barrier_type = repeat('x', 65)$q$, '22001');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET description = ''$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET description = repeat('x', 2001)$q$, '22001');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_reports SET status = 'confirmed'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET position = 3$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET position = -1$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET url = 'file:///private'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET url = 'https://'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET url = 'https://example.com/a b'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.barrier_report_evidence SET report_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$INSERT INTO public.barrier_report_evidence SELECT * FROM public.barrier_report_evidence$q$, '23505');
SELECT pg_temp.expect_error($q$DELETE FROM public.barrier_reports WHERE id = '00000000-0000-0000-0000-000000000001'$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.buildings WHERE id = 'other-building'$q$, '23001');

DO $$
DECLARE
    table_name text;
    role_name text;
    operation text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['barrier_reports', 'barrier_report_evidence'] LOOP
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
SELECT pg_temp.expect_error('SELECT author_id, payload_digest FROM public.barrier_reports', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT * FROM public.barrier_report_evidence', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Barrier report checks passed (fixtures rolled back).'
