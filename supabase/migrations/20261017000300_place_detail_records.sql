-- Complete read projection for the small campus pilot; production adapter pending.
CREATE VIEW public.place_detail_records WITH (security_invoker = true) AS
SELECT b.id, b.campus_id, jsonb_build_object(
    'id', b.id, 'campus_id', b.campus_id, 'name', b.name, 'category', b.category,
    'description', b.description,
    'coordinates', jsonb_build_object('latitude', b.latitude, 'longitude', b.longitude),
    'facilities', jsonb_build_object('step_free_entrance', b.step_free_entrance,
        'accessible_toilet', b.accessible_toilet, 'designated_parking', b.designated_parking),
    'is_demo', false,
    'entrances', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'description', e.description,
            'coordinates', CASE WHEN e.latitude IS NULL THEN NULL ELSE
                jsonb_build_object('latitude', e.latitude, 'longitude', e.longitude) END,
            'photo_urls', COALESCE((SELECT jsonb_agg(p.url ORDER BY p.position)
                FROM public.entrance_photos AS p WHERE p.entrance_id = e.id), '[]'::jsonb)
        ) ORDER BY e.id) FROM public.entrances AS e WHERE e.building_id = b.id
    ), '[]'::jsonb),
    'observations', COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'facility', o.facility, 'value', o.value, 'observed_at', o.observed_at,
            'source', o.source, 'notes', o.notes,
            'evidence_urls', COALESCE((SELECT jsonb_agg(p.url ORDER BY p.position)
                FROM public.observation_evidence AS p WHERE p.observation_id = o.id), '[]'::jsonb)
        ) ORDER BY o.recorded_at, o.id)
        FROM public.facility_observations AS o WHERE o.building_id = b.id
    ), '[]'::jsonb),
    'active_warnings', COALESCE((
        SELECT jsonb_agg(jsonb_build_object('report_id', w.report_id,
            'description', w.description, 'status', w.status, 'observed_at', w.observed_at)
            ORDER BY w.observed_at DESC NULLS LAST, w.report_id)
        FROM public.building_active_warnings AS w WHERE w.building_id = b.id
    ), '[]'::jsonb)
) AS record
FROM public.buildings AS b;

REVOKE ALL ON TABLE public.place_detail_records FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT ON TABLE public.place_detail_records TO service_role;
-- No inferred facility values, entrance coordinates, observation dates or status.
-- Arrays are independently aggregated to avoid multiplying children across joins.
