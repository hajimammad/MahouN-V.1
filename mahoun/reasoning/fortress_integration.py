"""
MAHOUN Fortress Integration for Unified Reasoning Service
==========================================================

Classification: MISSION-CRITICAL / GOVERNANCE-ENFORCEMENT
Purpose: Integrate FortressValidator with UnifiedReasoningService

This module provides a wrapper around UnifiedReasoningService that
automatically validates all responses through FortressValidator before
returning them to callers.

Usage:
    from mahoun.reasoning.fortress_integration import create_fortress_protected_service
    
    # Wrap existing service
    protected_service = create_fortress_protected_service(reasoning_service)
    
    # All responses are now validated
    response = await protected_service.reason(request)

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from mahoun.core.fortress_validator import (
    ExecutionMode,
    FortressValidator,
    ReasoningResponse,
    SecurityBreachException,
    ValidationResult,
)
from mahoun.core.logging_config import get_logger

log = get_logger(__name__)


# ============================================================================
# FORTRESS-PROTECTED REASONING SERVICE
# ============================================================================


class FortressProtectedReasoningService:
    """
    Wrapper around UnifiedReasoningService with automatic FortressValidator enforcement.
    
    This class intercepts ALL responses from the underlying reasoning service
    and validates them through FortressValidator before returning to callers.
    
    Features:
    - Automatic validation of all reasoning responses
    - SecurityBreachException on RedLine violations
    - Forensic audit trail generation
    - Statistics tracking
    - Transparent pass-through for valid responses
    
    Example:
        service = FortressProtectedReasoningService(
            reasoning_service=unified_service,
            strict_mode=True
        )
        
        response = await service.reason(request)  # Auto-validated
    """
    
    def __init__(
        self,
        reasoning_service: Any,
        validator: Optional[FortressValidator] = None,
        strict_mode: bool = True,
        execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL
    ):
        """
        Initialize Fortress-protected reasoning service.
        
        Args:
            reasoning_service: UnifiedReasoningService instance to wrap
            validator: Optional FortressValidator instance (creates new if None)
            strict_mode: If True, raise exceptions on violations
            execution_mode: Current execution mode
        """
        self.reasoning_service = reasoning_service
        self.strict_mode = strict_mode
        self.execution_mode = execution_mode
        
        # Create or use provided validator
        self.validator = validator or FortressValidator(
            execution_mode=execution_mode,
            strict_mode=strict_mode
        )
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "validated_responses": 0,
            "blocked_responses": 0,
            "validation_failures": 0
        }
        
        log.info(
            f"FortressProtectedReasoningService initialized: "
            f"strict={strict_mode}, mode={execution_mode.value}"
        )
    
    async def reason(
        self,
        request: Any,
        correlation_id: Optional[str] = None
    ) -> ReasoningResponse:
        """
        Execute reasoning with automatic fortress validation.
        
        This method:
        1. Calls underlying reasoning service
        2. Validates response through FortressValidator
        3. Returns validated response or raises SecurityBreachException
        
        Args:
            request: ReasoningRequest to process
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Validated ReasoningResponse
            
        Raises:
            SecurityBreachException: On critical RedLine violations
        """
        self.stats["total_requests"] += 1
        
        # Generate correlation_id if not provided
        if correlation_id is None and hasattr(request, 'correlation_id'):
            correlation_id = request.correlation_id
        
        try:
            # Execute reasoning
            log.debug(f"[{correlation_id}] Executing reasoning request")
            response = await self.reasoning_service.reason(request)
            
            # Validate response through Fortress
            log.debug(f"[{correlation_id}] Validating response through Fortress")
            validation_result = await self.validator.validate(
                response=response,
                correlation_id=correlation_id
            )
            
            self.stats["validated_responses"] += 1
            
            if not validation_result.passed:
                self.stats["blocked_responses"] += 1
                log.error(
                    f"[{correlation_id}] Response BLOCKED by Fortress: "
                    f"{len(validation_result.violations)} violations"
                )
            else:
                log.info(
                    f"[{correlation_id}] Response VALIDATED by Fortress "
                    f"({validation_result.execution_time_ms:.2f}ms)"
                )
            
            return response
            
        except SecurityBreachException:
            # Re-raise security breaches
            self.stats["blocked_responses"] += 1
            raise
            
        except Exception as e:
            self.stats["validation_failures"] += 1
            log.error(f"[{correlation_id}] Validation failed with exception: {e}")
            raise
    
    async def reason_batch(
        self,
        requests: list[Any],
        correlation_id_prefix: Optional[str] = None
    ) -> list[ReasoningResponse]:
        """
        Execute batch reasoning with validation.
        
        Args:
            requests: List of ReasoningRequest objects
            correlation_id_prefix: Optional prefix for correlation IDs
            
        Returns:
            List of validated ReasoningResponse objects
        """
        tasks = []
        for i, request in enumerate(requests):
            corr_id = f"{correlation_id_prefix}-{i}" if correlation_id_prefix else None
            tasks.append(self.reason(request, correlation_id=corr_id))
        
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        validator_stats = self.validator.get_stats()
        
        return {
            "service": self.stats.copy(),
            "validator": validator_stats,
            "combined": {
                "total_requests": self.stats["total_requests"],
                "validation_pass_rate": (
                    validator_stats["passed"] / validator_stats["total_validations"]
                    if validator_stats["total_validations"] > 0 else 0.0
                ),
                "block_rate": (
                    self.stats["blocked_responses"] / self.stats["total_requests"]
                    if self.stats["total_requests"] > 0 else 0.0
                )
            }
        }
    
    def get_audit_trail(self, limit: int = 100) -> list[Dict[str, Any]]:
        """Get recent audit trail from validator"""
        return self.validator.get_audit_trail(limit=limit)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on protected service"""
        try:
            # Check underlying service
            service_healthy = hasattr(self.reasoning_service, 'health_check')
            if service_healthy:
                service_health = await self.reasoning_service.health_check()
            else:
                service_health = {"status": "unknown"}
            
            # Check validator
            validator_healthy = self.validator is not None
            
            return {
                "status": "healthy" if (service_healthy and validator_healthy) else "degraded",
                "fortress_validator": {
                    "active": validator_healthy,
                    "strict_mode": self.strict_mode,
                    "execution_mode": self.execution_mode.value,
                    "total_validations": self.validator.stats["total_validations"]
                },
                "reasoning_service": service_health,
                "statistics": self.get_stats()
            }
            
        except Exception as e:
            log.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_fortress_protected_service(
    reasoning_service: Any,
    strict_mode: bool = True,
    execution_mode: ExecutionMode = ExecutionMode.DESKTOP_MINIMAL
) -> FortressProtectedReasoningService:
    """
    Create a Fortress-protected reasoning service.
    
    This is the recommended way to wrap an existing UnifiedReasoningService
    with automatic FortressValidator enforcement.
    
    Args:
        reasoning_service: UnifiedReasoningService instance to protect
        strict_mode: If True, raise exceptions on violations
        execution_mode: Current execution mode
        
    Returns:
        FortressProtectedReasoningService instance
        
    Example:
        from mahoun.reasoning.unified_reasoning_service import UnifiedReasoningService
        from mahoun.reasoning.fortress_integration import create_fortress_protected_service
        
        # Create base service
        base_service = UnifiedReasoningService()
        
        # Wrap with Fortress protection
        protected_service = create_fortress_protected_service(
            base_service,
            strict_mode=True
        )
        
        # Use protected service (all responses auto-validated)
        response = await protected_service.reason(request)
    """
    return FortressProtectedReasoningService(
        reasoning_service=reasoning_service,
        strict_mode=strict_mode,
        execution_mode=execution_mode
    )


