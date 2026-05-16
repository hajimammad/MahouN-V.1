"""
MAHOUN Governance Violations
=============================

Classification: CRITICAL / SHARED GOVERNANCE MODEL
Purpose: Unified violation model used by both Runtime and Lifecycle governance layers.

All governance violations — runtime and CI — use these types. No ad hoc
violation dicts or untyped error strings are allowed.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class ViolationCategory(str, Enum):
    """Categories of governance violations.

    Used by both Runtime and Lifecycle governance layers.
    """

    # Runtime violations
    MISSING_PROVENANCE = "MISSING_PROVENANCE"
    ONTOLOGY_VIOLATION = "ONTOLOGY_VIOLATION"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    MISSING_PROOF_TREE = "MISSING_PROOF_TREE"
    LOW_AGREEMENT_SCORE = "LOW_AGREEMENT_SCORE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    AUDIT_TRAIL_INCOMPLETE = "AUDIT_TRAIL_INCOMPLETE"
    SILENT_FAILURE = "SILENT_FAILURE"

    # Lifecycle / CI violations
    FORBIDDEN_PATTERN = "FORBIDDEN_PATTERN"
    ARCHITECTURE_BOUNDARY = "ARCHITECTURE_BOUNDARY"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    COVERAGE_DEFICIT = "COVERAGE_DEFICIT"
    CANONICAL_ENV_BYPASS = "CANONICAL_ENV_BYPASS"
    SECURITY_VULNERABILITY = "SECURITY_VULNERABILITY"


class ViolationSeverity(str, Enum):
    """Severity levels for governance violations.

    CRITICAL and HIGH violations always halt execution.
    There are no MEDIUM/LOW/WARNING severities — all violations
    are hard failures in the governance kernel.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"


@dataclass(frozen=True)
class GovernanceViolation:
    """Immutable record of a governance violation.

    Every governance failure — runtime or CI — produces one of these.
    Immutability is enforced via frozen=True.

    Attributes:
        category: What type of violation occurred.
        severity: How severe the violation is (always CRITICAL or HIGH).
        message: Human-readable description.
        details: Machine-readable context for forensic analysis.
        timestamp: UTC timestamp when the violation was detected.
        source: Which governance component detected the violation.
        correlation_id: Optional correlation ID for tracing.
    """

    category: ViolationCategory
    severity: ViolationSeverity
    message: str
    details: Dict[str, Any]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source: str = ""
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for logging and audit trail."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }


class GovernanceViolationError(Exception):
    """Exception raised on any governance violation.

    This exception is NON-BYPASSABLE. It carries the full
    GovernanceViolation record for forensic analysis.

    This is the single exception type for all governance failures.
    No governance component may raise a different exception type
    for policy violations.
    """

    def __init__(self, violation: GovernanceViolation) -> None:
        self.violation = violation
        super().__init__(self._format())

    def _format(self) -> str:
        v = self.violation
        return (
            f"[GOVERNANCE VIOLATION] {v.severity.value} / {v.category.value}\n"
            f"Message: {v.message}\n"
            f"Source: {v.source}\n"
            f"Correlation ID: {v.correlation_id}\n"
            f"Timestamp: {v.timestamp}\n"
            f"Details: {v.details}"
        )
