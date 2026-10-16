-- A composite reference binds the copied author identity to its actual report.
-- This lets a row CHECK reject self-voting without trusting a supplied author ID.
ALTER TABLE public.barrier_reports
    ADD CONSTRAINT barrier_report_id_author_key UNIQUE (id, author_id);

CREATE TABLE public.report_votes (
    report_id uuid NOT NULL,
    report_author_id uuid NOT NULL,
    voter_id uuid NOT NULL,
    stance text NOT NULL CHECK (stance IN ('corroborate', 'dispute')),
    weight numeric NOT NULL,
    -- Explicit metadata from the reviewed backend policy, never client input.
    -- There are deliberately no defaults for weights or policy values.
    policy_version text NOT NULL CHECK (length(btrim(policy_version)) > 0),
    policy_minimum_supporters integer NOT NULL CHECK (policy_minimum_supporters BETWEEN 2 AND 20),
    policy_minimum_weight numeric NOT NULL CHECK (policy_minimum_weight > 0 AND policy_minimum_weight <= 40),
    policy_support_ratio numeric NOT NULL CHECK (policy_support_ratio > 0.5 AND policy_support_ratio <= 1),
    policy_maximum_vote_weight numeric NOT NULL CHECK (policy_maximum_vote_weight BETWEEN 1 AND 2),
    updated_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(updated_at)),
    PRIMARY KEY (report_id, voter_id),
    CONSTRAINT report_vote_author_fk FOREIGN KEY (report_id, report_author_id)
        REFERENCES public.barrier_reports(id, author_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT report_vote_no_self_vote CHECK (voter_id <> report_author_id),
    CONSTRAINT report_vote_bounded_weight CHECK (weight BETWEEN 1 AND policy_maximum_vote_weight)
);

-- Voting identities, weights, and policy metadata stay private to the backend.
ALTER TABLE public.report_votes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.report_votes FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.report_votes TO service_role;

-- No aggregation trigger or default trust policy is installed. A future adapter
-- must lock the report and update vote/status/audit history in one transaction.