async def validate_existing_response(
    response: ReasoningResponse,
    correlation_id: Optional[str] = None,
    strict_mode: bool = True
) -> ValidationResult:
    """
    Validate an existing reasoning response.
    
    Useful for validating responses from external sources or
    for retroactive validation of cached responses.
    
    Args:
        response: ReasoningResponse to validate
        correlation_id: Optional correlation ID
        strict_mode: If True, raise exceptions on violations
        
    Returns:
        ValidationResult
        
    Raises:
        SecurityBreachException: On critical violations (if strict_mode=True)
    """
    validator = FortressValidator(strict_mode=strict_mode)
    return await validator.validate(response, correlation_id=correlation_id)


# ============================================================================
# DECORATOR FOR AUTOMATIC VALIDATION
# ============================================================================


def fortress_validated(strict_mode: bool = True):
    """
    Decorator for automatic fortress validation of reasoning methods.
    
    Usage:
        class MyReasoningService:
            @fortress_validated(strict_mode=True)
            async def reason(self, request):
                # ... reasoning logic ...
                return response
    
    Args:
        strict_mode: If True, raise exceptions on violations
        
    Returns:
        Decorated function with automatic validation
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Execute original function
            response = await func(*args, **kwargs)
            
            # Extract correlation_id if available
            correlation_id = kwargs.get('correlation_id')
            if correlation_id is None and len(args) > 1:
                request = args[1]
                if hasattr(request, 'correlation_id'):
                    correlation_id = request.correlation_id
            
            # Validate response
            validator = FortressValidator(strict_mode=strict_mode)
            await validator.validate(response, correlation_id=correlation_id)
            
            return response
        
        return wrapper
    return decorator


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

log.info("FortressIntegration module loaded: AUTOMATIC VALIDATION ENABLED")
