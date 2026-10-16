BEGIN;
CREATE FUNCTION pg_temp.expect_error(statement text, expected_state text)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    BEGIN EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        IF SQLSTATE = expected_state THEN RETURN; END IF;
        RAISE;
    END;
    RAISE EXCEPTION 'Expected SQLSTATE % for %', expected_state, statement;
END;
$$;
SET LOCAL ROLE service_role;
INSERT INTO public.campuses (id,name) VALUES ('community-campus','Fictional community campus');
INSERT INTO public.buildings (id,campus_id,name,category,latitude,longitude)
VALUES ('community-building','community-campus','Fictional community building','study',3.25,101.73);
INSERT INTO public.barrier_reports (id,building_id,author_id,barrier_type,description,observed_at,idempotency_key,payload_digest)
SELECT ('30000000-0000-0000-0000-'||lpad(n::text,12,'0'))::uuid,'community-building',
    '30000000-0000-0000-0000-000000000010','obstruction','Fictional community barrier',now()-interval '1 hour',
    ('30000000-0000-0000-0000-'||lpad(n::text,12,'0'))::uuid,repeat('a',64)
FROM generate_series(1,2) AS fixture(n);
INSERT INTO public.clearance_observations (id,report_id,report_observed_at,author_id,description,observed_at,idempotency_key,payload_digest)
SELECT ('30000000-0000-0000-0000-'||lpad(n::text,12,'0'))::uuid,
    '30000000-0000-0000-0000-000000000001',now()-interval '1 hour',
    '30000000-0000-0000-0000-000000000011','Fictional clearing claim',now(),
    ('30000000-0000-0000-0000-'||lpad(n::text,12,'0'))::uuid,repeat('b',64)
FROM generate_series(3,4) AS fixture(n);
INSERT INTO public.barrier_report_evidence (report_id,position,url) VALUES
    ('30000000-0000-0000-0000-000000000001',1,'https://example.com/second.jpg'),
    ('30000000-0000-0000-0000-000000000001',0,'https://example.com/first.jpg');
INSERT INTO public.clearance_evidence (clearance_id,position,url) VALUES
    ('30000000-0000-0000-0000-000000000003',0,'https://example.com/clear.jpg');
INSERT INTO public.report_votes (report_id,report_author_id,voter_id,stance,weight,policy_version,
    policy_minimum_supporters,policy_minimum_weight,policy_support_ratio,policy_maximum_vote_weight)
VALUES ('30000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000010',
    '30000000-0000-0000-0000-000000000012','corroborate',2,'fictional-policy',3,3,0.67,2);
INSERT INTO public.clearance_votes (clearance_id,report_id,clearance_author_id,voter_id,stance,weight,
    policy_version,policy_minimum_supporters,policy_minimum_weight,policy_support_ratio,policy_maximum_vote_weight)
VALUES ('30000000-0000-0000-0000-000000000003','30000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000011','30000000-0000-0000-0000-000000000012',
    'dispute',1,'fictional-policy',3,3,0.67,2);
INSERT INTO public.report_events (report_id,action,new_status,supporters,disputes,actor_id)
VALUES ('30000000-0000-0000-0000-000000000001','report_created','unverified',0,0,
    '30000000-0000-0000-0000-000000000010');
DO $$
DECLARE detail jsonb; empty_record jsonb; event_record jsonb;
BEGIN
    SELECT record INTO detail FROM public.report_public_records WHERE id='30000000-0000-0000-0000-000000000001';
    SELECT record INTO empty_record FROM public.report_public_records WHERE id='30000000-0000-0000-0000-000000000002';
    SELECT record INTO event_record FROM public.report_history_records;
    IF jsonb_array_length(detail->'clearance_observations') <> 2
        OR detail#>>'{community,supporters}' <> '1' OR detail#>>'{community,disputes}' <> '0'
        OR detail#>>'{clearance_observations,0,community,disputes}' <> '1'
        OR detail#>>'{clearance_observations,1,community,disputes}' <> '0' THEN
        RAISE EXCEPTION 'Report/clearing counts must stay unweighted, separate and free of join multiplication';
    END IF;
    IF detail->'evidence_urls' <> '["https://example.com/first.jpg","https://example.com/second.jpg"]'::jsonb
        OR empty_record->'evidence_urls' <> '[]'::jsonb
        OR empty_record->'clearance_observations' <> '[]'::jsonb
        OR empty_record#>>'{community,supporters}' <> '0' THEN
        RAISE EXCEPTION 'Ordered/empty evidence, empty clearing arrays and zero counts must survive projection';
    END IF;
    IF event_record#>>'{community,supporters}' <> '0'
        OR event_record->'previous_status' <> 'null'::jsonb THEN
        RAISE EXCEPTION 'History must use captured counts and preserve null previous status';
    END IF;
END;
$$;
UPDATE public.barrier_reports SET status='resolved' WHERE id='30000000-0000-0000-0000-000000000001';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.report_public_records WHERE record->>'status'='resolved') THEN
        RAISE EXCEPTION 'Resolved reports must remain in report history/detail queries';
    END IF;
END;
$$;
RESET ROLE;
DO $$
DECLARE view_name text; role_name text; operation text;
BEGIN
    FOREACH view_name IN ARRAY ARRAY['clearance_public_records','report_public_records','report_history_records'] LOOP
        IF NOT (SELECT 'security_invoker=true'=ANY(reloptions) FROM pg_class WHERE oid=('public.'||view_name)::regclass) THEN
            RAISE EXCEPTION 'Community projections require invoker permissions';
        END IF;
        FOREACH role_name IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
            FOREACH operation IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE'] LOOP
                IF has_table_privilege(role_name,'public.'||view_name,operation)
                    IS DISTINCT FROM (role_name='service_role' AND operation='SELECT') THEN
                    RAISE EXCEPTION 'Unexpected grant on % for % %',view_name,role_name,operation;
                END IF;
            END LOOP;
        END LOOP;
    END LOOP;
END;
$$;
GRANT SELECT ON public.report_public_records TO anon;
SET LOCAL ROLE anon;
SELECT pg_temp.expect_error('SELECT record FROM public.report_public_records','42501');
RESET ROLE;
SET LOCAL ROLE authenticated;
SELECT pg_temp.expect_error('SELECT record FROM public.report_history_records','42501');
SELECT pg_temp.expect_error('SELECT record FROM public.clearance_public_records','42501');
RESET ROLE;
ROLLBACK;
\echo 'Community record checks passed (fixtures rolled back).'
