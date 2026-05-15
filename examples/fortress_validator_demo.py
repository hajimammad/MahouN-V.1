#!/usr/bin/env python3
"""
MAHOUN Fortress Validator Demo
===============================

Demonstrates FortressValidator usage and enforcement capabilities.

This script shows:
1. Valid response validation (passes)
2. Missing proof_tree (fails)
3. Low agreement_score (fails)
4. Missing evidence (fails)
5. Statistics and audit trail

Run:
    python examples/fortress_validator_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mahoun.core.fortress_validator import (
    ExecutionMode,
    FortressValidator,
    ReasoningResponse,
    SecurityBreachException,
)


# ============================================================================
# MOCK PROOF TREE
# ============================================================================


class MockProofTree:
    """Mock proof tree for demonstration"""
    
    def __init__(self, depth: int = 5):
        self.depth = depth
    
    def get_proof_depth(self) -> int:
        return self.depth
    
    def __repr__(self) -> str:
        return f"<ProofTree depth={self.depth}>"


# ============================================================================
# DEMO SCENARIOS
# ============================================================================


async def demo_valid_response():
    """Demo 1: Valid response that passes all checks"""
    print("\n" + "="*80)
    print("DEMO 1: Valid Response (Should PASS)")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=True
    )
    
    response = ReasoningResponse(
        success=True,
        result="Tax exemption applies under Article 143 due to constitutional override",
        confidence=0.92,
        reasoning_mode="HYBRID",
        execution_time_ms=245.5,
        proof_tree=MockProofTree(depth=5),
        explanation="Based on constitutional hierarchy, Article 143 overrides Article 505...",
        derived_facts=[
            "tax_exempt(entity_123)",
            "article_143_applies(entity_123)",
            "constitutional_override(article_143, article_505)",
            "precedent_supports(case_2019_45)",
            "burden_of_proof_met(entity_123)"
        ],
        metadata={
            "agreement_score": 0.89,  # Above 0.85 threshold ✓
            "symbolic_facts": 15,
            "neural_facts": 12,
            "contradictions": []
        }
    )
    
    try:
        result = await validator.validate(response, correlation_id="demo-001")
        
        print(f"\n✅ VALIDATION PASSED")
        print(f"   Correlation ID: {result.correlation_id}")
        print(f"   Execution Time: {result.execution_time_ms:.2f}ms")
        print(f"   Forensic Hash: {result.forensic_hash}")
        print(f"   Violations: {len(result.violations)}")
        print(f"   Warnings: {len(result.warnings)}")
        
    except SecurityBreachException as e:
        print(f"\n❌ UNEXPECTED FAILURE: {e}")


async def demo_missing_proof_tree():
    """Demo 2: Response missing proof_tree (Should FAIL)"""
    print("\n" + "="*80)
    print("DEMO 2: Missing Proof Tree (Should FAIL)")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=True
    )
    
    response = ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.85,
        reasoning_mode="HYBRID",
        execution_time_ms=150.0,
        proof_tree=None,  # ❌ VIOLATION: Missing proof_tree
        derived_facts=["tax_exempt(entity_123)"],
        metadata={"agreement_score": 0.90}
    )
    
    try:
        result = await validator.validate(response, correlation_id="demo-002")
        print(f"\n⚠️  UNEXPECTED PASS (should have failed)")
        
    except SecurityBreachException as e:
        print(f"\n✅ CORRECTLY BLOCKED")
        print(f"   Violation Type: {e.violation_type.value}")
        print(f"   Severity: {e.severity.value}")
        print(f"   Message: {e.message}")
        print(f"   Correlation ID: {e.correlation_id}")


async def demo_low_agreement_score():
    """Demo 3: Low agreement_score (Should FAIL)"""
    print("\n" + "="*80)
    print("DEMO 3: Low Agreement Score (Should FAIL)")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=True
    )
    
    response = ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.80,
        reasoning_mode="HYBRID",
        execution_time_ms=200.0,
        proof_tree=MockProofTree(depth=3),
        derived_facts=["tax_exempt(entity_123)"],
        metadata={"agreement_score": 0.65}  # ❌ VIOLATION: Below 0.85 threshold
    )
    
    try:
        result = await validator.validate(response, correlation_id="demo-003")
        print(f"\n⚠️  UNEXPECTED PASS (should have failed)")
        
    except SecurityBreachException as e:
        print(f"\n✅ CORRECTLY BLOCKED")
        print(f"   Violation Type: {e.violation_type.value}")
        print(f"   Severity: {e.severity.value}")
        print(f"   Agreement Score: 0.65 (threshold: 0.85)")
        print(f"   Gap: {0.85 - 0.65:.2f}")


async def demo_missing_evidence():
    """Demo 4: Missing evidence linkage (Should FAIL)"""
    print("\n" + "="*80)
    print("DEMO 4: Missing Evidence Linkage (Should FAIL)")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=False  # Non-strict to see violation details
    )
    
    response = ReasoningResponse(
        success=True,
        result="Tax exemption applies",
        confidence=0.88,
        reasoning_mode="HYBRID",
        execution_time_ms=180.0,
        proof_tree=MockProofTree(depth=2),
        derived_facts=[],  # ❌ VIOLATION: No evidence
        metadata={"agreement_score": 0.92}
    )
    
    result = await validator.validate(response, correlation_id="demo-004")
    
    if result.passed:
        print(f"\n⚠️  UNEXPECTED PASS")
    else:
        print(f"\n✅ CORRECTLY FLAGGED")
        print(f"   Violations: {len(result.violations)}")
        for v in result.violations:
            print(f"   - {v['type']}: {v['message']}")


async def demo_statistics():
    """Demo 5: Statistics and audit trail"""
    print("\n" + "="*80)
    print("DEMO 5: Statistics and Audit Trail")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=False  # Non-strict to accumulate stats
    )
    
    # Valid response
    valid_response = ReasoningResponse(
        success=True,
        result="Valid result",
        confidence=0.95,
        reasoning_mode="SYMBOLIC",
        execution_time_ms=120.0,
        proof_tree=MockProofTree(depth=5),
        derived_facts=["fact1", "fact2"],
        metadata={}
    )
    
    # Invalid response
    invalid_response = ReasoningResponse(
        success=True,
        result="Invalid result",
        confidence=0.70,
        reasoning_mode="HYBRID",
        execution_time_ms=100.0,
        proof_tree=None,
        derived_facts=[],
        metadata={"agreement_score": 0.50}
    )
    
    # Run validations
    await validator.validate(valid_response, correlation_id="demo-005-valid")
    await validator.validate(invalid_response, correlation_id="demo-005-invalid")
    
    # Get statistics
    stats = validator.get_stats()
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total Validations: {stats['total_validations']}")
    print(f"   Passed: {stats['passed']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Average Time: {stats['average_validation_time_ms']:.2f}ms")
    print(f"\n   Violations by Type:")
    for vtype, count in stats['violations_by_type'].items():
        print(f"   - {vtype}: {count}")
    
    # Get audit trail
    audit_trail = validator.get_audit_trail(limit=10)
    
    print(f"\n📋 AUDIT TRAIL (last {len(audit_trail)} entries):")
    for entry in audit_trail:
        print(f"   - {entry['correlation_id']}: "
              f"{entry['checks_performed']} checks, "
              f"{entry['violations_count']} violations")


async def demo_multiple_violations():
    """Demo 6: Response with multiple violations"""
    print("\n" + "="*80)
    print("DEMO 6: Multiple Violations")
    print("="*80)
    
    validator = FortressValidator(
        execution_mode=ExecutionMode.DESKTOP_MINIMAL,
        strict_mode=False  # Non-strict to see all violations
    )
    
    response = ReasoningResponse(
        success=True,
        result="Result with multiple issues",
        confidence=0.70,
        reasoning_mode="HYBRID",
        execution_time_ms=100.0,
        proof_tree=None,  # ❌ VIOLATION 1: Missing proof
        derived_facts=[],  # ❌ VIOLATION 2: No evidence
        metadata={"agreement_score": 0.50}  # ❌ VIOLATION 3: Low agreement
    )
    
    result = await validator.validate(response, correlation_id="demo-006")
    
    print(f"\n🚨 MULTIPLE VIOLATIONS DETECTED:")
    print(f"   Total: {len(result.violations)}")
    print(f"   Passed: {result.passed}")
    print(f"\n   Details:")
    for i, v in enumerate(result.violations, 1):
        print(f"   {i}. [{v['severity']}] {v['type']}")
        print(f"      {v['message']}")


# ============================================================================
# MAIN DEMO
# ============================================================================


async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("MAHOUN FORTRESS VALIDATOR DEMONSTRATION")
    print("="*80)
    print("\nThis demo shows FortressValidator enforcing RedLines.yaml governance.")
    print("Key threshold: agreement_score >= 0.85")
    
    try:
        await demo_valid_response()
        await demo_missing_proof_tree()
        await demo_low_agreement_score()
        await demo_missing_evidence()
        await demo_statistics()
        await demo_multiple_violations()
        
        print("\n" + "="*80)
        print("✅ DEMO COMPLETE")
        print("="*80)
        print("\nKey Takeaways:")
        print("1. FortressValidator enforces RedLines.yaml governance")
        print("2. agreement_score threshold is 0.85 (raised from 0.30)")
        print("3. proof_tree is mandatory for all responses")
        print("4. Evidence linkage (derived_facts) is required")
        print("5. SecurityBreachException raised on critical violations")
        print("6. Complete audit trail maintained for forensics")
        
    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
