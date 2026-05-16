"""
MAHOUN Validator Pipeline
==========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Unified validation pipeline for all graph mutations.

Every graph write passes through this pipeline before persistence.
The pipeline composes ProvenanceTracker, OntologyEnforcer, and
schema validation into a single fail-closed gate.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata, ProvenanceTracker
from mahoun.core.governance.ontology_enforcer import OntologyEnforcer


@dataclass(frozen=True)
class ValidationGateResult:
    """Immutable result of a single validation gate."""
    gate_name: str
    passed: bool
    violation: Optional[GovernanceViolation] = None


@dataclass(frozen=True)
class PipelineResult:
    """Immutable result of the full validation pipeline."""
    passed: bool
    gate_results: tuple  # Tuple[ValidationGateResult, ...]
    correlation_id: str
    timestamp: str
    pipeline_hash: str

    @property
    def violations(self) -> List[GovernanceViolation]:
        return [g.violation for g in self.gate_results if g.violation is not None]


# Type alias for custom validation functions
ValidationGate = Callable[[Dict[str, Any], Optional[str]], None]


class ValidatorPipeline:
    """Unified validation pipeline for graph mutations.

    Composes multiple validation gates into a single fail-closed pipeline.
    If any gate fails, the entire pipeline fails immediately.

    Built-in gates:
        1. Provenance validation (via ProvenanceTracker)
        2. Ontology validation (via OntologyEnforcer, for relationships)
        3. Schema validation (required fields check)

    Custom gates can be added via add_gate().
    """

    def __init__(
        self,
        provenance_tracker: Optional[ProvenanceTracker] = None,
        ontology_enforcer: Optional[OntologyEnforcer] = None,
    ) -> None:
        self._provenance = provenance_tracker or ProvenanceTracker()
        self._ontology = ontology_enforcer or OntologyEnforcer()
        self._custom_gates: List[tuple] = []  # List of (name, gate_fn)

    def add_gate(self, name: str, gate_fn: ValidationGate) -> None:
        """Add a custom validation gate to the pipeline.

        Args:
            name: Gate name for audit trail.
            gate_fn: Function(data, correlation_id) -> None.
                     Must raise GovernanceViolationError on failure.
        """
        if not name:
            raise ValueError("Gate name cannot be empty")
        self._custom_gates.append((name, gate_fn))

    def validate_node_write(
        self,
        node_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> PipelineResult:
        """Validate a node write through the full pipeline.

        Gates executed:
            1. Provenance check
            2. Required fields check
            3. Custom gates

        Args:
            node_data: Node data dictionary. Must contain 'provenance'.
            correlation_id: Optional correlation ID.

        Returns:
            PipelineResult (always passed=True if we return).

        Raises:
            GovernanceViolationError: On any gate failure (fail-fast).
        """
        results: List[ValidationGateResult] = []
        ts = datetime.now(timezone.utc).isoformat()
        cid = correlation_id or ""

        # Gate 1: Provenance
        try:
            self._provenance.validate_node_provenance(node_data, correlation_id)
            results.append(ValidationGateResult(gate_name="provenance", passed=True))
        except GovernanceViolationError:
            raise  # Fail-fast, no catch

        # Gate 2: Required fields
        required = {"id"}
        missing = required - set(node_data.keys())
        if missing:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.SCHEMA_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=f"Node missing required fields: {sorted(missing)}",
                    details={"missing_fields": sorted(missing)},
                    source="ValidatorPipeline",
                    correlation_id=correlation_id,
                )
            )
        results.append(ValidationGateResult(gate_name="required_fields", passed=True))

        # Gate 3+: Custom gates
        for gate_name, gate_fn in self._custom_gates:
            gate_fn(node_data, correlation_id)
            results.append(ValidationGateResult(gate_name=gate_name, passed=True))

        return PipelineResult(
            passed=True,
            gate_results=tuple(results),
            correlation_id=cid,
            timestamp=ts,
            pipeline_hash=self._compute_hash(node_data),
        )

    def validate_relationship_write(
        self,
        source_type: str,
        relationship_type: str,
        target_type: str,
        relationship_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> PipelineResult:
        """Validate a relationship write through the full pipeline.

        Gates executed:
            1. Ontology check
            2. Provenance check (on relationship data)
            3. Custom gates

        Raises:
            GovernanceViolationError: On any gate failure.
        """
        results: List[ValidationGateResult] = []
        ts = datetime.now(timezone.utc).isoformat()
        cid = correlation_id or ""

        # Gate 1: Ontology
        self._ontology.validate_relationship(
            source_type, relationship_type, target_type, correlation_id
        )
        results.append(ValidationGateResult(gate_name="ontology", passed=True))

        # Gate 2: Provenance on relationship
        prov = relationship_data.get("provenance")
        if prov is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Relationship write rejected: missing provenance for "
                        f"{source_type} -[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "relationship_type": relationship_type,
                        "target_type": target_type,
                    },
                    source="ValidatorPipeline",
                    correlation_id=correlation_id,
                )
            )
        results.append(ValidationGateResult(gate_name="provenance", passed=True))

        # Gate 3+: Custom gates
        for gate_name, gate_fn in self._custom_gates:
            gate_fn(relationship_data, correlation_id)
            results.append(ValidationGateResult(gate_name=gate_name, passed=True))

        return PipelineResult(
            passed=True,
            gate_results=tuple(results),
            correlation_id=cid,
            timestamp=ts,
            pipeline_hash=self._compute_hash(relationship_data),
        )

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """Compute deterministic hash of mutation data."""
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]
