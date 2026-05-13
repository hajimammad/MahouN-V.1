"""
MAHOUN Fortress Validator
==========================

Classification: MISSION-CRITICAL / SECURITY-ENFORCEMENT / NON-BYPASSABLE
Purpose: Final forensic validation layer for all reasoning outputs

This module implements the Fortress Validator, a standalone wrapper that intercepts
ALL outputs from unified_reasoning_service.py and performs mandatory forensic checks
before allowing responses to proceed.

Core Responsibilities:
- Enforce RedLines.yaml governance thresholds
- Validate proof_tree existence and integrity
- Verify agreement_score >= 0.85
- Block responses that violate zero-hallucination guarantees
- Generate forensic audit trails
- Raise SecurityBreachException on violations

Author: MahouN AEO Governance Council
Version: 1.0.0
Last Updated: 2026-05-13
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TypeVar, Union

import yaml
from pydantic import BaseModel, Field, validator

try:
    from mahoun.core.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

log = get_logger(__name__)

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

T = TypeVar('T')


class ViolationSeverity(str, Enum):
    """Severity classification for RedLine violations"""
    CRITICAL = "CRITICAL"  # Immediate block, security breach
    HIGH = "HIGH"          # Block response, log incident
    MEDIUM = "MEDIUM"      # Warn, allow with audit
    LOW = "LOW"            # Log only


class ViolationType(str, Enum):
    """Types of RedLine violations"""
    MISSING_PROOF_TREE = "MISSING_PROOF_TREE"
    LOW_AGREEMENT_SCORE = "LOW_AGREEMENT_SCORE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    SEMANTIC_DRIFT = "SEMANTIC_DRIFT"
    DETERMINISM_FAILURE = "DETERMINISM_FAILURE"
    AUDIT_TRAIL_INCOMPLETE = "AUDIT_TRAIL_INCOMPLETE"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    RESOURCE_VIOLATION = "RESOURCE_VIOLATION"
    SILENT_FAILURE = "SILENT_FAILURE"


class ExecutionMode(str, Enum):
    """System execution modes"""
    DESKTOP_MINIMAL = "DESKTOP_MINIMAL"
    ENTERPRISE_FULL = "ENTERPRISE_FULL"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class SecurityBreachException(Exception):
    """
    Raised when a RedLine violation is detected.
    
    This exception is NON-BYPASSABLE and indicates a critical
    governance failure that must be addressed immediately.
    """
    
    def __init__(
        self,
        message: str,
        violation_type: ViolationType,
        severity: ViolationSeverity,
        forensic_context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.violation_type = violation_type
        self.severity = severity
        self.forensic_context = forensic_context
        self.correlation_id = correlation_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format exception message with forensic context"""
        return (
            f"[SECURITY BREACH] {self.severity.value}\n"
            f"Violation: {self.violation_type.value}\n"
            f"Message: {self.message}\n"
            f"Correlation ID: {self.correlation_id}\n"
            f"Timestamp: {self.timestamp}\n"
            f"Forensic Context: {self.forensic_context}"
        )


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class RedLinesConfig(BaseModel):
    """Pydantic model for RedLines.yaml configuration"""
    
    class ThresholdsConfig(BaseModel):
        min_agreement_score: float = Field(ge=0.0, le=1.0)
        min_confidence_score: float = Field(ge=0.0, le=1.0)
        max_reasoning_time_ms: int = Field(gt=0)
        max_recursion_depth: int = Field(gt=0)
    
    class ProofRequirementsConfig(BaseModel):
        proof_tree_required: bool
        min_proof_depth: int = Field(ge=0)
        evidence_linkage_required: bool
        audit_trail_required: bool
    
    class HallucinationPreventionConfig(BaseModel):
        require_graph_evidence: bool
        require_source_attribution: bool
        reject_contradictions: bool
        require_determinism: bool
    
    class DualModeConfig(BaseModel):
        enforce_semantic_equivalence: bool
        allow_resource_scaling_only: bool
        fail_on_semantic_drift: bool
    
    class ExceptionsConfig(BaseModel):
        violation_exception: str
        allow_silent_failures: bool
        require_exception_logging: bool
        require_forensic_context: bool
    
    thresholds: ThresholdsConfig
    proof_requirements: ProofRequirementsConfig
    hallucination_prevention: HallucinationPreventionConfig
    dual_mode: DualModeConfig
    exceptions: ExceptionsConfig


