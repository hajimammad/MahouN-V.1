"""
MAHOUN Governance Policies
===========================

Classification: CRITICAL / CENTRALIZED POLICY DEFINITIONS
Purpose: Single source of truth for all governance policies.

Policies are loaded from constitution/RedLines.yaml and are immutable
after initialization. Both Runtime and Lifecycle governance layers
consume policies from this module.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class GovernancePolicy:
    """Immutable governance policy definition.

    Attributes:
        name: Policy identifier (e.g., 'proof_tree_required').
        description: Human-readable description.
        enabled: Whether the policy is active.
        threshold: Numeric threshold (if applicable).
        required_fields: Fields that must be present.
        forbidden_patterns: Patterns that must not appear.
    """

    name: str
    description: str
    enabled: bool = True
    threshold: Optional[float] = None
    required_fields: FrozenSet[str] = field(default_factory=frozenset)
    forbidden_patterns: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Policy name cannot be empty")
        if self.threshold is not None and not (0.0 <= self.threshold <= 1.0):
            if self.name not in (
                "max_reasoning_time_ms",
                "max_recursion_depth",
            ):
                raise ValueError(
                    f"Threshold must be in [0.0, 1.0] for policy '{self.name}', "
                    f"got {self.threshold}"
                )


class PolicyRegistry:
    """Thread-safe, immutable registry of governance policies.

    Policies are loaded once and cannot be modified at runtime.
    This ensures deterministic policy enforcement.
    """

    def __init__(self, policies: List[GovernancePolicy]) -> None:
        self._policies: Dict[str, GovernancePolicy] = {}
        for policy in policies:
            if policy.name in self._policies:
                raise ValueError(f"Duplicate policy name: {policy.name}")
            self._policies[policy.name] = policy
        self._frozen = True

    def get(self, name: str) -> GovernancePolicy:
        """Get policy by name.

        Raises:
            KeyError: If policy does not exist.
        """
        if name not in self._policies:
            raise KeyError(f"Unknown governance policy: {name}")
        return self._policies[name]

    def get_all(self) -> Tuple[GovernancePolicy, ...]:
        """Get all policies as an immutable tuple."""
        return tuple(self._policies.values())

    def get_enabled(self) -> Tuple[GovernancePolicy, ...]:
        """Get all enabled policies."""
        return tuple(p for p in self._policies.values() if p.enabled)

    def __len__(self) -> int:
        return len(self._policies)

    def __contains__(self, name: str) -> bool:
        return name in self._policies


def load_redlines_policies(
    config_path: Optional[Path] = None,
) -> PolicyRegistry:
    """Load governance policies from RedLines.yaml.

    Args:
        config_path: Path to RedLines.yaml. Defaults to
            constitution/RedLines.yaml relative to project root.

    Returns:
        Immutable PolicyRegistry.

    Raises:
        FileNotFoundError: If RedLines.yaml does not exist.
        ValueError: If configuration is invalid.
    """
    if config_path is None:
        config_path = (
            Path(__file__).parent.parent.parent.parent
            / "constitution"
            / "RedLines.yaml"
        )

    if not config_path.exists():
        raise FileNotFoundError(
            f"RedLines configuration not found: {config_path}"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f)

    policies: List[GovernancePolicy] = []

    # Threshold policies
    thresholds = raw.get("thresholds", {})
    policies.append(
        GovernancePolicy(
            name="min_agreement_score",
            description="Minimum agreement score between symbolic and neural reasoning",
            threshold=float(thresholds.get("min_agreement_score", 0.85)),
        )
    )
    policies.append(
        GovernancePolicy(
            name="min_confidence_score",
            description="Minimum confidence score for reasoning verdicts",
            threshold=float(thresholds.get("min_confidence_score", 0.70)),
        )
    )

    # Proof requirements
    proof_reqs = raw.get("proof_requirements", {})
    policies.append(
        GovernancePolicy(
            name="proof_tree_required",
            description="Every reasoning response must contain a proof_tree",
            enabled=bool(proof_reqs.get("proof_tree_required", True)),
            required_fields=frozenset({"proof_tree"}),
        )
    )
    policies.append(
        GovernancePolicy(
            name="evidence_linkage_required",
            description="Proof tree must contain evidence linkage",
            enabled=bool(proof_reqs.get("evidence_linkage_required", True)),
            required_fields=frozenset({"derived_facts"}),
        )
    )
    policies.append(
        GovernancePolicy(
            name="audit_trail_required",
            description="Audit trail must be complete",
            enabled=bool(proof_reqs.get("audit_trail_required", True)),
            required_fields=frozenset({"reasoning_mode", "execution_time_ms"}),
        )
    )

    # Hallucination prevention
    hallu = raw.get("hallucination_prevention", {})
    policies.append(
        GovernancePolicy(
            name="require_graph_evidence",
            description="Reject responses without graph evidence",
            enabled=bool(hallu.get("require_graph_evidence", True)),
        )
    )
    policies.append(
        GovernancePolicy(
            name="require_determinism",
            description="Require deterministic execution",
            enabled=bool(hallu.get("require_determinism", True)),
        )
    )
    policies.append(
        GovernancePolicy(
            name="reject_contradictions",
            description="Reject responses with contradictions",
            enabled=bool(hallu.get("reject_contradictions", True)),
        )
    )

    # Exceptions policy
    exceptions = raw.get("exceptions", {})
    policies.append(
        GovernancePolicy(
            name="no_silent_failures",
            description="Silent exception swallowing is forbidden",
            enabled=not bool(exceptions.get("allow_silent_failures", False)),
        )
    )

    # CI enforcement
    ci = raw.get("ci_enforcement", {})
    policies.append(
        GovernancePolicy(
            name="ci_fail_on_violation",
            description="CI must fail on RedLine violations",
            enabled=bool(ci.get("fail_ci_on_violation", True)),
        )
    )
    policies.append(
        GovernancePolicy(
            name="ci_block_merge_on_failure",
            description="Block merge on governance failures",
            enabled=bool(ci.get("block_merge_on_failure", True)),
        )
    )

    # Provenance policy (derived from audit requirements)
    audit = raw.get("audit", {})
    policies.append(
        GovernancePolicy(
            name="require_provenance",
            description="Every graph node/relationship must carry provenance metadata",
            enabled=bool(audit.get("require_correlation_id", True)),
            required_fields=frozenset(
                {"source", "timestamp", "correlation_id", "author"}
            ),
        )
    )

    return PolicyRegistry(policies)
