"""
MAHOUN Governance Kernel Tests
================================

Classification: CRITICAL / TEST ENFORCEMENT
Purpose: Deterministic tests for all governance kernel components.

Covers:
    - GovernanceViolation and GovernanceViolationError
    - PolicyRegistry and load_redlines_policies
    - ProvenanceTracker
    - OntologyEnforcer
    - DeterministicResolver
    - ValidatorPipeline

All tests are deterministic, no external dependencies, no randomness.

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

import pytest
from typing import Dict, Any

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)
from mahoun.core.governance.policies import (
    GovernancePolicy,
    PolicyRegistry,
    load_redlines_policies,
)
from mahoun.core.governance.provenance_tracker import (
    ProvenanceMetadata,
    ProvenanceTracker,
    REQUIRED_PROVENANCE_FIELDS,
)
from mahoun.core.governance.ontology_enforcer import (
    OntologyEnforcer,
    OntologyRule,
)
from mahoun.core.governance.deterministic_resolver import (
    ConflictCandidate,
    DeterministicResolver,
    ResolutionResult,
    SourceTier,
)
from mahoun.core.governance.validator_pipeline import (
    ValidatorPipeline,
    PipelineResult,
)


# ============================================================================
# VIOLATION MODEL TESTS
# ============================================================================


class TestGovernanceViolation:
    """Tests for the unified violation model."""

    def test_violation_is_frozen(self) -> None:
        v = GovernanceViolation(
            category=ViolationCategory.MISSING_PROVENANCE,
            severity=ViolationSeverity.CRITICAL,
            message="test",
            details={},
        )
        with pytest.raises(AttributeError):
            v.message = "changed"  # type: ignore[misc]

    def test_violation_to_dict(self) -> None:
        v = GovernanceViolation(
            category=ViolationCategory.ONTOLOGY_VIOLATION,
            severity=ViolationSeverity.HIGH,
            message="bad relationship",
            details={"key": "value"},
            source="test",
            correlation_id="corr-1",
        )
        d = v.to_dict()
        assert d["category"] == "ONTOLOGY_VIOLATION"
        assert d["severity"] == "HIGH"
        assert d["message"] == "bad relationship"
        assert d["details"] == {"key": "value"}
        assert d["source"] == "test"
        assert d["correlation_id"] == "corr-1"

    def test_violation_has_timestamp(self) -> None:
        v = GovernanceViolation(
            category=ViolationCategory.SCHEMA_DRIFT,
            severity=ViolationSeverity.CRITICAL,
            message="drift",
            details={},
        )
        assert v.timestamp  # Non-empty
        assert "T" in v.timestamp  # ISO format

    def test_violation_error_carries_violation(self) -> None:
        v = GovernanceViolation(
            category=ViolationCategory.FORBIDDEN_PATTERN,
            severity=ViolationSeverity.CRITICAL,
            message="found bare except",
            details={"file": "test.py", "line": 42},
        )
        err = GovernanceViolationError(v)
        assert err.violation is v
        assert "GOVERNANCE VIOLATION" in str(err)
        assert "FORBIDDEN_PATTERN" in str(err)

    def test_all_categories_are_str_enum(self) -> None:
        for cat in ViolationCategory:
            assert isinstance(cat.value, str)

    def test_only_critical_and_high_severities(self) -> None:
        values = {s.value for s in ViolationSeverity}
        assert values == {"CRITICAL", "HIGH"}


# ============================================================================
# POLICY TESTS
# ============================================================================


class TestGovernancePolicy:
    """Tests for governance policy definitions."""

    def test_policy_is_frozen(self) -> None:
        p = GovernancePolicy(name="test", description="desc")
        with pytest.raises(AttributeError):
            p.name = "changed"  # type: ignore[misc]

    def test_policy_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="name cannot be empty"):
            GovernancePolicy(name="", description="desc")

    def test_policy_invalid_threshold_rejected(self) -> None:
        with pytest.raises(ValueError, match="Threshold"):
            GovernancePolicy(name="bad", description="desc", threshold=1.5)

    def test_policy_valid_threshold(self) -> None:
        p = GovernancePolicy(name="valid", description="desc", threshold=0.85)
        assert p.threshold == 0.85


class TestPolicyRegistry:
    """Tests for policy registry."""

    def test_registry_get(self) -> None:
        p = GovernancePolicy(name="test_policy", description="test")
        reg = PolicyRegistry([p])
        assert reg.get("test_policy") is p

    def test_registry_unknown_key_raises(self) -> None:
        reg = PolicyRegistry([])
        with pytest.raises(KeyError, match="Unknown governance policy"):
            reg.get("nonexistent")

    def test_registry_duplicate_name_rejected(self) -> None:
        p1 = GovernancePolicy(name="dup", description="first")
        p2 = GovernancePolicy(name="dup", description="second")
        with pytest.raises(ValueError, match="Duplicate policy"):
            PolicyRegistry([p1, p2])

    def test_registry_contains(self) -> None:
        p = GovernancePolicy(name="exists", description="yes")
        reg = PolicyRegistry([p])
        assert "exists" in reg
        assert "missing" not in reg

    def test_registry_get_enabled(self) -> None:
        p1 = GovernancePolicy(name="on", description="on", enabled=True)
        p2 = GovernancePolicy(name="off", description="off", enabled=False)
        reg = PolicyRegistry([p1, p2])
        enabled = reg.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "on"

    def test_load_redlines_policies(self) -> None:
        """Load from real RedLines.yaml — must not crash."""
        registry = load_redlines_policies()
        assert len(registry) > 0
        assert "min_agreement_score" in registry
        assert "proof_tree_required" in registry
        assert "require_provenance" in registry


# ============================================================================
# PROVENANCE TRACKER TESTS
# ============================================================================


class TestProvenanceMetadata:
    """Tests for ProvenanceMetadata."""

    def test_metadata_is_frozen(self) -> None:
        m = ProvenanceMetadata(
            source="test", timestamp="2026-01-01T00:00:00Z",
            correlation_id="c-1", author="tester",
        )
        with pytest.raises(AttributeError):
            m.source = "changed"  # type: ignore[misc]

    def test_metadata_empty_source_rejected(self) -> None:
        with pytest.raises(ValueError, match="source"):
            ProvenanceMetadata(
                source="", timestamp="t", correlation_id="c", author="a"
            )

    def test_metadata_empty_correlation_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="correlation_id"):
            ProvenanceMetadata(
                source="s", timestamp="t", correlation_id="", author="a"
            )

    def test_metadata_create_factory(self) -> None:
        m = ProvenanceMetadata.create(
            source="ingestion", correlation_id="c-1", author="system"
        )
        assert m.source == "ingestion"
        assert m.correlation_id == "c-1"
        assert m.timestamp  # Auto-set

    def test_metadata_to_dict(self) -> None:
        m = ProvenanceMetadata.create(
            source="test", correlation_id="c-1", author="tester",
            document_id="doc-1",
        )
        d = m.to_dict()
        assert d["source"] == "test"
        assert d["document_id"] == "doc-1"


class TestProvenanceTracker:
    """Tests for ProvenanceTracker enforcement."""

    def setup_method(self) -> None:
        self.tracker = ProvenanceTracker()

    def test_none_provenance_rejected(self) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            self.tracker.validate_provenance(
                provenance=None, entity_type="node", entity_id="n1"
            )
        assert exc_info.value.violation.category == ViolationCategory.MISSING_PROVENANCE

    def test_valid_provenance_passes(self) -> None:
        m = ProvenanceMetadata.create(
            source="test", correlation_id="c-1", author="tester"
        )
        result = self.tracker.validate_provenance(
            provenance=m, entity_type="node", entity_id="n1"
        )
        assert result is m

    def test_node_without_provenance_key_rejected(self) -> None:
        node = {"id": "n1", "name": "Test Node"}
        with pytest.raises(GovernanceViolationError):
            self.tracker.validate_node_provenance(node)

    def test_node_with_valid_provenance_dict_passes(self) -> None:
        node = {
            "id": "n1",
            "provenance": {
                "source": "test",
                "timestamp": "2026-01-01T00:00:00Z",
                "correlation_id": "c-1",
                "author": "tester",
            },
        }
        result = self.tracker.validate_node_provenance(node)
        assert result is node

    def test_node_with_incomplete_provenance_dict_rejected(self) -> None:
        node = {
            "id": "n1",
            "provenance": {"source": "test"},  # Missing fields
        }
        with pytest.raises(GovernanceViolationError):
            self.tracker.validate_node_provenance(node)

    def test_node_with_provenance_metadata_object_passes(self) -> None:
        m = ProvenanceMetadata.create(
            source="test", correlation_id="c-1", author="tester"
        )
        node: Dict[str, Any] = {"id": "n1", "provenance": m}
        result = self.tracker.validate_node_provenance(node)
        assert result is node

    def test_node_with_invalid_provenance_type_rejected(self) -> None:
        node: Dict[str, Any] = {"id": "n1", "provenance": 42}
        with pytest.raises(GovernanceViolationError):
            self.tracker.validate_node_provenance(node)


# ============================================================================
# ONTOLOGY ENFORCER TESTS
# ============================================================================


class TestOntologyEnforcer:
    """Tests for ontology enforcement."""

    def setup_method(self) -> None:
        self.enforcer = OntologyEnforcer()

    def test_valid_relationship_passes(self) -> None:
        # Should not raise
        self.enforcer.validate_relationship("Law", "AMENDS", "Law")
        self.enforcer.validate_relationship("Case", "CITES", "Law")
        self.enforcer.validate_relationship("Document", "CONTAINS", "Entity")

    def test_invalid_relationship_rejected(self) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            self.enforcer.validate_relationship("Law", "CONTAINS", "Entity")
        assert exc_info.value.violation.category == ViolationCategory.ONTOLOGY_VIOLATION

    def test_unknown_source_type_rejected(self) -> None:
        with pytest.raises(GovernanceViolationError):
            self.enforcer.validate_relationship("Unknown", "CITES", "Law")

    def test_get_valid_relationships(self) -> None:
        rels = self.enforcer.get_valid_relationships("Law")
        assert "AMENDS" in rels
        assert "REPEALS" in rels

    def test_get_valid_targets(self) -> None:
        targets = self.enforcer.get_valid_targets("Case", "CITES")
        assert "Law" in targets
        assert "Case" in targets

    def test_custom_rules(self) -> None:
        custom = (OntologyRule("Custom", "LINKS", "Custom", "test"),)
        enforcer = OntologyEnforcer(rules=custom)
        enforcer.validate_relationship("Custom", "LINKS", "Custom")
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_relationship("Law", "AMENDS", "Law")

    def test_bidirectional_rule(self) -> None:
        rules = (
            OntologyRule("A", "RELATES", "B", "test", bidirectional=True),
        )
        enforcer = OntologyEnforcer(rules=rules)
        enforcer.validate_relationship("A", "RELATES", "B")
        enforcer.validate_relationship("B", "RELATES", "A")  # Reverse


# ============================================================================
# DETERMINISTIC RESOLVER TESTS
# ============================================================================


class TestDeterministicResolver:
    """Tests for deterministic conflict resolution."""

    def setup_method(self) -> None:
        self.resolver = DeterministicResolver()

    def _candidate(
        self, eid: str, tier: SourceTier, conf: float
    ) -> ConflictCandidate:
        return ConflictCandidate(
            entity_id=eid, value=f"value_{eid}",
            tier=tier, confidence=conf,
            source="test", metadata={},
        )

    def test_tier_priority_wins(self) -> None:
        c1 = self._candidate("a", SourceTier.CONSTITUTIONAL, 0.8)
        c2 = self._candidate("b", SourceTier.USER_INPUT, 0.99)
        result = self.resolver.resolve([c1, c2])
        assert result.winner.entity_id == "a"
        assert "Tier priority" in result.resolution_reason

    def test_confidence_breaks_same_tier(self) -> None:
        c1 = self._candidate("a", SourceTier.JUDICIAL_PRECEDENT, 0.9)
        c2 = self._candidate("b", SourceTier.JUDICIAL_PRECEDENT, 0.7)
        result = self.resolver.resolve([c1, c2])
        assert result.winner.entity_id == "a"
        assert "confidence" in result.resolution_reason

    def test_equal_tie_halts(self) -> None:
        c1 = self._candidate("a", SourceTier.REGULATORY, 0.5)
        c2 = self._candidate("b", SourceTier.REGULATORY, 0.5)
        with pytest.raises(GovernanceViolationError) as exc_info:
            self.resolver.resolve([c1, c2])
        assert exc_info.value.violation.category == ViolationCategory.DETERMINISM_FAILURE
        assert "Unresolvable" in exc_info.value.violation.message

    def test_single_candidate_rejected(self) -> None:
        c1 = self._candidate("a", SourceTier.CONSTITUTIONAL, 1.0)
        with pytest.raises(GovernanceViolationError):
            self.resolver.resolve([c1])

    def test_empty_candidates_rejected(self) -> None:
        with pytest.raises(GovernanceViolationError):
            self.resolver.resolve([])

    def test_three_way_conflict(self) -> None:
        c1 = self._candidate("a", SourceTier.USER_INPUT, 0.9)
        c2 = self._candidate("b", SourceTier.REGULATORY, 0.5)
        c3 = self._candidate("c", SourceTier.CONSTITUTIONAL, 0.3)
        result = self.resolver.resolve([c1, c2, c3])
        assert result.winner.entity_id == "c"  # Highest tier priority
        assert len(result.losers) == 2

    def test_resolve_entity_merge(self) -> None:
        values = [
            ("value_a", SourceTier.USER_INPUT, 0.9, "user"),
            ("value_b", SourceTier.CONSTITUTIONAL, 0.5, "law"),
        ]
        value, reason = self.resolver.resolve_entity_merge("e1", values)
        assert value == "value_b"

    def test_candidate_invalid_confidence(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            ConflictCandidate(
                entity_id="x", value="v", tier=SourceTier.CONSTITUTIONAL,
                confidence=1.5, source="test", metadata={},
            )

    def test_candidate_empty_id(self) -> None:
        with pytest.raises(ValueError, match="entity_id"):
            ConflictCandidate(
                entity_id="", value="v", tier=SourceTier.CONSTITUTIONAL,
                confidence=0.5, source="test", metadata={},
            )


# ============================================================================
# VALIDATOR PIPELINE TESTS
# ============================================================================


class TestValidatorPipeline:
    """Tests for the unified validator pipeline."""

    def setup_method(self) -> None:
        self.pipeline = ValidatorPipeline()

    def _valid_node(self) -> Dict[str, Any]:
        return {
            "id": "n1",
            "name": "Test Node",
            "provenance": {
                "source": "test",
                "timestamp": "2026-01-01T00:00:00Z",
                "correlation_id": "c-1",
                "author": "tester",
            },
        }

    def test_valid_node_passes(self) -> None:
        result = self.pipeline.validate_node_write(self._valid_node(), "c-1")
        assert result.passed is True
        assert len(result.violations) == 0
        assert result.pipeline_hash  # Non-empty

    def test_node_without_provenance_fails(self) -> None:
        node = {"id": "n1", "name": "No Provenance"}
        with pytest.raises(GovernanceViolationError):
            self.pipeline.validate_node_write(node)

    def test_node_without_id_fails(self) -> None:
        node = {
            "name": "No ID",
            "provenance": {
                "source": "test",
                "timestamp": "t",
                "correlation_id": "c",
                "author": "a",
            },
        }
        with pytest.raises(GovernanceViolationError):
            self.pipeline.validate_node_write(node)

    def test_valid_relationship_passes(self) -> None:
        rel_data = {
            "provenance": {
                "source": "test",
                "timestamp": "t",
                "correlation_id": "c",
                "author": "a",
            },
        }
        result = self.pipeline.validate_relationship_write(
            "Case", "CITES", "Law", rel_data, "c-1"
        )
        assert result.passed is True

    def test_invalid_ontology_relationship_fails(self) -> None:
        rel_data = {
            "provenance": {
                "source": "test",
                "timestamp": "t",
                "correlation_id": "c",
                "author": "a",
            },
        }
        with pytest.raises(GovernanceViolationError) as exc_info:
            self.pipeline.validate_relationship_write(
                "Law", "CONTAINS", "Entity", rel_data
            )
        assert exc_info.value.violation.category == ViolationCategory.ONTOLOGY_VIOLATION

    def test_relationship_without_provenance_fails(self) -> None:
        with pytest.raises(GovernanceViolationError):
            self.pipeline.validate_relationship_write(
                "Case", "CITES", "Law", {}, "c-1"
            )

    def test_custom_gate_executed(self) -> None:
        called = {"count": 0}

        def custom_gate(data: Dict[str, Any], cid: str | None) -> None:
            called["count"] += 1

        self.pipeline.add_gate("custom", custom_gate)
        self.pipeline.validate_node_write(self._valid_node())
        assert called["count"] == 1

    def test_custom_gate_failure_propagates(self) -> None:
        def failing_gate(data: Dict[str, Any], cid: str | None) -> None:
            raise GovernanceViolationError(
                GovernanceViolation(
                    category=ViolationCategory.SCHEMA_VIOLATION,
                    severity=ViolationSeverity.CRITICAL,
                    message="custom fail",
                    details={},
                    source="custom_gate",
                )
            )

        self.pipeline.add_gate("will_fail", failing_gate)
        with pytest.raises(GovernanceViolationError):
            self.pipeline.validate_node_write(self._valid_node())

    def test_empty_gate_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            self.pipeline.add_gate("", lambda d, c: None)

    def test_pipeline_result_is_frozen(self) -> None:
        result = self.pipeline.validate_node_write(self._valid_node())
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]

    def test_pipeline_deterministic_hash(self) -> None:
        node = self._valid_node()
        r1 = self.pipeline.validate_node_write(node)
        r2 = self.pipeline.validate_node_write(node)
        assert r1.pipeline_hash == r2.pipeline_hash


# ============================================================================
# INTEGRATION: FULL PIPELINE FLOW
# ============================================================================


class TestGovernanceIntegration:
    """Integration tests for the full governance kernel."""

    def test_full_node_write_flow(self) -> None:
        """Complete node write through all governance gates."""
        pipeline = ValidatorPipeline()
        node = {
            "id": "law_123",
            "type": "Law",
            "name": "Civil Code Article 1",
            "provenance": ProvenanceMetadata.create(
                source="document_ingestion",
                correlation_id="req-001",
                author="ingestion_pipeline",
                document_id="doc-456",
            ).to_dict(),
        }
        result = pipeline.validate_node_write(node, "req-001")
        assert result.passed is True

    def test_full_relationship_write_flow(self) -> None:
        """Complete relationship write through all governance gates."""
        pipeline = ValidatorPipeline()
        rel = {
            "weight": 0.95,
            "provenance": ProvenanceMetadata.create(
                source="extraction",
                correlation_id="req-002",
                author="relation_extractor",
            ).to_dict(),
        }
        result = pipeline.validate_relationship_write(
            "Case", "CITES", "Law", rel, "req-002"
        )
        assert result.passed is True

    def test_governance_violation_error_is_exception(self) -> None:
        """GovernanceViolationError must be a proper exception."""
        v = GovernanceViolation(
            category=ViolationCategory.MISSING_PROVENANCE,
            severity=ViolationSeverity.CRITICAL,
            message="test",
            details={},
        )
        err = GovernanceViolationError(v)
        assert isinstance(err, Exception)
        assert err.violation.category == ViolationCategory.MISSING_PROVENANCE


# ============================================================================
# ADDITIONAL COVERAGE TESTS
# ============================================================================


class TestCoverageGaps:
    """Tests specifically targeting uncovered lines for 100% coverage."""

    def test_policy_registry_get_all(self) -> None:
        p1 = GovernancePolicy(name="a", description="a")
        p2 = GovernancePolicy(name="b", description="b")
        reg = PolicyRegistry([p1, p2])
        all_policies = reg.get_all()
        assert len(all_policies) == 2
        assert isinstance(all_policies, tuple)

    def test_load_redlines_policies_file_not_found(self) -> None:
        from pathlib import Path
        with pytest.raises(FileNotFoundError):
            load_redlines_policies(Path("/nonexistent/RedLines.yaml"))

    def test_provenance_metadata_empty_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp"):
            ProvenanceMetadata(
                source="s", timestamp="", correlation_id="c", author="a"
            )

    def test_provenance_metadata_empty_author_rejected(self) -> None:
        with pytest.raises(ValueError, match="author"):
            ProvenanceMetadata(
                source="s", timestamp="t", correlation_id="c", author=""
            )

    def test_provenance_metadata_to_dict_with_pipeline_version(self) -> None:
        m = ProvenanceMetadata(
            source="s", timestamp="t", correlation_id="c", author="a",
            pipeline_version="1.0",
        )
        d = m.to_dict()
        assert d["pipeline_version"] == "1.0"

    def test_provenance_metadata_to_dict_without_optionals(self) -> None:
        m = ProvenanceMetadata(
            source="s", timestamp="t", correlation_id="c", author="a",
        )
        d = m.to_dict()
        assert "document_id" not in d
        assert "pipeline_version" not in d

    def test_ontology_valid_source_invalid_target(self) -> None:
        """Source type and rel type are known, but target is wrong."""
        enforcer = OntologyEnforcer()
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_relationship("Case", "CITES", "Topic")
        # Should hit the "does not match any ontology rule" branch
        assert "ONTOLOGY_VIOLATION" in str(exc_info.value)

    def test_ontology_invalid_relationship_for_known_source(self) -> None:
        """Source type is known but relationship type is not valid for it."""
        enforcer = OntologyEnforcer()
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_relationship("Law", "DESTROYS", "Law")

    def test_ontology_rule_count(self) -> None:
        enforcer = OntologyEnforcer()
        assert enforcer.rule_count > 0

    def test_ontology_custom_rule_count(self) -> None:
        rules = (OntologyRule("A", "LINKS", "B"),)
        enforcer = OntologyEnforcer(rules=rules)
        assert enforcer.rule_count == 1

    def test_pipeline_relationship_hash_computed(self) -> None:
        """Ensures _compute_hash is called for relationship writes."""
        pipeline = ValidatorPipeline()
        rel_data: Dict[str, Any] = {
            "provenance": {
                "source": "test", "timestamp": "t",
                "correlation_id": "c", "author": "a",
            },
        }
        result = pipeline.validate_relationship_write(
            "Case", "CITES", "Law", rel_data, "c-1"
        )
        assert result.pipeline_hash  # Non-empty hash

    def test_pipeline_relationship_custom_gate(self) -> None:
        """Custom gates also run on relationship writes."""
        pipeline = ValidatorPipeline()
        called = {"count": 0}

        def gate(data: Dict[str, Any], cid: str | None) -> None:
            called["count"] += 1

        pipeline.add_gate("rel_gate", gate)
        rel_data: Dict[str, Any] = {
            "provenance": {
                "source": "test", "timestamp": "t",
                "correlation_id": "c", "author": "a",
            },
        }
        pipeline.validate_relationship_write(
            "Case", "CITES", "Law", rel_data, "c-1"
        )
        assert called["count"] == 1

    def test_provenance_validate_with_broken_object(self) -> None:
        """Test validate_provenance with an object that has empty fields.
        
        ProvenanceMetadata.__post_init__ prevents creating one normally,
        so we construct one bypassing __post_init__ via object.__new__.
        """
        tracker = ProvenanceTracker()
        # Create a broken ProvenanceMetadata bypassing __post_init__
        broken = object.__new__(ProvenanceMetadata)
        object.__setattr__(broken, "source", "test")
        object.__setattr__(broken, "timestamp", "t")
        object.__setattr__(broken, "correlation_id", "")  # Empty!
        object.__setattr__(broken, "author", "a")
        object.__setattr__(broken, "document_id", None)
        object.__setattr__(broken, "pipeline_version", None)

        with pytest.raises(GovernanceViolationError) as exc_info:
            tracker.validate_provenance(
                provenance=broken, entity_type="node", entity_id="n1"
            )
        assert "incomplete provenance" in exc_info.value.violation.message
