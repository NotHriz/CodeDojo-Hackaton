-- First persistence slice; no campus observations or fictional records are seeded.
CREATE TABLE public.campuses (
    id varchar(128) PRIMARY KEY CHECK (length(btrim(id)) > 0),
    name varchar(200) NOT NULL CHECK (length(btrim(name)) > 0)
);

CREATE TABLE public.buildings (
    id varchar(128) PRIMARY KEY CHECK (length(btrim(id)) > 0),
    campus_id varchar(128) NOT NULL REFERENCES public.campuses(id) ON DELETE RESTRICT,
    name varchar(200) NOT NULL CHECK (length(btrim(name)) > 0),
    category varchar(64) NOT NULL CHECK (length(btrim(category)) > 0),
    description text,
    latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    step_free_entrance text NOT NULL DEFAULT 'unknown'
        CHECK (step_free_entrance IN ('yes', 'no', 'unknown')),
    accessible_toilet text NOT NULL DEFAULT 'unknown'
        CHECK (accessible_toilet IN ('yes', 'no', 'unknown')),
    designated_parking text NOT NULL DEFAULT 'unknown'
        CHECK (designated_parking IN ('yes', 'no', 'unknown'))
);

CREATE INDEX buildings_campus_id_idx ON public.buildings(campus_id);

-- Application data travels through FastAPI. Auth alone grants no table access.
-- Supabase's backend service role bypasses RLS; its credential stays server-side.
ALTER TABLE public.campuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.buildings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.campuses, public.buildings FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.campuses, public.buildings TO service_role;
