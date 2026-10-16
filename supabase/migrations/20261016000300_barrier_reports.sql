-- Creation storage only. Voting, audit events, restrictions, and adapter wiring
-- are separate increments; this does not activate a trust policy.
CREATE TABLE public.barrier_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    building_id varchar(128) NOT NULL REFERENCES public.buildings(id) ON DELETE RESTRICT,
    author_id uuid NOT NULL,
    barrier_type varchar(64) NOT NULL CHECK (length(btrim(barrier_type)) > 0),
    description varchar(2000) NOT NULL CHECK (length(btrim(description)) > 0),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    submitted_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(submitted_at)),
    status text NOT NULL DEFAULT 'unverified' CHECK (
        status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')
    ),
    idempotency_key uuid NOT NULL,
    payload_digest text NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT barrier_report_observation_time CHECK (
        observed_at <= submitted_at + interval '5 minutes'
    ),
    -- This table represents the create-report operation; building_id is its target.
    CONSTRAINT barrier_report_submission_key UNIQUE (author_id, building_id, idempotency_key)
);

CREATE INDEX barrier_reports_building_submitted_idx
    ON public.barrier_reports(building_id, submitted_at DESC, id DESC);

CREATE TABLE public.barrier_report_evidence (
    report_id uuid NOT NULL REFERENCES public.barrier_reports(id) ON DELETE RESTRICT,
    -- Three distinct slots enforce the contract's maximum of three references.
    position integer NOT NULL CHECK (position BETWEEN 0 AND 2),
    url text NOT NULL CHECK (url ~* '^https?://[^[:space:]/?#]+([/?#][^[:space:]]*)?$'),
    PRIMARY KEY (report_id, position)
);

-- Rows contain private author identity and retry metadata: backend access only.
ALTER TABLE public.barrier_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.barrier_report_evidence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.barrier_reports, public.barrier_report_evidence
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.barrier_reports, public.barrier_report_evidence
    TO service_role;
