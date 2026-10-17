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
-- A fictional identity, not a Supabase account or deployable seed.
INSERT INTO public.contributor_state (user_id)
VALUES ('00000000-0000-0000-0000-000000000001');
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.contributor_state WHERE can_contribute AND vote_weight = 1
            AND restriction_reason IS NULL AND updated_at = transaction_timestamp()
    ) THEN
        RAISE EXCEPTION 'New contributor state must default to neutral eligibility';
    END IF;
END;
$$;
SELECT pg_temp.expect_error($q$INSERT INTO public.contributor_state SELECT * FROM public.contributor_state$q$, '23505');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET can_contribute = false$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET restriction_reason = 'reason while eligible'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET can_contribute = false, restriction_reason = ' '$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = 0.99$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = 2.01$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = 'NaN'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = 'Infinity'$q$, '23514');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET can_contribute = NULL$q$, '23502');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET updated_at = 'infinity'$q$, '23514');

-- Restriction does not silently change weight or erase previous contributions.
UPDATE public.contributor_state SET can_contribute = false,
    restriction_reason = 'Fictional explicit restriction for SQL testing', updated_at = now();
SELECT pg_temp.expect_error('DELETE FROM public.contributor_state', '42501');
SELECT pg_temp.expect_error('TRUNCATE public.contributor_state', '42501');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET can_contribute = true$q$, '23514');
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.contributor_state WHERE NOT can_contribute
        AND vote_weight = 1 AND restriction_reason IS NOT NULL) THEN
        RAISE EXCEPTION 'Restricted state must remain explicit with neutral weight intact';
    END IF;
END;
$$;
UPDATE public.contributor_state SET can_contribute = true, restriction_reason = NULL,
    vote_weight = 2, updated_at = now();
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.contributor_state WHERE can_contribute
        AND vote_weight = 2 AND restriction_reason IS NULL) THEN
        RAISE EXCEPTION 'Explicit state restoration or upper weight boundary failed';
    END IF;
END;
$$;
RESET ROLE;

DO $$
DECLARE role_name text; operation text;
BEGIN
    IF NOT (SELECT relrowsecurity FROM pg_class WHERE oid = 'public.contributor_state'::regclass) THEN
        RAISE EXCEPTION 'RLS disabled on contributor state';
    END IF;
    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'] LOOP
            IF has_table_privilege(role_name, 'public.contributor_state', operation) THEN
                RAISE EXCEPTION '% has unexpected % contributor access', role_name, operation;
            END IF;
        END LOOP;
    END LOOP;
END;
$$;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT * FROM public.contributor_state', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT vote_weight, restriction_reason FROM public.contributor_state', '42501');
SELECT pg_temp.expect_error($q$UPDATE public.contributor_state SET vote_weight = 2$q$, '42501');
RESET ROLE;
ROLLBACK;
\echo 'Contributor state checks passed (fixtures rolled back).'
