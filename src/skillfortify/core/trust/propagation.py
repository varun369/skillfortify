"""Trust propagation, temporal decay, and evidence updates.

Extends :class:`TrustEngine` with methods for:

- **Chain propagation** -- computing trust through ordered dependency chains.
- **Temporal decay** -- exponential decay for unmaintained skills.
- **Evidence updates** -- monotonic signal updates (Theorem 5 guarantee).

Trust Decay Model:
    T(s, t) = T_0(s) * exp(-lambda * (t - t_last_update))

Theorem 5 (Trust Monotonicity):
    Adding positive evidence (increasing any signal) NEVER reduces the
    trust score.

References:
    RFC 2704 (KeyNote Trust Management): Assertion monotonicity.
    SolarWinds (2020): Supply chain trust propagation failure.
    ClawHavoc (arXiv:2602.20867): 1,200+ malicious skills.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from .models import TrustScore, TrustSignals


def propagate_through_chain(
    engine: object,
    chain: list[tuple[str, str, TrustSignals]],
) -> list[TrustScore]:
    """Compute trust scores for a dependency chain from leaf to root.

    The chain is ordered from leaf (no dependencies) to root (depends
    on everything before it). Each skill's effective score incorporates
    the effective scores of all skills earlier in the chain.

    Example chain: [("lib-a", "1.0", signals_a), ("lib-b", "2.0", signals_b)]
    means lib-b depends on lib-a.

    Args:
        engine: A ``TrustEngine`` instance providing ``compute_score``.
        chain: Ordered list of (skill_name, version, signals) from leaf
            to root. The first element has no dependencies; each subsequent
            element depends on all previous elements.

    Returns:
        List of ``TrustScore`` objects, one per skill in the chain,
        in the same order as the input.

    Raises:
        ValueError: If the chain is empty or signals are invalid.
    """
    if not chain:
        raise ValueError("Chain must not be empty")

    scores: list[TrustScore] = []

    for i, (name, version, signals) in enumerate(chain):
        if i == 0:
            # Leaf node: no dependencies
            score = engine.compute_score(name, version, signals)  # type: ignore[attr-defined]
        else:
            # Depends on all previous nodes in the chain
            score = engine.compute_score(  # type: ignore[attr-defined]
                name, version, signals, dependency_scores=scores[:i]
            )
        scores.append(score)

    return scores


def apply_decay(
    engine: object,
    score: TrustScore,
    last_update: datetime,
    current_time: datetime | None = None,
) -> TrustScore:
    """Apply exponential decay for time since last update.

    T(s, t) = T_0(s) * exp(-lambda * days_elapsed)

    where days_elapsed = (current_time - last_update) in days.
    If current_time < last_update (skill updated in the "future"),
    no decay is applied.

    Args:
        engine: A ``TrustEngine`` instance providing ``decay_rate`` and
            ``score_to_level``.
        score: The base trust score to decay.
        last_update: When the skill was last updated.
        current_time: The reference time. Defaults to UTC now.

    Returns:
        A new ``TrustScore`` with decayed effective score.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Ensure both datetimes are timezone-aware for safe subtraction
    if last_update.tzinfo is None:
        last_update = last_update.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    delta = current_time - last_update
    days_elapsed = max(0.0, delta.total_seconds() / 86400.0)

    decay_factor = math.exp(-engine.decay_rate * days_elapsed)  # type: ignore[attr-defined]
    decayed_effective = score.effective_score * decay_factor

    # Clamp to [0, 1]
    decayed_effective = max(0.0, min(1.0, decayed_effective))
    level = engine.score_to_level(decayed_effective)  # type: ignore[attr-defined]

    return TrustScore(
        skill_name=score.skill_name,
        version=score.version,
        intrinsic_score=score.intrinsic_score,
        effective_score=decayed_effective,
        level=level,
        signals=score.signals,
    )


def update_with_evidence(
    current: TrustSignals,
    positive_evidence: dict[str, float],
) -> TrustSignals:
    """Update trust signals with new positive evidence.

    Each entry in ``positive_evidence`` maps a signal name to an
    additional trust increment. The increment is added to the current
    signal value, and the result is clamped to [0, 1].

    **Theorem 5 guarantee:** The intrinsic score computed from the
    returned signals is guaranteed to be >= the intrinsic score of
    the ``current`` signals. This holds because:
    1. Only non-negative increments are accepted (negative values raise).
    2. All weights are non-negative.
    3. The linear combination with non-negative weights is monotone.

    Args:
        current: The current trust signals.
        positive_evidence: Dictionary mapping signal names to non-negative
            increments. Valid keys: "provenance", "behavioral",
            "community", "historical".

    Returns:
        A new ``TrustSignals`` with updated values.

    Raises:
        ValueError: If any increment is negative or the signal name
            is not recognized.
    """
    valid_names = {"provenance", "behavioral", "community", "historical"}
    current_dict = current.as_dict()

    for name, evidence_delta in positive_evidence.items():
        if name not in valid_names:
            raise ValueError(
                f"Unknown signal name '{name}'. "
                f"Valid names: {sorted(valid_names)}"
            )
        if evidence_delta < 0.0:
            raise ValueError(
                f"Positive evidence delta must be non-negative for '{name}', "
                f"got {evidence_delta}"
            )
        current_dict[name] = min(1.0, current_dict[name] + evidence_delta)

    return TrustSignals(**current_dict)
