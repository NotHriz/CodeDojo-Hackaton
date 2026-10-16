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
INSERT INTO public.campuses (id, name) VALUES ('detail-campus', 'Fictional detail campus');
INSERT INTO public.buildings (id, campus_id, name, category, latitude, longitude, step_free_entrance) VALUES
    ('detail-building', 'detail-campus', 'Fictional detailed building', 'study', 3.25, 101.73, 'yes'),
    ('empty-building', 'detail-campus', 'Fictional unobserved building', 'study', 3.25, 101.73, 'unknown');
INSERT INTO public.entrances (id, building_id, description, latitude, longitude) VALUES
    ('20000000-0000-0000-0000-000000000001', 'detail-building', 'Fictional east entrance', NULL, NULL),
    ('20000000-0000-0000-0000-000000000002', 'detail-building', 'Fictional west entrance', 3.251, 101.731);
INSERT INTO public.entrance_photos (entrance_id, position, url) VALUES
    ('20000000-0000-0000-0000-000000000001', 1, 'https://example.com/second.jpg'),
    ('20000000-0000-0000-0000-000000000001', 0, 'https://example.com/first.jpg');
INSERT INTO public.facility_observations (id, building_id, facility, value, observed_at) VALUES
    ('20000000-0000-0000-0000-000000000003', 'detail-building', 'step_free_entrance', 'yes', NULL),
    ('20000000-0000-0000-0000-000000000004', 'detail-building', 'accessible_toilet', 'unknown', '2026-10-17T12:00:00+08:00');
INSERT INTO public.observation_evidence (observation_id, position, url) VALUES
    ('20000000-0000-0000-0000-000000000003', 1, 'https://example.com/second.jpg'),
    ('20000000-0000-0000-0000-000000000003', 0, 'https://example.com/first.jpg');
INSERT INTO public.barrier_reports (id, building_id, author_id, barrier_type, description,
    observed_at, status, idempotency_key, payload_digest)
SELECT ('20000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid, 'detail-building',
    '20000000-0000-0000-0000-000000000010', 'obstruction', 'Fictional detail warning',
    now(), status, ('20000000-0000-0000-0000-' || lpad(n::text,12,'0'))::uuid, repeat('a',64)
FROM (VALUES (5,'unverified'),(6,'disputed'),(7,'resolved')) AS fixture(n,status);

DO $$
DECLARE detail jsonb; empty_record jsonb;
BEGIN
    SELECT record INTO detail FROM public.place_detail_records WHERE id='detail-building';
    SELECT record INTO empty_record FROM public.place_detail_records WHERE id='empty-building';
    IF jsonb_array_length(detail->'entrances') <> 2 OR jsonb_array_length(detail->'observations') <> 2
        OR jsonb_array_length(detail->'active_warnings') <> 2 THEN
        RAISE EXCEPTION 'Related records must not multiply across joins or include resolved warnings';
    END IF;
    IF detail#>'{entrances,0,coordinates}' <> 'null'::jsonb
        OR detail#>>'{entrances,1,coordinates,latitude}' <> '3.251'
        OR detail#>'{observations,0,observed_at}' <> 'null'::jsonb
        OR detail#>'{observations,0,source}' <> 'null'::jsonb THEN
        RAISE EXCEPTION 'Missing entrance/observation metadata must remain null';
    END IF;
    IF detail#>'{entrances,0,photo_urls}' <> '["https://example.com/first.jpg","https://example.com/second.jpg"]'::jsonb
        OR detail#>'{observations,0,evidence_urls}' <> '["https://example.com/first.jpg","https://example.com/second.jpg"]'::jsonb
        OR detail#>'{entrances,1,photo_urls}' <> '[]'::jsonb THEN
        RAISE EXCEPTION 'Evidence/photo order and missing reference arrays must be preserved';
    END IF;
    IF empty_record->'entrances' <> '[]'::jsonb OR empty_record->'observations' <> '[]'::jsonb
        OR empty_record->'active_warnings' <> '[]'::jsonb
        OR empty_record#>>'{facilities,step_free_entrance}' <> 'unknown'
        OR detail#>>'{facilities,step_free_entrance}' <> 'yes'
        OR detail->>'is_demo' <> 'false' THEN
        RAISE EXCEPTION 'Empty/unknown records and facility summaries must be retained';
    END IF;
END;
$$;
RESET ROLE;
DO $$
DECLARE role_name text; operation text;
BEGIN
    IF NOT (SELECT 'security_invoker=true'=ANY(reloptions) FROM pg_class
        WHERE oid='public.place_detail_records'::regclass) THEN
        RAISE EXCEPTION 'Place projection must retain invoker permissions';
    END IF;
    FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
        FOREACH operation IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE'] LOOP
            IF has_table_privilege(role_name,'public.place_detail_records',operation)
                IS DISTINCT FROM (role_name='service_role' AND operation='SELECT') THEN
                RAISE EXCEPTION 'Unexpected place-record grant for % %',role_name,operation;
            END IF;
        END LOOP;
    END LOOP;
END;
$$;
GRANT SELECT ON public.place_detail_records TO anon;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT record FROM public.place_detail_records','42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT record FROM public.place_detail_records','42501');
RESET ROLE;
ROLLBACK;
\echo 'Place detail record checks passed (fixtures rolled back).'
