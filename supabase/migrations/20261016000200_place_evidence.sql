-- Add evidence storage without changing current facility summaries or report state.
CREATE TABLE public.entrances (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id varchar(128) NOT NULL REFERENCES public.buildings(id) ON DELETE RESTRICT,
    description varchar(2000) NOT NULL CHECK (length(btrim(description)) > 0),
    latitude double precision CHECK (latitude BETWEEN -90 AND 90),
    longitude double precision CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT entrance_coordinates_pair CHECK (
        (latitude IS NULL AND longitude IS NULL)
        OR (latitude IS NOT NULL AND longitude IS NOT NULL)
    )
);

CREATE INDEX entrances_building_id_idx ON public.entrances(building_id);

CREATE TABLE public.facility_observations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id varchar(128) NOT NULL REFERENCES public.buildings(id) ON DELETE RESTRICT,
    facility text NOT NULL CHECK (
        facility IN ('step_free_entrance', 'accessible_toilet', 'designated_parking')
    ),
    value text NOT NULL CHECK (value IN ('yes', 'no', 'unknown')),
    observed_at timestamptz,
    source text,
    notes text,
    -- Ingestion time is separate from a possibly unknown observation time.
    recorded_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX facility_observations_building_facility_idx
    ON public.facility_observations(building_id, facility);

-- Ordered references map to the API's photo_urls / evidence_urls arrays.
-- These are reference records, not Storage objects or an upload API.
CREATE TABLE public.entrance_photos (
    entrance_id uuid NOT NULL REFERENCES public.entrances(id) ON DELETE RESTRICT,
    position integer NOT NULL CHECK (position >= 0),
    url text NOT NULL CHECK (url ~* '^https?://[^[:space:]/?#]+([/?#][^[:space:]]*)?$'),
    PRIMARY KEY (entrance_id, position)
);

CREATE TABLE public.observation_evidence (
    observation_id uuid NOT NULL REFERENCES public.facility_observations(id) ON DELETE RESTRICT,
    position integer NOT NULL CHECK (position >= 0),
    url text NOT NULL CHECK (url ~* '^https?://[^[:space:]/?#]+([/?#][^[:space:]]*)?$'),
    PRIMARY KEY (observation_id, position)
);

ALTER TABLE public.entrances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.facility_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entrance_photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observation_evidence ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.entrances, public.facility_observations,
    public.entrance_photos, public.observation_evidence FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.entrances, public.facility_observations,
    public.entrance_photos, public.observation_evidence TO service_role;
