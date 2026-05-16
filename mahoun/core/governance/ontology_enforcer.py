"""
MAHOUN Ontology Enforcer
=========================

Classification: CRITICAL / RUNTIME GOVERNANCE
Purpose: Enforce ontology rules before relationship creation.

Relationships between graph nodes must conform to the MAHOUN legal
ontology. Invalid relationships are rejected immediately with
GovernanceViolationError.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Set, Tuple

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)


@dataclass(frozen=True)
class OntologyRule:
    """Immutable ontology rule defining valid relationship patterns.

    Attributes:
        source_type: Type of the source node (e.g., 'Law', 'Case').
        relationship_type: Type of relationship (e.g., 'CITES', 'AMENDS').
        target_type: Type of the target node.
        description: Human-readable description of the rule.
        bidirectional: Whether the relationship can go both ways.
    """

    source_type: str
    relationship_type: str
    target_type: str
    description: str = ""
    bidirectional: bool = False


# Default MAHOUN legal ontology rules
_DEFAULT_ONTOLOGY_RULES: Tuple[OntologyRule, ...] = (
    # Law relationships
    OntologyRule("Law", "AMENDS", "Law", "A law amends another law"),
    OntologyRule("Law", "REPEALS", "Law", "A law repeals another law"),
    OntologyRule("Law", "SUPERSEDES", "Law", "A law supersedes another law"),
    OntologyRule("Law", "REFERENCES", "Law", "A law references another law"),
    OntologyRule("Law", "IMPLEMENTS", "Law", "A law implements another law"),
    # Case relationships
    OntologyRule("Case", "CITES", "Law", "A case cites a law"),
    OntologyRule("Case", "CITES", "Case", "A case cites another case"),
    OntologyRule("Case", "APPLIES", "Law", "A case applies a law"),
    OntologyRule("Case", "INTERPRETS", "Law", "A case interprets a law"),
    OntologyRule("Case", "OVERRULES", "Case", "A case overrules another case"),
    OntologyRule("Case", "FOLLOWS", "Case", "A case follows another case"),
    OntologyRule("Case", "DISTINGUISHES", "Case", "A case distinguishes another"),
    # Document relationships
    OntologyRule("Document", "REFERENCES", "Law", "A document references a law"),
    OntologyRule("Document", "REFERENCES", "Case", "A document references a case"),
    OntologyRule("Document", "CONTAINS", "Entity", "A document contains an entity"),
    OntologyRule("Document", "DISCUSSES", "Topic", "A document discusses a topic"),
    # Entity relationships
    OntologyRule("Entity", "MENTIONED_IN", "Document", "An entity is mentioned in a document"),
    OntologyRule("Entity", "PARTY_TO", "Case", "An entity is party to a case"),
    OntologyRule("Entity", "SUBJECT_OF", "Law", "An entity is subject of a law"),
    # Topic relationships
    OntologyRule("Topic", "RELATES_TO", "Topic", "A topic relates to another topic", bidirectional=True),
    # Verdict/Reasoning relationships
    OntologyRule("Verdict", "BASED_ON", "Law", "A verdict is based on a law"),
    OntologyRule("Verdict", "BASED_ON", "Case", "A verdict is based on a case"),
    OntologyRule("Verdict", "DERIVED_FROM", "Evidence", "A verdict is derived from evidence"),
    OntologyRule("Evidence", "SUPPORTS", "Verdict", "Evidence supports a verdict"),
    OntologyRule("Evidence", "CONTRADICTS", "Verdict", "Evidence contradicts a verdict"),
    OntologyRule("Evidence", "EXTRACTED_FROM", "Document", "Evidence extracted from a document"),
)


class OntologyEnforcer:
    """Enforce ontology rules before relationship creation.

    This enforcer validates that relationship types between node types
    conform to the MAHOUN legal ontology. Invalid relationships are
    rejected with GovernanceViolationError.

    The enforcer operates in STRICT mode only — no warnings, no soft
    failures, no fallbacks.
    """

    def __init__(
        self,
        rules: Optional[Tuple[OntologyRule, ...]] = None,
    ) -> None:
        """Initialize the ontology enforcer.

        Args:
            rules: Ontology rules to enforce. Defaults to MAHOUN legal ontology.
        """
        effective_rules = rules if rules is not None else _DEFAULT_ONTOLOGY_RULES
        # Build lookup index: (source_type, relationship_type, target_type) -> rule
        self._rules: Dict[Tuple[str, str, str], OntologyRule] = {}
        for rule in effective_rules:
            key = (rule.source_type, rule.relationship_type, rule.target_type)
            self._rules[key] = rule
            if rule.bidirectional:
                reverse_key = (
                    rule.target_type,
                    rule.relationship_type,
                    rule.source_type,
                )
                self._rules[reverse_key] = rule

        # Build valid relationship types per source type
        self._valid_relationships: Dict[str, Set[str]] = {}
        for src, rel, tgt in self._rules:
            if src not in self._valid_relationships:
                self._valid_relationships[src] = set()
            self._valid_relationships[src].add(rel)

    def validate_relationship(
        self,
        source_type: str,
        relationship_type: str,
        target_type: str,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Validate that a relationship conforms to the ontology.

        Args:
            source_type: Type of the source node.
            relationship_type: Type of the relationship.
            target_type: Type of the target node.
            correlation_id: Optional correlation ID for tracing.

        Raises:
            GovernanceViolationError: If the relationship is not in the ontology.
        """
        key = (source_type, relationship_type, target_type)

        if key not in self._rules:
            # Determine the specific failure reason
            if source_type not in self._valid_relationships:
                detail_msg = (
                    f"Unknown source type '{source_type}'. "
                    f"Known types: {sorted(self._valid_relationships.keys())}"
                )
            elif relationship_type not in self._valid_relationships.get(
                source_type, set()
            ):
                detail_msg = (
                    f"Invalid relationship '{relationship_type}' for "
                    f"source type '{source_type}'. "
                    f"Valid relationships: "
                    f"{sorted(self._valid_relationships.get(source_type, set()))}"
                )
            else:
                detail_msg = (
                    f"Relationship '{source_type} -[{relationship_type}]-> "
                    f"{target_type}' does not match any ontology rule"
                )

            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.ONTOLOGY_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message=(
                        f"Ontology violation: {source_type} "
                        f"-[{relationship_type}]-> {target_type}"
                    ),
                    details={
                        "source_type": source_type,
                        "relationship_type": relationship_type,
                        "target_type": target_type,
                        "detail": detail_msg,
                    },
                    source="OntologyEnforcer",
                    correlation_id=correlation_id,
                )
            )

    def get_valid_relationships(
        self, source_type: str
    ) -> FrozenSet[str]:
        """Get valid relationship types for a given source type.

        Args:
            source_type: Node type to query.

        Returns:
            Frozen set of valid relationship type names.
        """
        return frozenset(self._valid_relationships.get(source_type, set()))

    def get_valid_targets(
        self, source_type: str, relationship_type: str
    ) -> FrozenSet[str]:
        """Get valid target types for a source type and relationship.

        Args:
            source_type: Source node type.
            relationship_type: Relationship type.

        Returns:
            Frozen set of valid target node types.
        """
        targets: Set[str] = set()
        for (src, rel, tgt), _rule in self._rules.items():
            if src == source_type and rel == relationship_type:
                targets.add(tgt)
        return frozenset(targets)

    @property
    def rule_count(self) -> int:
        """Total number of ontology rules (including bidirectional expansions)."""
        return len(self._rules)
