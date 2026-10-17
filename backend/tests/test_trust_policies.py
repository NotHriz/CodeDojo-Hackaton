"""Named policy selection, boundaries and precedence; no external services."""
from dataclasses import FrozenInstanceError
from unittest.mock import patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app
from app.services.community import (
    ContributorState, TrustPolicy, VoteSnapshot, VoteStance, aggregate_votes, eligible_weight,
)
from app.services.trust_policies import PILOT_POLICY, PILOT_POLICY_VERSION, configured_policy
from app.services.postgres_community import PostgresCommunityRepository


def test_disabled_default_does_not_activate_voting():
    app = create_app(Settings(_env_file=None))
    assert app.state.trust_policy is None
    assert app.state.trust_policy_version is None
    assert configured_policy("disabled") is None


def test_selected_version_binds_routes_and_persisted_adapter_without_connecting():
    with patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError("Must remain lazy")):
        app = create_app(Settings(_env_file=None, database_url="postgresql://postgres@localhost/test",
                                  community_policy_version=PILOT_POLICY_VERSION))
        try:
            assert app.state.trust_policy == PILOT_POLICY.policy
            assert app.state.trust_policy_version == PILOT_POLICY_VERSION
            assert app.state.community_repository.policy == PILOT_POLICY.policy
            assert app.state.community_repository.policy_version == PILOT_POLICY_VERSION
        finally:
            app.state.community_repository.database.close()


@pytest.mark.parametrize("version", ["", "typo", "iium-gombak-pilot-v2", " iium-gombak-pilot-v1"])
def test_unknown_version_fails_configuration_instead_of_falling_back(version):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, community_policy_version=version)
    with pytest.raises(ValueError):
        configured_policy(version)


def test_explicit_injected_policy_takes_precedence_over_environment_selection():
    explicit = TrustPolicy(minimum_supporters=4, minimum_weight=4, support_ratio=.8, maximum_vote_weight=1)
    app = create_app(Settings(_env_file=None, community_policy_version=PILOT_POLICY_VERSION),
                     trust_policy=explicit, trust_policy_version="test-explicit-v1")
    assert app.state.trust_policy == explicit
    assert app.state.trust_policy_version == "test-explicit-v1"


def test_injected_thresholds_cannot_reuse_published_version():
    different = TrustPolicy(minimum_supporters=4, minimum_weight=4, support_ratio=.8, maximum_vote_weight=1)
    with pytest.raises(ValueError, match="different thresholds"):
        create_app(Settings(_env_file=None), trust_policy=different, trust_policy_version=PILOT_POLICY_VERSION)
    with pytest.raises(ValueError, match="different thresholds"):
        PostgresCommunityRepository(None, policy=different, policy_version=PILOT_POLICY_VERSION)


def test_published_binding_is_immutable_and_has_expected_snapshot():
    assert PILOT_POLICY.policy.model_dump() == {
        "minimum_supporters": 3, "minimum_weight": 3, "support_ratio": .67, "maximum_vote_weight": 2,
    }
    with pytest.raises(FrozenInstanceError):
        PILOT_POLICY.version = "changed"
    with pytest.raises(ValidationError):
        PILOT_POLICY.policy.minimum_supporters = 2
    assert eligible_weight(None, PILOT_POLICY.policy) == 1
    assert eligible_weight(ContributorState(vote_weight=10), PILOT_POLICY.policy) == 2


@pytest.mark.parametrize("support,oppose,expected", [
    ([1, 1], [], "unverified"),
    ([2, 2], [], "unverified"),  # Weight cannot bypass distinct-person quorum.
    ([1, 1, 1], [], "community_corroborated"),
    ([1, 1, 1], [1], "community_corroborated"),
    ([1, 1, 1], [1, 1], "disputed"),
    ([1, 1, 2], [2], "disputed"),  # 2/3 is below the explicit 67% cutoff.
    ([1, 2, 2], [2], "community_corroborated"),
])
def test_pilot_quorum_weight_and_ratio_boundaries(support, oppose, expected):
    votes = [VoteSnapshot(uuid4(), VoteStance.CORROBORATE, w) for w in support]
    votes += [VoteSnapshot(uuid4(), VoteStance.DISPUTE, w) for w in oppose]
    status, counts = aggregate_votes(votes, author_id=uuid4(), policy=PILOT_POLICY.policy)
    assert status == expected
    assert (counts.supporters, counts.disputes) == (len(support), len(oppose))
