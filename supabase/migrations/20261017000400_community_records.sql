CREATE VIEW public.clearance_public_records WITH (security_invoker = true) AS
SELECT c.id, c.report_id, c.submitted_at, jsonb_build_object(
    'id', c.id, 'description', c.description, 'observed_at', c.observed_at,
    'submitted_at', c.submitted_at, 'status', c.status,
    'community', jsonb_build_object('supporters', counts.supporters, 'disputes', counts.disputes),
    'evidence_urls', COALESCE((SELECT jsonb_agg(e.url ORDER BY e.position)
        FROM public.clearance_evidence AS e WHERE e.clearance_id = c.id), '[]'::jsonb)
) AS record
FROM public.clearance_observations AS c
JOIN public.clearance_community_counts AS counts ON counts.clearance_id = c.id;

CREATE VIEW public.report_public_records WITH (security_invoker = true) AS
SELECT r.id, r.building_id, b.campus_id, r.submitted_at, jsonb_build_object(
    'id', r.id, 'place_id', r.building_id, 'campus_id', b.campus_id,
    'barrier_type', r.barrier_type, 'description', r.description,
    'observed_at', r.observed_at, 'submitted_at', r.submitted_at, 'status', r.status,
    'community', jsonb_build_object('supporters', counts.supporters, 'disputes', counts.disputes),
    'evidence_urls', COALESCE((SELECT jsonb_agg(e.url ORDER BY e.position)
        FROM public.barrier_report_evidence AS e WHERE e.report_id = r.id), '[]'::jsonb),
    'clearance_observations', COALESCE((SELECT jsonb_agg(c.record ORDER BY c.submitted_at, c.id)
        FROM public.clearance_public_records AS c WHERE c.report_id = r.id), '[]'::jsonb)
) AS record
FROM public.barrier_reports AS r
JOIN public.buildings AS b ON b.id = r.building_id
JOIN public.report_community_counts AS counts ON counts.report_id = r.id;

CREATE VIEW public.report_history_records WITH (security_invoker = true) AS
SELECT e.id, e.report_id, b.campus_id, e.occurred_at, e.sequence, jsonb_build_object(
    'id', e.id, 'report_id', e.report_id, 'occurred_at', e.occurred_at,
    'action', e.action, 'previous_status', e.previous_status, 'new_status', e.new_status,
    'community', jsonb_build_object('supporters', e.supporters, 'disputes', e.disputes)
) AS record
FROM public.report_events AS e
JOIN public.barrier_reports AS r ON r.id = e.report_id
JOIN public.buildings AS b ON b.id = r.building_id;

REVOKE ALL ON TABLE public.clearance_public_records, public.report_public_records,
    public.report_history_records FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.clearance_public_records, public.report_public_records,
    public.report_history_records TO service_role;
-- "Public" describes DTO field selection, not browser access to the views.
-- Stored statuses remain backend-owned; history uses captured counts, not live votes.
