-- PostgreSQL 17 added MAINTAIN to table ALL privileges. The earlier deployed
-- correction left that grant intact. Keep applied files immutable and remove
-- the extra privilege without affecting CRUD or data. Older servers do not
-- recognize MAINTAIN, so parse the REVOKE only where it is supported.
DO $$
BEGIN
    IF current_setting('server_version_num')::integer >= 170000 THEN
        EXECUTE 'REVOKE MAINTAIN ON TABLE
            public.campuses,
            public.buildings,
            public.entrances,
            public.entrance_photos,
            public.facility_observations,
            public.observation_evidence,
            public.barrier_reports,
            public.barrier_report_evidence,
            public.report_votes,
            public.clearance_observations,
            public.clearance_evidence,
            public.clearance_votes
        FROM service_role';
    END IF;
END;
$$;
