-- Private current eligibility/weight, mapped by the future CommunityRepository.
-- No public profile, scoring algorithm, automatic restriction, or seed accounts.
CREATE TABLE public.contributor_state (
    user_id uuid PRIMARY KEY,
    can_contribute boolean NOT NULL DEFAULT true,
    vote_weight numeric NOT NULL DEFAULT 1 CHECK (vote_weight BETWEEN 1 AND 2),
    restriction_reason text,
    updated_at timestamptz NOT NULL DEFAULT now() CHECK (isfinite(updated_at)),
    CONSTRAINT contributor_restriction_reason CHECK (
        (can_contribute AND restriction_reason IS NULL)
        OR (NOT can_contribute AND restriction_reason IS NOT NULL
            AND length(btrim(restriction_reason)) > 0)
    )
);

ALTER TABLE public.contributor_state ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.contributor_state FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.contributor_state TO service_role;
-- Restore eligibility explicitly rather than deleting a blocked row and causing
-- the repository's missing-contributor neutral default to apply accidentally.
