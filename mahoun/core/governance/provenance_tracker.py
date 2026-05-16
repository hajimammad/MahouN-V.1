"""
MAHOUN Provenance Tracker
==========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Enforce mandatory provenance metadata on all graph writes.

Every node and relationship added to the knowledge graph MUST carry
provenance metadata. Writes without provenance are rejected immediately
with GovernanceViolationError.

Provenance metadata is immutable after creation (frozen dataclass).

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Optional

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)

# Fields that MUST be present in every provenance record
REQUIRED_PROVENANCE_FIELDS: FrozenSet[str] = frozenset(
    {"source", "timestamp", "correlation_id", "author"}
)


@dataclass(frozen=True)
class ProvenanceMetadata:
    """Immutable provenance record for graph entities.

    Every graph node and relationship must be created with
    a ProvenanceMetadata instance. This record is immutable
    and cannot be modified after creation.

    Attributes:
        source: Origin of the data (e.g., 'document_ingestion', 'user_input').
        timestamp: UTC ISO-8601 timestamp of creation.
        correlation_id: Correlation ID for tracing the operation.
        author: Identifier of the actor that created the entity.
        document_id: Optional source document identifier.
        pipeline_version: Optional version of the processing pipeline.
        extra: Additional provenance fields (frozen after creation).
    """

    source: str
    timestamp: str
    correlation_id: str
    author: str
    document_id: Optional[str] = None
    pipeline_version: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate all required fields are non-empty."""
        if not self.source:
            raise ValueError("Provenance 'source' cannot be empty")
        if not self.timestamp:
            raise ValueError("Provenance 'timestamp' cannot be empty")
        if not self.correlation_id:
            raise ValueError("Provenance 'correlation_id' cannot be empty")
        if not self.author:
            raise ValueError("Provenance 'author' cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for storage."""
        result: Dict[str, Any] = {
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "author": self.author,
        }
        if self.document_id is not None:
            result["document_id"] = self.document_id
        if self.pipeline_version is not None:
            result["pipeline_version"] = self.pipeline_version
        return result

    @classmethod
    def create(
        cls,
        source: str,
        correlation_id: str,
        author: str,
        document_id: Optional[str] = None,
        pipeline_version: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """Factory method with automatic timestamp.

        Args:
            source: Origin of the data.
            correlation_id: Correlation ID for tracing.
            author: Actor identifier.
            document_id: Optional source document ID.
            pipeline_version: Optional pipeline version.

        Returns:
            Immutable ProvenanceMetadata instance.
        """
        return cls(
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            author=author,
            document_id=document_id,
            pipeline_version=pipeline_version,
        )


class ProvenanceTracker:
    """Enforcement layer for mandatory provenance on graph writes.

    This tracker validates that every graph mutation includes valid
    provenance metadata. It is integrated into the ValidatorPipeline
    and runs before any graph persistence.

    Fail-closed: Missing or invalid provenance raises GovernanceViolationError.
    """

    def validate_provenance(
        self,
        provenance: Optional[ProvenanceMetadata],
        entity_type: str,
        entity_id: str,
        correlation_id: Optional[str] = None,
    ) -> ProvenanceMetadata:
        """Validate that provenance metadata is present and complete.

        Args:
            provenance: Provenance metadata to validate (must not be None).
            entity_type: Type of entity being written (node/relationship).
            entity_id: Identifier of the entity.
            correlation_id: Optional correlation ID for error reporting.

        Returns:
            The validated ProvenanceMetadata (pass-through on success).

        Raises:
            GovernanceViolationError: If provenance is missing or invalid.
        """
        if provenance is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Graph write rejected: missing provenance metadata "
                        f"for {entity_type} '{entity_id}'"
                    ),
                    details={
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        # Validate all required fields are non-empty
        missing_fields = []
        for field_name in REQUIRED_PROVENANCE_FIELDS:
            value = getattr(provenance, field_name, None)
            if not value:
                missing_fields.append(field_name)

        if missing_fields:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Graph write rejected: incomplete provenance for "
                        f"{entity_type} '{entity_id}'. "
                        f"Missing fields: {sorted(missing_fields)}"
                    ),
                    details={
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "missing_fields": sorted(missing_fields),
                        "provided_fields": [
                            f
                            for f in REQUIRED_PROVENANCE_FIELDS
                            if f not in missing_fields
                        ],
                    },
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        return provenance

    def validate_node_provenance(
        self,
        node_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate provenance in a node data dictionary.

        Checks that the node dictionary contains a 'provenance' key
        with a valid ProvenanceMetadata or dict representation.

        Args:
            node_data: Node data dictionary.
            correlation_id: Optional correlation ID.

        Returns:
            The validated node_data (pass-through on success).

        Raises:
            GovernanceViolationError: If provenance is missing or invalid.
        """
        node_id = node_data.get("id", node_data.get("name", "<unknown>"))
        provenance_raw = node_data.get("provenance")

        if provenance_raw is None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.MISSING_PROVENANCE,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Node write rejected: 'provenance' key missing "
                        f"from node data for '{node_id}'"
                    ),
                    details={"node_id": str(node_id)},
                    source="ProvenanceTracker",
                    correlation_id=correlation_id,
                )
            )

        if isinstance(provenance_raw, ProvenanceMetadata):
            return node_data

        if isinstance(provenance_raw, dict):
            # Validate required fields exist in the dict
            missing = [
                f for f in REQUIRED_PROVENANCE_FIELDS if not provenance_raw.get(f)
            ]
            if missing:
                raise GovernanceViolationError(
                    GovernanceViolation(
                        category=ViolationCategory.MISSING_PROVENANCE,
                        severity=ViolationSeverity.CRITICAL,
                        message=(
                            f"Node write rejected: incomplete provenance dict "
                            f"for '{node_id}'. Missing: {sorted(missing)}"
                        ),
                        details={
                            "node_id": str(node_id),
                            "missing_fields": sorted(missing),
                        },
                        source="ProvenanceTracker",
                        correlation_id=correlation_id,
                    )
                )
            return node_data

        raise GovernanceViolationError(
            GovernanceViolation(
                category=ViolationCategory.MISSING_PROVENANCE,
                severity=ViolationSeverity.CRITICAL,
                message=(
                    f"Node write rejected: 'provenance' must be "
                    f"ProvenanceMetadata or dict, got {type(provenance_raw).__name__}"
                ),
                details={
                    "node_id": str(node_id),
                    "provenance_type": type(provenance_raw).__name__,
                },
                source="ProvenanceTracker",
                correlation_id=correlation_id,
            )
        )
