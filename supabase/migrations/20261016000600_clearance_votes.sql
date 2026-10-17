-- Bind votes to the actual clearing observation, parent report, and author.
ALTER TABLE public.clearance_observations
    ADD CONSTRAINT clearance_id_report_author_key UNIQUE (id, report_id, author_id);

CREATE TABLE public.clearance_votes (
    clearance_id uuid NOT NULL,
    report_id uuid NOT NULL,
    clearance_author_id uuid NOT NULL,
    voter_id uuid NOT NULL,
    stance text NOT NULL CHECK (stance IN ('corroborate', 'dispute')),
    weight numeric NOT NULL,
    -- Required snapshots from a reviewed backend policy; no active defaults.
    policy_version text NOT NULL CHECK (length(btrim(policy_version)) > 0),
    policy_minimum_supporters integer NOT NULL CHECK (policy_minimum_supporters BETWEEN 2 AND 20),
    policy_minimum_weight numeric NOT NULL CHECK (policy_minimum_weight > 0 AND policy_minimum_weight <= 40),
    policy_support_ratio numeric NOT NULL CHECK (policy_support_ratio > 0.5 AND policy_support_ratio <= 1),
    policy_maximum_vote_weight numeric NOT NULL CHECK (policy_maximum_vote_weight BETWEEN 1 AND 2),
    updated_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(updated_at)),
    PRIMARY KEY (clearance_id, voter_id),
    CONSTRAINT clearance_vote_target_fk FOREIGN KEY (clearance_id, report_id, clearance_author_id)
        REFERENCES public.clearance_observations(id, report_id, author_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT clearance_vote_no_self_vote CHECK (voter_id <> clearance_author_id),
    CONSTRAINT clearance_vote_bounded_weight CHECK (weight BETWEEN 1 AND policy_maximum_vote_weight)
);

CREATE INDEX clearance_votes_report_id_idx ON public.clearance_votes(report_id);

ALTER TABLE public.clearance_votes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.clearance_votes FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.clearance_votes TO service_role;

-- No status trigger: a future adapter must recalculate clearing/parent statuses
-- and record history atomically with each vote under an explicitly reviewed policy.
