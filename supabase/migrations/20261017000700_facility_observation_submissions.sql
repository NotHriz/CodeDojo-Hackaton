-- Durable retry protection for signed-in facility observations.
CREATE TABLE public.facility_observation_submissions (
    author_id uuid NOT NULL,
    building_id varchar(128) NOT NULL REFERENCES public.buildings(id) ON DELETE RESTRICT,
    idempotency_key uuid NOT NULL,
    payload_digest text NOT NULL CHECK (length(payload_digest) = 64),
    observation_id uuid NOT NULL UNIQUE REFERENCES public.facility_observations(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (author_id, building_id, idempotency_key)
);

ALTER TABLE public.facility_observation_submissions ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.facility_observation_submissions FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.facility_observation_submissions TO service_role;

DO $$
BEGIN
    IF current_setting('server_version_num')::integer >= 170000 THEN
        EXECUTE 'REVOKE MAINTAIN ON TABLE public.facility_observation_submissions FROM service_role';
    END IF;
END;
$$;
