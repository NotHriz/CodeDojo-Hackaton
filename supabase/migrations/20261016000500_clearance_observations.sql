-- Bind the copied barrier time to the actual parent, allowing a row constraint
-- to enforce chronology without a race against changes to the parent time.
ALTER TABLE public.barrier_reports
    ADD CONSTRAINT barrier_report_id_observed_key UNIQUE (id, observed_at);

CREATE TABLE public.clearance_observations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id uuid NOT NULL,
    report_observed_at timestamptz NOT NULL,
    author_id uuid NOT NULL,
    description varchar(2000) NOT NULL CHECK (length(btrim(description)) > 0),
    observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
    submitted_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(submitted_at)),
    status text NOT NULL DEFAULT 'unverified' CHECK (
        status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')
    ),
    idempotency_key uuid NOT NULL,
    payload_digest text NOT NULL CHECK (payload_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT clearance_report_time_fk FOREIGN KEY (report_id, report_observed_at)
        REFERENCES public.barrier_reports(id, observed_at) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT clearance_observation_chronology CHECK (observed_at >= report_observed_at),
    CONSTRAINT clearance_observation_future_bound CHECK (
        observed_at <= submitted_at + interval '5 minutes'
    ),
    -- The operation is create-clearance and its target is the parent report.
    CONSTRAINT clearance_submission_key UNIQUE (author_id, report_id, idempotency_key)
);

CREATE INDEX clearance_observations_report_submitted_idx
    ON public.clearance_observations(report_id, submitted_at, id);

CREATE TABLE public.clearance_evidence (
    clearance_id uuid NOT NULL REFERENCES public.clearance_observations(id) ON DELETE RESTRICT,
    position integer NOT NULL CHECK (position BETWEEN 0 AND 2),
    url text NOT NULL CHECK (url ~* '^https?://[^[:space:]/?#]+([/?#][^[:space:]]*)?$'),
    PRIMARY KEY (clearance_id, position)
);

ALTER TABLE public.clearance_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clearance_evidence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.clearance_observations, public.clearance_evidence
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.clearance_observations, public.clearance_evidence
    TO service_role;

-- A clearing claim does not resolve a report. No aggregation/status trigger,
-- clearing votes, audit event, or contributor policy is installed in this slice.
