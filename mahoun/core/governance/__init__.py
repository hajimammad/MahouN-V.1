"""
MAHOUN Governance Kernel
========================

Classification: CRITICAL PLATFORM GOVERNANCE / NON-BYPASSABLE
Purpose: Unified enforcement model for Runtime and Lifecycle governance.

This package is the single governance kernel for MAHOUN. All governance
enforcement — runtime and CI/CD — flows through this module.

Layers:
    Runtime Governance:
        ValidatorPipeline, ProvenanceTracker, OntologyEnforcer,
        DeterministicResolver

    Lifecycle Governance (CI/CD):
        ForbiddenPatternScanner, ArchitectureComplianceChecker,
        SchemaDriftDetector, CoverageEnforcer

Shared:
    GovernanceViolation, GovernancePolicy, ViolationSeverity

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
)
from mahoun.core.governance.policies import (
    GovernancePolicy,
    PolicyRegistry,
    load_redlines_policies,
)
from mahoun.core.governance.validator_pipeline import ValidatorPipeline
from mahoun.core.governance.provenance_tracker import (
    ProvenanceMetadata,
    ProvenanceTracker,
)
from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
from mahoun.core.governance.deterministic_resolver import DeterministicResolver

__all__ = [
    # Violations
    "GovernanceViolation",
    "GovernanceViolationError",
    "ViolationCategory",
    # Policies
    "GovernancePolicy",
    "PolicyRegistry",
    "load_redlines_policies",
    # Runtime Governance
    "ValidatorPipeline",
    "ProvenanceTracker",
    "ProvenanceMetadata",
    "OntologyEnforcer",
    "DeterministicResolver",
]