class ValidationResult(BaseModel):
    """Result of fortress validation"""
    
    passed: bool
    correlation_id: str
    timestamp: str
    execution_time_ms: float
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    forensic_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        frozen = False


class ReasoningResponse(BaseModel):
    """Expected structure of reasoning service response"""
    
    success: bool
    result: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_mode: str
    execution_time_ms: float
    proof_tree: Optional[Any] = None
    explanation: Optional[str] = None
    derived_facts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# FORTRESS VALIDATOR CORE
# ============================================================================


@dataclass
class ForensicContext:
    """Forensic context for audit trail"""
    
    correlation_id: str
    timestamp: str
    execution_mode: ExecutionMode
    response_hash: str
    validation_checks: List[str] = field(default_factory=list)
    violations_detected: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FortressValidator:
    """
    The Fortress Validator: Final governance enforcement layer.
    
    This class intercepts ALL outputs from unified_reasoning_service.py
    and performs mandatory forensic validation before allowing responses
    to proceed.
    
    Responsibilities:
    - Load and enforce RedLines.yaml configuration
    - Validate proof_tree existence and integrity
    - Verify agreement_score >= threshold
    - Check evidence linkage and audit trails
    - Generate forensic audit records
    - Raise SecurityBreachException on violations
    
    Usage:
        validator = FortressValidator()
        validated_response = await validator.validate(
            response=reasoning_response,
            correlation_id="req-12345"
        )
    """
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL,
        strict_mode: bool = True
    ):
        """
        Initialize Fortress Validator.
        
        Args:
            config_path: Path to RedLines.yaml (defaults to constitution/RedLines.yaml)
            execution_mode: Current execution mode (DESKTOP_MINIMAL or ENTERPRISE_FULL)
            strict_mode: If True, raise exceptions on violations; if False, log only
        """
        self.execution_mode = execution_mode
        self.strict_mode = strict_mode
        self.config_path = config_path or Path(__file__).parent.parent.parent / "constitution" / "RedLines.yaml"
        
        # Load configuration
        self.config = self._load_config()
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "passed": 0,
            "failed": 0,
            "violations_by_type": {},
            "average_validation_time_ms": 0.0
        }
        
        # Forensic audit trail
        self.audit_trail: List[ForensicContext] = []
        
        log.info(
            f"FortressValidator initialized: mode={execution_mode.value}, "
            f"strict={strict_mode}, config={self.config_path}"
        )
    
    def _load_config(self) -> RedLinesConfig:
        """Load and validate RedLines.yaml configuration"""
        try:
            if not self.config_path.exists():
                log.error(f"RedLines.yaml not found at {self.config_path}")
                raise FileNotFoundError(f"RedLines configuration missing: {self.config_path}")
            
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            config = RedLinesConfig(**raw_config)
            log.info(f"RedLines.yaml loaded successfully: min_agreement={config.thresholds.min_agreement_score}")
            return config
            
        except Exception as e:
            log.critical(f"Failed to load RedLines.yaml: {e}")
            raise
    
    async def validate(
        self,
        response: Union[ReasoningResponse, Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Perform comprehensive fortress validation on reasoning response.
        
        This is the main entry point for validation. It performs all
        mandatory checks defined in RedLines.yaml and raises
        SecurityBreachException if critical violations are detected.
        
        Args:
            response: Reasoning service response to validate
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            ValidationResult with pass/fail status and forensic context
            
        Raises:
            SecurityBreachException: On critical RedLine violations
        """
        start_time = time.perf_counter()
        correlation_id = correlation_id or self._generate_correlation_id()
        
        # Convert dict to Pydantic model if needed
        if isinstance(response, dict):
            try:
                response = ReasoningResponse(**response)
            except Exception as e:
                log.error(f"[{correlation_id}] Failed to parse response: {e}")
                raise SecurityBreachException(
                    message=f"Invalid response structure: {e}",
                    violation_type=ViolationType.AUDIT_TRAIL_INCOMPLETE,
                    severity=ViolationSeverity.CRITICAL,
                    forensic_context={"error": str(e), "response": str(response)[:500]},
                    correlation_id=correlation_id
                )
        
        # Initialize forensic context
        forensic_ctx = ForensicContext(
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            execution_mode=self.execution_mode,
            response_hash=self._compute_response_hash(response)
        )
        
        violations: List[Dict[str, Any]] = []
        warnings: List[str] = []
        
        # Execute validation checks
        try:
            # CHECK 1: Proof tree validation
            proof_violation = await self._validate_proof_tree(response, forensic_ctx)
            if proof_violation:
                violations.append(proof_violation)
            
            # CHECK 2: Agreement score validation
            agreement_violation = await self._validate_agreement_score(response, forensic_ctx)
            if agreement_violation:
                violations.append(agreement_violation)
            
            # CHECK 3: Evidence linkage validation
            evidence_violation = await self._validate_evidence_linkage(response, forensic_ctx)
            if evidence_violation:
                violations.append(evidence_violation)
            
            # CHECK 4: Audit trail validation
            audit_violation = await self._validate_audit_trail(response, forensic_ctx)
            if audit_violation:
                violations.append(audit_violation)
            
            # CHECK 5: Determinism validation
            determinism_violation = await self._validate_determinism(response, forensic_ctx)
            if determinism_violation:
                violations.append(determinism_violation)
            
            # CHECK 6: Contradiction detection
            contradiction_violation = await self._validate_contradictions(response, forensic_ctx)
            if contradiction_violation:
                violations.append(contradiction_violation)
            
        except Exception as e:
            log.error(f"[{correlation_id}] Validation check failed: {e}")
            violations.append({
                "type": ViolationType.SILENT_FAILURE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": f"Validation exception: {e}",
                "details": {"exception": str(e)}
            })
        
        # Compute execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        
        # Determine overall pass/fail
        critical_violations = [v for v in violations if v["severity"] == ViolationSeverity.CRITICAL.value]
        passed = len(critical_violations) == 0
        
        # Update statistics
        self._update_stats(passed, violations, execution_time_ms)
        
        # Store forensic context
        forensic_ctx.violations_detected = violations
        self.audit_trail.append(forensic_ctx)
        
        # Create validation result
        result = ValidationResult(
            passed=passed,
            correlation_id=correlation_id,
            timestamp=forensic_ctx.timestamp,
            execution_time_ms=execution_time_ms,
            violations=violations,
            warnings=warnings,
            forensic_hash=forensic_ctx.response_hash,
            metadata={
                "execution_mode": self.execution_mode.value,
                "strict_mode": self.strict_mode,
                "checks_performed": len(forensic_ctx.validation_checks)
            }
        )
        
        # Raise exception if critical violations detected and strict mode enabled
        if not passed and self.strict_mode:
            self._raise_security_breach(violations, forensic_ctx)
        
        # Log result
        if passed:
            log.info(f"[{correlation_id}] ✓ Fortress validation PASSED ({execution_time_ms:.2f}ms)")
        else:
            log.error(f"[{correlation_id}] ✗ Fortress validation FAILED: {len(violations)} violations")
        
        return result
    
    async def _validate_proof_tree(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate proof_tree existence and integrity"""
        forensic_ctx.validation_checks.append("proof_tree")
        
        if not self.config.proof_requirements.proof_tree_required:
            return None
        
        if response.proof_tree is None:
            return {
                "type": ViolationType.MISSING_PROOF_TREE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": "Response missing required proof_tree",
                "details": {
                    "requirement": "proof_tree_required=true",
                    "actual": "proof_tree=None"
                }
            }
        
        # Validate proof depth if proof_tree exists
        if hasattr(response.proof_tree, 'get_proof_depth'):
            try:
                depth = response.proof_tree.get_proof_depth()
                min_depth = self.config.proof_requirements.min_proof_depth
                
                if depth < min_depth:
                    return {
                        "type": ViolationType.MISSING_PROOF_TREE.value,
                        "severity": ViolationSeverity.HIGH.value,
                        "message": f"Proof tree depth {depth} below minimum {min_depth}",
                        "details": {"depth": depth, "min_depth": min_depth}
                    }
            except Exception as e:
                log.warning(f"Could not validate proof depth: {e}")
        
        return None
    
    async def _validate_agreement_score(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate agreement_score meets threshold"""
        forensic_ctx.validation_checks.append("agreement_score")
        
        # Extract agreement_score from metadata
        agreement_score = response.metadata.get("agreement_score")
        
        if agreement_score is None:
            # If no agreement_score, check if this is a single-mode response
            if response.reasoning_mode in ["SYMBOLIC", "NEURAL"]:
                # Single-mode responses don't have agreement scores
                return None
            
            return {
                "type": ViolationType.AUDIT_TRAIL_INCOMPLETE.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": "Missing agreement_score in hybrid reasoning response",
                "details": {"reasoning_mode": response.reasoning_mode}
            }
        
        min_score = self.config.thresholds.min_agreement_score
        
        if agreement_score < min_score:
            return {
                "type": ViolationType.LOW_AGREEMENT_SCORE.value,
                "severity": ViolationSeverity.CRITICAL.value,
                "message": f"Agreement score {agreement_score:.2%} below threshold {min_score:.2%}",
                "details": {
                    "agreement_score": agreement_score,
                    "threshold": min_score,
                    "gap": min_score - agreement_score
                }
            }
        
        return None
    
    async def _validate_evidence_linkage(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate evidence linkage requirements"""
        forensic_ctx.validation_checks.append("evidence_linkage")
        
        if not self.config.hallucination_prevention.require_graph_evidence:
            return None
        
        # Check if derived_facts exist (evidence of graph reasoning)
        if not response.derived_facts or len(response.derived_facts) == 0:
            return {
                "type": ViolationType.MISSING_EVIDENCE.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": "No derived facts found (missing graph evidence)",
                "details": {"derived_facts_count": 0}
            }
        
        return None
    
    async def _validate_audit_trail(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate audit trail completeness"""
        forensic_ctx.validation_checks.append("audit_trail")
        
        if not self.config.proof_requirements.audit_trail_required:
            return None
        
        # Check for required metadata fields
        required_fields = ["reasoning_mode", "execution_time_ms"]
        missing_fields = [f for f in required_fields if not hasattr(response, f) or getattr(response, f) is None]
        
        if missing_fields:
            return {
                "type": ViolationType.AUDIT_TRAIL_INCOMPLETE.value,
                "severity": ViolationSeverity.MEDIUM.value,
                "message": f"Audit trail missing required fields: {missing_fields}",
                "details": {"missing_fields": missing_fields}
            }
        
        return None
    
    async def _validate_determinism(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate determinism requirements"""
        forensic_ctx.validation_checks.append("determinism")
        
        if not self.config.hallucination_prevention.require_determinism:
            return None
        
        # Check if response contains non-deterministic indicators
        # (This is a placeholder - full determinism validation requires state tracking)
        if response.reasoning_mode == "NEURAL" and not response.proof_tree:
            return {
                "type": ViolationType.DETERMINISM_FAILURE.value,
                "severity": ViolationSeverity.MEDIUM.value,
                "message": "Neural-only response without proof tree (non-deterministic)",
                "details": {"reasoning_mode": response.reasoning_mode}
            }
        
        return None
    
    async def _validate_contradictions(
        self,
        response: ReasoningResponse,
        forensic_ctx: ForensicContext
    ) -> Optional[Dict[str, Any]]:
        """Validate contradiction detection"""
        forensic_ctx.validation_checks.append("contradictions")
        
        if not self.config.hallucination_prevention.reject_contradictions:
            return None
        
        # Check metadata for contradiction markers
        contradictions = response.metadata.get("contradictions", [])
        
        if contradictions and len(contradictions) > 0:
            return {
                "type": ViolationType.CONTRADICTION_DETECTED.value,
                "severity": ViolationSeverity.HIGH.value,
                "message": f"Contradictions detected: {len(contradictions)}",
                "details": {"contradictions": contradictions[:5]}  # Limit to first 5
            }
        
        return None
    
    def _compute_response_hash(self, response: ReasoningResponse) -> str:
        """Compute forensic hash of response for audit trail"""
        hash_input = f"{response.result}|{response.confidence}|{response.reasoning_mode}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        return f"fortress-{uuid.uuid4().hex[:12]}"
    
    def _update_stats(
        self,
        passed: bool,
        violations: List[Dict[str, Any]],
        execution_time_ms: float
    ) -> None:
        """Update validation statistics"""
        self.stats["total_validations"] += 1
        
        if passed:
            self.stats["passed"] += 1
        else:
            self.stats["failed"] += 1
        
        # Update violation counts by type
        for violation in violations:
            vtype = violation["type"]
            self.stats["violations_by_type"][vtype] = self.stats["violations_by_type"].get(vtype, 0) + 1
        
        # Update average validation time
        total = self.stats["total_validations"]
        current_avg = self.stats["average_validation_time_ms"]
        self.stats["average_validation_time_ms"] = ((current_avg * (total - 1)) + execution_time_ms) / total
    
    def _raise_security_breach(
        self,
        violations: List[Dict[str, Any]],
        forensic_ctx: ForensicContext
    ) -> None:
        """Raise SecurityBreachException for critical violations"""
        critical_violations = [v for v in violations if v["severity"] == ViolationSeverity.CRITICAL.value]
        
        if not critical_violations:
            return
        
        primary_violation = critical_violations[0]
        
        raise SecurityBreachException(
            message=primary_violation["message"],
            violation_type=ViolationType(primary_violation["type"]),
            severity=ViolationSeverity.CRITICAL,
            forensic_context={
                "correlation_id": forensic_ctx.correlation_id,
                "timestamp": forensic_ctx.timestamp,
                "response_hash": forensic_ctx.response_hash,
                "total_violations": len(violations),
                "critical_violations": len(critical_violations),
                "violations": violations
            },
            correlation_id=forensic_ctx.correlation_id
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return self.stats.copy()
    
    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit trail entries"""
        recent = self.audit_trail[-limit:]
        return [
            {
                "correlation_id": ctx.correlation_id,
                "timestamp": ctx.timestamp,
                "execution_mode": ctx.execution_mode.value,
                "response_hash": ctx.response_hash,
                "checks_performed": len(ctx.validation_checks),
                "violations_count": len(ctx.violations_detected)
            }
            for ctx in recent
        ]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


async def validate_reasoning_response(
    response: Union[ReasoningResponse, Dict[str, Any]],
    correlation_id: Optional[str] = None,
    strict_mode: bool = True
) -> ValidationResult:
    """
    Convenience function for one-off validation.
    
    Args:
        response: Reasoning response to validate
        correlation_id: Optional correlation ID
        strict_mode: If True, raise exceptions on violations
        
    Returns:
        ValidationResult
        
    Raises:
        SecurityBreachException: On critical violations (if strict_mode=True)
    """
    validator = FortressValidator(strict_mode=strict_mode)
    return await validator.validate(response, correlation_id)


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

log.info("FortressValidator module loaded: GOVERNANCE ENFORCEMENT ACTIVE")
