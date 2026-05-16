"""
MAHOUN Deterministic Resolver
==============================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Deterministic conflict resolution with explicit tier priority.

Tier Priority (highest to lowest):
    1. Constitutional/Statutory Law
    2. Judicial Precedent
    3. Regulatory/Administrative Law
    4. Expert Opinion / Doctrine
    5. User-Provided Input

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)


class SourceTier(IntEnum):
    """Priority tiers. Lower value = higher priority."""
    CONSTITUTIONAL = 1
    JUDICIAL_PRECEDENT = 2
    REGULATORY = 3
    EXPERT_OPINION = 4
    USER_INPUT = 5


@dataclass(frozen=True)
class ConflictCandidate:
    """Immutable candidate in a conflict resolution."""
    entity_id: str
    value: Any
    tier: SourceTier
    confidence: float
    source: str
    metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("entity_id cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass(frozen=True)
class ResolutionResult:
    """Immutable result of conflict resolution."""
    winner: ConflictCandidate
    losers: Tuple[ConflictCandidate, ...]
    resolution_reason: str
    was_tie: bool = False


class DeterministicResolver:
    """Deterministic conflict resolution with explicit tier priority.

    Rules (applied in order):
        1. Lowest tier number wins.
        2. If tiers equal, highest confidence wins.
        3. If confidence equal (within epsilon), HALT with error.
    """

    CONFIDENCE_EPSILON: float = 1e-9

    def resolve(
        self,
        candidates: Sequence[ConflictCandidate],
        correlation_id: Optional[str] = None,
    ) -> ResolutionResult:
        """Resolve a conflict between candidates.

        Raises:
            GovernanceViolationError: On < 2 candidates or unresolvable tie.
        """
        if len(candidates) < 2:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.DETERMINISM_FAILURE,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Need >= 2 candidates, got {len(candidates)}",
                    details={"candidate_count": len(candidates)},
                    source="DeterministicResolver",
                    correlation_id=correlation_id,
                )
            )

        sorted_candidates = sorted(
            candidates, key=lambda c: (c.tier.value, -c.confidence)
        )
        best = sorted_candidates[0]
        runner_up = sorted_candidates[1]

        if best.tier == runner_up.tier:
            if abs(best.confidence - runner_up.confidence) < self.CONFIDENCE_EPSILON:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.DETERMINISM_FAILURE,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"Unresolvable tie: '{best.entity_id}' and "
                            f"'{runner_up.entity_id}' same tier "
                            f"({best.tier.name}) and confidence ({best.confidence:.6f})"
                        ),
                        details={
                            "candidate_1": {"id": best.entity_id, "tier": best.tier.name, "conf": best.confidence},
                            "candidate_2": {"id": runner_up.entity_id, "tier": runner_up.tier.name, "conf": runner_up.confidence},
                        },
                        source="DeterministicResolver",
                        correlation_id=correlation_id,
                    )
                )
            reason = f"Same tier ({best.tier.name}), confidence {best.confidence:.4f} > {runner_up.confidence:.4f}"
        else:
            reason = f"Tier priority: {best.tier.name} > {runner_up.tier.name}"

        losers = tuple(c for c in sorted_candidates if c is not best)
        return ResolutionResult(winner=best, losers=losers, resolution_reason=reason)

    def resolve_entity_merge(
        self,
        entity_id: str,
        conflicting_values: List[Tuple[Any, SourceTier, float, str]],
        correlation_id: Optional[str] = None,
    ) -> Tuple[Any, str]:
        """Convenience: resolve entity field conflicts. Returns (value, reason)."""
        candidates = [
            ConflictCandidate(
                entity_id=f"{entity_id}:{i}", value=v, tier=t,
                confidence=c, source=s, metadata={},
            )
            for i, (v, t, c, s) in enumerate(conflicting_values)
        ]
        result = self.resolve(candidates, correlation_id=correlation_id)
        return result.winner.value, result.resolution_reason
