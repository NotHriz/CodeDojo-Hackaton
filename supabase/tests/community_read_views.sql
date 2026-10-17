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
INSERT INTO public.campuses (id, name) VALUES
    ('read-campus', 'Fictional read campus'), ('other-campus', 'Fictional other campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude, step_free_entrance) VALUES
    ('read-building', 'read-campus', 'Fictional read building', 'study', 3.25, 101.73, 'yes'),
    ('other-building', 'other-campus', 'Fictional other building', 'study', 3.25, 101.73, 'unknown');
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, status, idempotency_key, payload_digest)
SELECT ('00000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
    CASE WHEN n = 5 THEN 'other-building' ELSE 'read-building' END,
    '00000000-0000-0000-0000-000000000010', 'obstruction', 'Fictional test warning',
    now() - interval '1 hour', status,
    ('00000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid, repeat('a', 64)
FROM (VALUES (1, 'unverified'), (2, 'community_corroborated'), (3, 'disputed'),
    (4, 'resolved'), (5, 'unverified')) AS fixtures(n, status);

INSERT INTO public.clearance_observations (id, report_id, report_observed_at, author_id,
    description, observed_at, idempotency_key, payload_digest)
SELECT ('00000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
    '00000000-0000-0000-0000-000000000001', now() - interval '1 hour',
    '00000000-0000-0000-0000-000000000011', 'Fictional clearing claim', now(),
    ('00000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid, repeat('b', 64)
FROM generate_series(20, 21) AS fixtures(n);

INSERT INTO public.report_votes (report_id, report_author_id, voter_id, stance, weight,
    policy_version, policy_minimum_supporters, policy_minimum_weight, policy_support_ratio, policy_maximum_vote_weight)
SELECT '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000010',
    ('00000000-0000-0000-0000-' || lpad(n::text, 12, '0'))::uuid,
    CASE WHEN n = 30 THEN 'corroborate' ELSE 'dispute' END,
    CASE WHEN n = 30 THEN 2 ELSE 1 END, 'fictional-test-policy', 3, 3, 0.67, 2
FROM generate_series(30, 31) AS fixtures(n);
INSERT INTO public.clearance_votes (clearance_id, report_id, clearance_author_id, voter_id,
    stance, weight, policy_version, policy_minimum_supporters, policy_minimum_weight, policy_support_ratio, policy_maximum_vote_weight)
VALUES ('00000000-0000-0000-0000-000000000020', '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000030',
    'corroborate', 2, 'fictional-test-policy', 3, 3, 0.67, 2);

DO $$
BEGIN
    IF (SELECT count(*) FROM public.building_active_warnings WHERE campus_id = 'read-campus') <> 3
        OR EXISTS (SELECT 1 FROM public.building_active_warnings WHERE status = 'resolved')
        OR NOT EXISTS (SELECT 1 FROM public.building_active_warnings WHERE campus_id = 'other-campus') THEN
        RAISE EXCEPTION 'Active warnings must retain all unresolved states and their real campus';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.buildings WHERE id = 'read-building' AND step_free_entrance = 'yes') THEN
        RAISE EXCEPTION 'Warnings must not alter facility summaries';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.report_community_counts
        WHERE report_id = '00000000-0000-0000-0000-000000000001' AND supporters = 1 AND disputes = 1)
        OR (SELECT count(*) FROM public.report_community_counts WHERE supporters = 0 AND disputes = 0) <> 4 THEN
        RAISE EXCEPTION 'Report counts must count member rows, include zero-vote reports, and exclude clearing votes';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.clearance_community_counts
        WHERE clearance_id = '00000000-0000-0000-0000-000000000020' AND supporters = 1 AND disputes = 0)
        OR NOT EXISTS (SELECT 1 FROM public.clearance_community_counts
        WHERE clearance_id = '00000000-0000-0000-0000-000000000021' AND supporters = 0 AND disputes = 0) THEN
        RAISE EXCEPTION 'Clearing counts must remain scoped to each observation';
    END IF;
END;
$$;

UPDATE public.report_votes SET stance = 'corroborate';
UPDATE public.barrier_reports SET status = 'resolved' WHERE id = '00000000-0000-0000-0000-000000000001';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.report_community_counts
        WHERE report_id = '00000000-0000-0000-0000-000000000001' AND supporters = 2 AND disputes = 0)
        OR (SELECT count(*) FROM public.building_active_warnings WHERE campus_id = 'read-campus') <> 2 THEN
        RAISE EXCEPTION 'Views must reflect committed-table changes without materialized stale counts/warnings';
    END IF;
END;
$$;
SELECT pg_temp.expect_error($q$UPDATE public.building_active_warnings SET description = 'changed'$q$, '55000');
RESET ROLE;

DO $$
DECLARE view_name text; role_name text; operation text; columns text[]; expected text[];
BEGIN
    FOREACH view_name IN ARRAY ARRAY['building_active_warnings', 'report_community_counts', 'clearance_community_counts'] LOOP
        IF NOT (SELECT 'security_invoker=true' = ANY(reloptions) FROM pg_class WHERE oid = ('public.' || view_name)::regclass) THEN
            RAISE EXCEPTION 'View % must use invoker permissions', view_name;
        END IF;
        SELECT array_agg(column_name::text ORDER BY ordinal_position) INTO columns
            FROM information_schema.columns WHERE table_schema = 'public' AND table_name = view_name;
        expected := CASE view_name
            WHEN 'building_active_warnings' THEN ARRAY['building_id', 'campus_id', 'report_id', 'description', 'status', 'observed_at']
            WHEN 'report_community_counts' THEN ARRAY['report_id', 'supporters', 'disputes']
            ELSE ARRAY['clearance_id', 'report_id', 'supporters', 'disputes'] END;
        IF columns IS DISTINCT FROM expected THEN
            RAISE EXCEPTION 'Unexpected public projection columns on %', view_name;
        END IF;
        FOREACH operation IN ARRAY ARRAY['INSERT', 'UPDATE', 'DELETE'] LOOP
            IF has_table_privilege('service_role', 'public.' || view_name, operation) THEN
                RAISE EXCEPTION 'Service role has unexpected % view access', operation;
            END IF;
        END LOOP;
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
                IF has_table_privilege(role_name, 'public.' || view_name, operation) THEN
                    RAISE EXCEPTION '% has unexpected % view access', role_name, operation;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;
END;
$$;
-- Even an accidental view grant must not borrow owner access to private tables.
GRANT SELECT ON public.report_community_counts TO anon;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT * FROM public.report_community_counts', '42501');
SELECT pg_temp.expect_error('SELECT * FROM public.building_active_warnings', '42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT * FROM public.clearance_community_counts', '42501');
RESET ROLE;
ROLLBACK;
\echo 'Community read-view checks passed (fixtures rolled back).'
