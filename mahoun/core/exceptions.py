"""
Mahoun Exception Hierarchy
==========================
Standardized exceptions for the entire platform.

All exceptions inherit from MahounError for consistent handling.
"""

from typing import Any, Dict, Optional


class MahounError(Exception):
    """
    Base exception for all Mahoun errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional context for debugging
    """
    
    error_code: str = "MAHOUN_ERROR"
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if error_code:
            self.error_code = error_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


# =============================================================================
# Serialization Errors
# =============================================================================

class SerializationError(MahounError):
    """Error during serialization/deserialization."""
    error_code = "SERIALIZATION_ERROR"


class UnsafeSerializationError(SerializationError):
    """Attempted to use unsafe serialization format (e.g., pickle)."""
    error_code = "UNSAFE_SERIALIZATION"


# =============================================================================
# Ledger Errors
# =============================================================================

class LedgerError(MahounError):
    """Error in evidence ledger operations."""
    error_code = "LEDGER_ERROR"


class LedgerWriteError(LedgerError):
    """Failed to write to evidence ledger."""
    error_code = "LEDGER_WRITE_ERROR"


class LedgerIntegrityError(LedgerError):
    """Hash chain integrity violation detected."""
    error_code = "LEDGER_INTEGRITY_ERROR"


# =============================================================================
# Knowledge Graph Errors
# =============================================================================

class KnowledgeGraphError(MahounError):
    """Error in knowledge graph operations."""
    error_code = "KNOWLEDGE_GRAPH_ERROR"


class RuleNotFoundError(KnowledgeGraphError):
    """Requested rule not found in knowledge graph."""
    error_code = "RULE_NOT_FOUND"


class PrecedentNotFoundError(KnowledgeGraphError):
    """Requested precedent not found in knowledge graph."""
    error_code = "PRECEDENT_NOT_FOUND"


class GraphConnectionError(KnowledgeGraphError):
    """Failed to connect to graph database."""
    error_code = "GRAPH_CONNECTION_ERROR"


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(MahounError):
    """Invalid or missing configuration."""
    error_code = "CONFIGURATION_ERROR"


class MissingSecretError(ConfigurationError):
    """Required secret not set in environment."""
    error_code = "MISSING_SECRET"


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""
    error_code = "INVALID_CONFIG"


# =============================================================================
# LLM Router Errors
# =============================================================================

class LLMRouterError(MahounError):
    """Error in LLM routing."""
    error_code = "LLM_ROUTER_ERROR"


class ModelNotFoundError(LLMRouterError):
    """Requested model not found in registry."""
    error_code = "MODEL_NOT_FOUND"


class ModelUnavailableError(LLMRouterError):
    """Model is unavailable (timeout, error, etc.)."""
    error_code = "MODEL_UNAVAILABLE"


class NoFallbackAvailableError(LLMRouterError):
    """No fallback model available after primary failure."""
    error_code = "NO_FALLBACK_AVAILABLE"


# =============================================================================
# Validation Errors
# =============================================================================

class ValidationError(MahounError):
    """Input validation error."""
    error_code = "VALIDATION_ERROR"


class InputTooLargeError(ValidationError):
    """Input exceeds size limit."""
    error_code = "INPUT_TOO_LARGE"


class InvalidInputTypeError(ValidationError):
    """Input has wrong type."""
    error_code = "INVALID_INPUT_TYPE"


class MissingRequiredFieldError(ValidationError):
    """Required field is missing."""
    error_code = "MISSING_REQUIRED_FIELD"


class SecurityConstraintError(ValidationError):
    """Security constraint violation (e.g., OCR confidence too low)."""
    error_code = "SECURITY_CONSTRAINT_ERROR"


# =============================================================================
# Reasoning Errors
# =============================================================================

class ReasoningError(MahounError):
    """Error in reasoning/verdict generation."""
    error_code = "REASONING_ERROR"


class InsufficientEvidenceError(ReasoningError):
    """Not enough evidence to generate verdict."""
    error_code = "INSUFFICIENT_EVIDENCE"


class ContradictionError(ReasoningError):
    """Unresolvable contradiction in evidence."""
    error_code = "UNRESOLVABLE_CONTRADICTION"


class InvariantViolationError(ReasoningError):
    """Runtime invariant was violated."""
    error_code = "INVARIANT_VIOLATION"


class GovernanceError(MahounError):
    """Governance policy violation.
    
    Links to the unified governance kernel violation model.
    Use GovernanceViolationError from mahoun.core.governance.violations
    for typed governance failures.
    """
    error_code = "GOVERNANCE_VIOLATION"


# =============================================================================
# External Service Errors
# =============================================================================

class ExternalServiceError(MahounError):
    """Error communicating with external service."""
    error_code = "EXTERNAL_SERVICE_ERROR"


class TimeoutError(ExternalServiceError):
    """Operation timed out."""
    error_code = "TIMEOUT_ERROR"


class ConnectionError(ExternalServiceError):
    """Failed to connect to external service."""
    error_code = "CONNECTION_ERROR"


# =============================================================================
# Utility Functions
# =============================================================================

def wrap_exception(
    exc: Exception,
    error_class: type = MahounError,
    message: Optional[str] = None
) -> MahounError:
    """
    Wrap a generic exception in a MahounError.
    
    Args:
        exc: Original exception
        error_class: MahounError subclass to use
        message: Optional custom message
        
    Returns:
        MahounError instance
    """
    msg = message or str(exc)
    return error_class(
        message=msg,
        details={
            "original_type": type(exc).__name__,
            "original_message": str(exc)
        }
    )
