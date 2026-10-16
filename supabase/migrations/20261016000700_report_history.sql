ALTER TABLE public.clearance_observations
    ADD CONSTRAINT clearance_id_report_key UNIQUE (id, report_id);

CREATE TABLE public.report_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    report_id uuid NOT NULL REFERENCES public.barrier_reports(id) ON DELETE RESTRICT,
    occurred_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(occurred_at)),
    action text NOT NULL CHECK (action IN (
        'report_created', 'vote_updated', 'clearance_submitted', 'clearance_vote_updated'
    )),
    previous_status text CHECK (previous_status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')),
    new_status text NOT NULL CHECK (new_status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')),
    supporters integer NOT NULL CHECK (supporters >= 0),
    disputes integer NOT NULL CHECK (disputes >= 0),
    -- Everything below is internal, excluded from ReportEventResponse.
    actor_id uuid NOT NULL,
    clearance_id uuid,
    clearance_previous_status text CHECK (clearance_previous_status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')),
    clearance_new_status text CHECK (clearance_new_status IN ('unverified', 'community_corroborated', 'disputed', 'resolved')),
    clearance_supporters integer CHECK (clearance_supporters >= 0),
    clearance_disputes integer CHECK (clearance_disputes >= 0),
    stance text CHECK (stance IN ('corroborate', 'dispute')),
    weight numeric,
    policy_version text CHECK (length(btrim(policy_version)) > 0),
    policy_minimum_supporters integer CHECK (policy_minimum_supporters BETWEEN 2 AND 20),
    policy_minimum_weight numeric CHECK (policy_minimum_weight > 0 AND policy_minimum_weight <= 40),
    policy_support_ratio numeric CHECK (policy_support_ratio > 0.5 AND policy_support_ratio <= 1),
    policy_maximum_vote_weight numeric CHECK (policy_maximum_vote_weight BETWEEN 1 AND 2),
    FOREIGN KEY (clearance_id, report_id) REFERENCES public.clearance_observations(id, report_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT report_event_previous_status CHECK (
        (action = 'report_created' AND previous_status IS NULL AND new_status = 'unverified'
            AND supporters = 0 AND disputes = 0)
        OR (action <> 'report_created' AND previous_status IS NOT NULL)
    ),
    CONSTRAINT report_event_clearance_scope CHECK (
        (action IN ('clearance_submitted', 'clearance_vote_updated')
            AND clearance_id IS NOT NULL AND clearance_new_status IS NOT NULL
            AND clearance_supporters IS NOT NULL AND clearance_disputes IS NOT NULL
            AND ((action = 'clearance_submitted' AND clearance_previous_status IS NULL
                AND clearance_new_status = 'unverified' AND clearance_supporters = 0 AND clearance_disputes = 0)
                OR (action = 'clearance_vote_updated' AND clearance_previous_status IS NOT NULL)))
        OR (action IN ('report_created', 'vote_updated') AND clearance_id IS NULL
            AND clearance_previous_status IS NULL AND clearance_new_status IS NULL
            AND clearance_supporters IS NULL AND clearance_disputes IS NULL)
    ),
    CONSTRAINT report_event_vote_snapshot CHECK (
        (action IN ('vote_updated', 'clearance_vote_updated')
            AND stance IS NOT NULL AND weight IS NOT NULL AND policy_version IS NOT NULL
            AND policy_minimum_supporters IS NOT NULL AND policy_minimum_weight IS NOT NULL
            AND policy_support_ratio IS NOT NULL AND policy_maximum_vote_weight IS NOT NULL
            AND weight BETWEEN 1 AND policy_maximum_vote_weight)
        OR (action IN ('report_created', 'clearance_submitted')
            AND stance IS NULL AND weight IS NULL AND policy_version IS NULL
            AND policy_minimum_supporters IS NULL AND policy_minimum_weight IS NULL
            AND policy_support_ratio IS NULL AND policy_maximum_vote_weight IS NULL)
    )
);

CREATE INDEX report_events_timeline_idx ON public.report_events(report_id, occurred_at, sequence);
CREATE UNIQUE INDEX report_events_one_creation_idx ON public.report_events(report_id)
    WHERE action = 'report_created';
CREATE UNIQUE INDEX report_events_one_clearance_creation_idx ON public.report_events(clearance_id)
    WHERE action = 'clearance_submitted';

ALTER TABLE public.report_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.report_events FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT ON TABLE public.report_events TO service_role;
REVOKE ALL ON SEQUENCE public.report_events_sequence_seq FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.report_events_sequence_seq TO service_role;
-- Append-only for the application role. Database owners can still administer it.
-- The future adapter must insert events in the same transaction as each mutation.
