-- Supabase's existing default privileges can grant ALL to service_role on new
-- tables. Earlier explicit CRUD GRANTs do not remove those inherited defaults.
-- Preserve the accepted application CRUD contract while removing extra rights.
-- Already-applied migrations remain immutable; no data or schema is removed.
REVOKE TRUNCATE, REFERENCES, TRIGGER ON TABLE
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
FROM service_role;
