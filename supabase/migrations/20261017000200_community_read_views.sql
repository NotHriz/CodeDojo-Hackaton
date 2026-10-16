-- Invoker views retain underlying table permissions/RLS instead of borrowing
-- the view owner's privileges. They are backend-only query projections.
CREATE VIEW public.building_active_warnings WITH (security_invoker = true) AS
SELECT b.id AS building_id, b.campus_id, r.id AS report_id,
    r.description, r.status, r.observed_at
FROM public.barrier_reports AS r
JOIN public.buildings AS b ON b.id = r.building_id
WHERE r.status IN ('unverified', 'community_corroborated', 'disputed');

CREATE VIEW public.report_community_counts WITH (security_invoker = true) AS
SELECT r.id AS report_id,
    count(*) FILTER (WHERE v.stance = 'corroborate') AS supporters,
    count(*) FILTER (WHERE v.stance = 'dispute') AS disputes
FROM public.barrier_reports AS r
LEFT JOIN public.report_votes AS v ON v.report_id = r.id
GROUP BY r.id;

CREATE VIEW public.clearance_community_counts WITH (security_invoker = true) AS
SELECT c.id AS clearance_id, c.report_id,
    count(*) FILTER (WHERE v.stance = 'corroborate') AS supporters,
    count(*) FILTER (WHERE v.stance = 'dispute') AS disputes
FROM public.clearance_observations AS c
LEFT JOIN public.clearance_votes AS v ON v.clearance_id = c.id
GROUP BY c.id, c.report_id;

REVOKE ALL ON TABLE public.building_active_warnings, public.report_community_counts,
    public.clearance_community_counts FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.building_active_warnings, public.report_community_counts,
    public.clearance_community_counts TO service_role;
-- Counts are distinct member rows, not weighted support or a consensus decision.
-- Status is stored backend-derived state; no transition or policy is activated.
