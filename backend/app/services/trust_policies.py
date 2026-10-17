"""Immutable, named pilot policy definitions; activation is explicit configuration.

Never change thresholds under a published version: introduce a new version and
review existing snapshots/migration separately. Disabled remains the default.
"""
from dataclasses import dataclass

from app.services.community import TrustPolicy

PILOT_POLICY_VERSION = "iium-gombak-pilot-v1"


@dataclass(frozen=True)
class PolicyBinding:
    version: str
    policy: TrustPolicy


PILOT_POLICY = PolicyBinding(
    version=PILOT_POLICY_VERSION,
    policy=TrustPolicy(
        minimum_supporters=3,
        minimum_weight=3,
        support_ratio=0.67,
        maximum_vote_weight=2,
    ),
)


def configured_policy(version: str) -> PolicyBinding | None:
    if version == "disabled":
        return None
    if version == PILOT_POLICY_VERSION:
        return PILOT_POLICY
    raise ValueError("Unknown community policy version.")


def validate_named_binding(policy: TrustPolicy | None, version: str | None) -> None:
    if version == PILOT_POLICY_VERSION and policy != PILOT_POLICY.policy:
        raise ValueError("Published policy version cannot be bound to different thresholds.")
