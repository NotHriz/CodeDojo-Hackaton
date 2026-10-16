-- Run only against the disposable database created by run-local.ps1.
BEGIN;

CREATE FUNCTION pg_temp.expect_error(statement text, expected_state text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = expected_state THEN
            RETURN;
        END IF;
        RAISE;
    END;
    RAISE EXCEPTION 'Expected SQLSTATE % for %', expected_state, statement;
END;
$$;

SET LOCAL ROLE service_role;
INSERT INTO public.campuses (id, name) VALUES ('test-campus', 'Fictional test campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude)
VALUES ('test-building', 'test-campus', 'Fictional test building', 'study', 3.25, 101.73);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.buildings
        WHERE id = 'test-building' AND step_free_entrance = 'unknown'
            AND accessible_toilet = 'unknown' AND designated_parking = 'unknown'
            AND description IS NULL
    ) THEN
        RAISE EXCEPTION 'Missing observations must default to unknown';
    END IF;
END;
$$;
RESET ROLE;

SELECT pg_temp.expect_error($q$UPDATE public.buildings SET latitude = 91$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET latitude = -91$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET longitude = 181$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET longitude = -181$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET latitude = 'NaN'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET longitude = 'Infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET step_free_entrance = 'maybe'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET accessible_toilet = 'true'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET designated_parking = 'YES'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET accessible_toilet = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET latitude = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET campus_id = 'missing'$q$, '23503');
SELECT pg_temp.expect_error($q$DELETE FROM public.campuses WHERE id = 'test-campus'$q$, '23001');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET name = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET category = ''$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET id = ''$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.buildings SET id = repeat('x', 129)$q$, '22001');
SELECT pg_temp.expect_error($q$
    INSERT INTO public.buildings SELECT * FROM public.buildings
$q$, '23505');

UPDATE public.buildings SET step_free_entrance = 'yes', accessible_toilet = 'no',
    designated_parking = 'unknown', latitude = -90, longitude = 180;
UPDATE public.buildings SET latitude = 90, longitude = -180;

DO $$
DECLARE
    role_name text;
    table_name text;
    operation text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['campuses', 'buildings'] LOOP
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
SELECT pg_temp.expect_error('SELECT * FROM public.buildings', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT * FROM public.buildings', '42501');
RESET ROLE;

ROLLBACK;
\echo 'Building foundation checks passed (fixtures rolled back).'
