-- Disposable fixtures only; no real campus observations.
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
INSERT INTO public.campuses (id, name) VALUES ('evidence-campus', 'Fictional evidence campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('evidence-building', 'evidence-campus', 'Fictional evidence building', 'study', 3.25, 101.73);
INSERT INTO public.entrances (id, building_id, description)
VALUES ('00000000-0000-0000-0000-000000000001', 'evidence-building', 'Fictional east entrance');
INSERT INTO public.facility_observations (id, building_id, facility, value)
VALUES ('00000000-0000-0000-0000-000000000002', 'evidence-building', 'step_free_entrance', 'yes');
INSERT INTO public.facility_observations (building_id, facility, value, observed_at, source, notes)
VALUES ('evidence-building', 'accessible_toilet', 'unknown', '2026-10-16 12:00:00+08', 'Fictional test source', 'Test note');
INSERT INTO public.entrance_photos (entrance_id, position, url)
VALUES ('00000000-0000-0000-0000-000000000001', 0, 'https://example.com/entrance.jpg');
INSERT INTO public.observation_evidence (observation_id, position, url) VALUES
    ('00000000-0000-0000-0000-000000000002', 1, 'https://example.com/second.jpg'),
    ('00000000-0000-0000-0000-000000000002', 0, 'https://example.com/first.jpg');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.entrances WHERE latitude IS NULL AND longitude IS NULL) THEN
        RAISE EXCEPTION 'Unobserved entrance coordinates must remain null';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.facility_observations
        WHERE facility = 'step_free_entrance' AND observed_at IS NULL AND source IS NULL
            AND notes IS NULL AND recorded_at = transaction_timestamp()
    ) THEN
        RAISE EXCEPTION 'Observation time/source must not be fabricated from ingestion time';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.facility_observations
        WHERE facility = 'accessible_toilet' AND observed_at = '2026-10-16 04:00:00+00'::timestamptz
    ) THEN
        RAISE EXCEPTION 'Observation timestamp did not preserve its instant';
    END IF;
    IF (SELECT step_free_entrance FROM public.buildings WHERE id = 'evidence-building') <> 'unknown' THEN
        RAISE EXCEPTION 'An observation must not silently select an aggregation policy';
    END IF;
    IF (SELECT array_agg(url ORDER BY position) FROM public.observation_evidence) <>
        ARRAY['https://example.com/first.jpg', 'https://example.com/second.jpg'] THEN
        RAISE EXCEPTION 'Evidence order must be recoverable independently of insertion order';
    END IF;
END;
$$;
UPDATE public.entrances SET latitude = -90, longitude = 180;
UPDATE public.entrances SET latitude = 90, longitude = -180;
RESET ROLE;

SELECT pg_temp.expect_error($q$UPDATE public.entrances SET latitude = NULL$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET latitude = 91$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET longitude = -181$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET latitude = 'NaN'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET longitude = 'Infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET description = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET description = repeat('x', 2001)$q$, '22001');
SELECT pg_temp.expect_error($q$UPDATE public.entrances SET building_id = 'missing'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.facility_observations SET building_id = 'missing'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.facility_observations SET facility = 'lift'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.facility_observations SET value = 'maybe'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.facility_observations SET value = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.entrance_photos SET url = 'file:///private.jpg'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET url = 'javascript:alert(1)'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET url = 'https://'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET url = 'https://example.com/a b'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET url = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET position = -1$q$, '23514');
SELECT pg_temp.expect_error($q$INSERT INTO public.observation_evidence SELECT * FROM public.observation_evidence$q$, '23505');
SELECT pg_temp.expect_error($q$UPDATE public.observation_evidence SET observation_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$UPDATE public.entrance_photos SET entrance_id = '00000000-0000-0000-0000-000000000099'$q$, '23503');
SELECT pg_temp.expect_error($q$DELETE FROM public.buildings WHERE id = 'evidence-building'$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.entrances$q$, '23001');
SELECT pg_temp.expect_error($q$DELETE FROM public.facility_observations WHERE facility = 'step_free_entrance'$q$, '23001');

DO $$
DECLARE
    table_name text;
    role_name text;
    operation text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['entrances', 'facility_observations', 'entrance_photos', 'observation_evidence'] LOOP
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
SELECT pg_temp.expect_error('SELECT * FROM public.facility_observations', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT * FROM public.observation_evidence', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Place evidence checks passed (fixtures rolled back).'
