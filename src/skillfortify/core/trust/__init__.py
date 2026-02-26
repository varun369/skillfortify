"""Trust Score Algebra for Agent Skill Supply Chain Security.

This package implements the trust computation, propagation, and decay engine
for SkillShield. Trust scores quantify the confidence that an agent skill is
safe to install and execute.

Submodules:
    models       -- TrustLevel, TrustSignals, TrustWeights, TrustScore
    engine       -- TrustEngine (compute, propagate, decay, evidence update)
    propagation  -- Standalone chain propagation, decay, and evidence functions

All public names are re-exported here so that existing imports of the form
``from skillfortify.core.trust import TrustEngine`` continue to work unchanged.
"""

from skillfortify.core.trust.models import (
    TrustLevel,
    TrustScore,
    TrustSignals,
    TrustWeights,
)
from skillfortify.core.trust.engine import TrustEngine

__all__ = [
    "TrustEngine",
    "TrustLevel",
    "TrustScore",
    "TrustSignals",
    "TrustWeights",
]
