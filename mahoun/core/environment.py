"""
MAHOUN CANONICAL ENVIRONMENT AUTHORITY
======================================

Classification: CRITICAL PLATFORM GOVERNANCE / IMMUTABLE RUNTIME AUTHORITY
Purpose: Single Source of Truth for Environment Configuration

This module is the ONLY authority for environment resolution across MAHOUN.
All subsystems MUST use this module. Direct os.getenv("MAHOUN_ENV") is FORBIDDEN.

INVARIANTS:
- ENV-G1: Environment is immutable after bootstrap
- ENV-G2: Invalid environments cause explicit failure (no silent fallback)
- ENV-G3: All subsystems use canonical environment
- ENV-G4: Environment resolution is deterministic
- ENV-G5: Environment transitions are audited and logged
- ENV-G6: Test isolation is enforced through context managers
- ENV-G7: Concurrent access is thread-safe

SECURITY GUARANTEES:
- No silent fallbacks to insecure defaults
- No runtime environment mutation (except test isolation)
- Explicit failure on invalid configuration
- Audit trail for all environment resolutions
- Thread-safe singleton pattern

Author: MAHOUN Platform Governance Council
Version: 2.0.0 (Enterprise Hardened)
"""

import os
import sys
import logging
import threading
import traceback
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MahounEnvironment(str, Enum):
    """
    Canonical environment enumeration for MAHOUN platform.
    
    CRITICAL: This is the ONLY valid set of environments.
    No subsystem may define its own environment list.
    
    Security Levels:
    - PRODUCTION: Maximum security, audit-grade, zero-tolerance
    - STAGING: Production-like, pre-deployment validation
    - DEVELOPMENT: Developer workstation, relaxed constraints
    - TEST: Automated testing, deterministic, isolated
    """
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @property
    def security_level(self) -> int:
        """
        Get security enforcement level (0=lowest, 3=highest).
        
        Used by guardrails and enforcement systems.
        """
        levels = {
            self.DEVELOPMENT: 0,
            self.TEST: 1,
            self.STAGING: 2,
            self.PRODUCTION: 3,
        }
        return levels[self]
    
    @property
    def requires_audit_trail(self) -> bool:
        """Check if environment requires full audit trail"""
        return self in (self.STAGING, self.PRODUCTION)
    
    @property
    def allows_unsafe_operations(self) -> bool:
        """Check if environment allows unsafe operations"""
        return self == self.DEVELOPMENT
    
    @property
    def requires_immutable_ledger(self) -> bool:
        """Check if environment requires immutable ledger"""
        return self == self.PRODUCTION
    
    @classmethod
    def from_string(cls, value: str) -> "MahounEnvironment":
        """
        Parse environment from string with strict validation.
        
        Args:
            value: Environment string (case-insensitive)
            
        Returns:
            MahounEnvironment enum
            
        Raises:
            EnvironmentConfigurationError: If environment is invalid
        """
        if not value:
            raise EnvironmentConfigurationError(
                "Environment value cannot be empty"
            )
        
        normalized = value.strip().lower()
        
        # Map common aliases to canonical values
        aliases = {
            "dev": cls.DEVELOPMENT,
            "develop": cls.DEVELOPMENT,
            "development": cls.DEVELOPMENT,
            "test": cls.TEST,
            "testing": cls.TEST,
            "tests": cls.TEST,
            "stage": cls.STAGING,
            "staging": cls.STAGING,
            "prod": cls.PRODUCTION,
            "production": cls.PRODUCTION,
        }
        
        if normalized in aliases:
            return aliases[normalized]
        
        # Invalid environment - FAIL CLOSED
        valid_values = sorted(set(aliases.keys()))
        raise EnvironmentConfigurationError(
            f"Invalid MAHOUN_ENV='{value}'. "
            f"Valid values: {', '.join(valid_values)}"
        )


class EnvironmentConfigurationError(Exception):
    """
    Raised when environment configuration is invalid.
    
    This is a CRITICAL error that should terminate startup.
    NO silent fallbacks are allowed.
    """
    pass


class EnvironmentLockViolation(Exception):
    """
    Raised when attempting to modify locked environment.
    
    Environment is immutable after bootstrap (except test isolation).
    """
    pass


class EnvironmentAccessError(Exception):
    """
    Raised when environment accessed before bootstrap.
    """
    pass


@dataclass(frozen=True)
class EnvironmentTransition:
    """
    Audit record for environment state transitions.
    
    Used for forensic analysis and compliance.
    """
    from_env: Optional[str]
    to_env: str
    timestamp: datetime
    source: str
    caller_stack: str
    thread_id: int
    process_id: int


@dataclass(frozen=True)
class EnvironmentContext:
    """
    Immutable environment context for runtime.
    
    CRITICAL: This object is IMMUTABLE after creation.
    Environment cannot change during process lifetime.
    
    Attributes:
        environment: Canonical environment enum
        resolved_at: UTC timestamp of resolution
        source: How environment was determined
        raw_value: Original string value
        bootstrap_stack: Stack trace at bootstrap (for debugging)
        thread_id: Thread that performed bootstrap
        process_id: Process ID at bootstrap
        transitions: Audit trail of environment changes
    """
    environment: MahounEnvironment
    resolved_at: datetime
    source: str  # "env_var", "default", "override", "test_isolation"
    raw_value: str
    bootstrap_stack: str = field(default="")
    thread_id: int = field(default_factory=lambda: threading.get_ident())
    process_id: int = field(default_factory=os.getpid)
    transitions: List[EnvironmentTransition] = field(default_factory=list)
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == MahounEnvironment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == MahounEnvironment.DEVELOPMENT
    
    def is_test(self) -> bool:
        """Check if running in test"""
        return self.environment == MahounEnvironment.TEST
    
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.environment == MahounEnvironment.STAGING
    
    def get_security_level(self) -> int:
        """Get security enforcement level"""
        return self.environment.security_level
    
    def requires_audit_trail(self) -> bool:
        """Check if audit trail is required"""
        return self.environment.requires_audit_trail
    
    def allows_unsafe_operations(self) -> bool:
        """Check if unsafe operations are allowed"""
        return self.environment.allows_unsafe_operations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "environment": self.environment.value,
            "resolved_at": self.resolved_at.isoformat(),
            "source": self.source,
            "raw_value": self.raw_value,
            "thread_id": self.thread_id,
            "process_id": self.process_id,
            "security_level": self.get_security_level(),
            "transitions_count": len(self.transitions),
        }
    
    def __str__(self) -> str:
        return f"MahounEnvironment({self.environment.value}, source={self.source})"
    
    def __repr__(self) -> str:
        return (
            f"EnvironmentContext("
            f"env={self.environment.value}, "
            f"source={self.source}, "
            f"resolved_at={self.resolved_at.isoformat()}"
            f")"
        )


# Global canonical environment (initialized once at startup)
_CANONICAL_ENVIRONMENT: Optional[EnvironmentContext] = None
_ENVIRONMENT_LOCKED: bool = False
_ENVIRONMENT_LOCK = threading.RLock()  # Thread-safe access
_TRANSITION_HISTORY: List[EnvironmentTransition] = []


def _capture_stack_trace() -> str:
    """Capture current stack trace for audit purposes"""
    return "".join(traceback.format_stack()[:-1])


def _record_transition(
    from_env: Optional[str],
    to_env: str,
    source: str
) -> None:
    """Record environment transition for audit trail"""
    transition = EnvironmentTransition(
        from_env=from_env,
        to_env=to_env,
        timestamp=datetime.now(timezone.utc),
        source=source,
        caller_stack=_capture_stack_trace(),
        thread_id=threading.get_ident(),
        process_id=os.getpid()
    )
    _TRANSITION_HISTORY.append(transition)
    
    logger.debug(
        f"🔄 Environment transition recorded: {from_env} → {to_env}",
        extra={
            "from": from_env,
            "to": to_env,
            "source": source,
            "thread_id": transition.thread_id,
        }
    )


def bootstrap_environment(
    override: Optional[str] = None,
    allow_default: bool = True,
    fail_on_missing: bool = False
) -> EnvironmentContext:
    """
    Bootstrap canonical environment for the platform.
    
    This function MUST be called once at application startup.
    After bootstrap, environment becomes IMMUTABLE.
    
    Thread-safe: Multiple concurrent calls will block until first completes.
    
    Args:
        override: Optional environment override (for testing)
        allow_default: Whether to allow default to DEVELOPMENT
        fail_on_missing: If True, raise error when MAHOUN_ENV not set
        
    Returns:
        Immutable EnvironmentContext
        
    Raises:
        EnvironmentConfigurationError: If environment is invalid
        EnvironmentLockViolation: If environment already bootstrapped
        EnvironmentAccessError: If MAHOUN_ENV missing and fail_on_missing=True
    """
    global _CANONICAL_ENVIRONMENT, _ENVIRONMENT_LOCKED
    
    with _ENVIRONMENT_LOCK:
        if _ENVIRONMENT_LOCKED:
            # Already bootstrapped - return existing
            if _CANONICAL_ENVIRONMENT is None:
                raise RuntimeError(
                    "CRITICAL: Environment locked but context is None. "
                    "This indicates a severe internal error."
                )
            
            logger.debug(
                f"Environment already bootstrapped: {_CANONICAL_ENVIRONMENT.environment.value}"
            )
            return _CANONICAL_ENVIRONMENT
        
        # Determine environment source
        from_env = _CANONICAL_ENVIRONMENT.environment.value if _CANONICAL_ENVIRONMENT else None
        
        if override is not None:
            raw_value = override
            source = "override"
            logger.info(f"🔧 Environment override: {raw_value}")
        else:
            raw_value = os.getenv("MAHOUN_ENV")
            if raw_value is None:
                if fail_on_missing:
                    raise EnvironmentAccessError(
                        "MAHOUN_ENV environment variable not set. "
                        "Set MAHOUN_ENV to one of: development, test, staging, production"
                    )
                if not allow_default:
                    raise EnvironmentConfigurationError(
                        "MAHOUN_ENV not set and default not allowed"
                    )
                raw_value = "development"
                source = "default"
                logger.warning(
                    "⚠️ MAHOUN_ENV not set, defaulting to 'development'. "
                    "Set MAHOUN_ENV explicitly for production deployments."
                )
            else:
                source = "env_var"
        
        # Parse and validate
        try:
            environment = MahounEnvironment.from_string(raw_value)
        except EnvironmentConfigurationError as e:
            logger.critical(
                f"🚨 ENVIRONMENT CONFIGURATION FAILURE: {e}",
                extra={
                    "raw_value": raw_value,
                    "source": source,
                    "critical": True,
                    "process_id": os.getpid(),
                    "thread_id": threading.get_ident(),
                }
            )
            raise
        
        # Capture bootstrap stack for forensics
        bootstrap_stack = _capture_stack_trace()
        
        # Record transition
        _record_transition(from_env, environment.value, source)
        
        # Create immutable context
        context = EnvironmentContext(
            environment=environment,
            resolved_at=datetime.now(timezone.utc),
            source=source,
            raw_value=raw_value,
            bootstrap_stack=bootstrap_stack,
            thread_id=threading.get_ident(),
            process_id=os.getpid(),
            transitions=list(_TRANSITION_HISTORY),  # Copy for immutability
        )
        
        _CANONICAL_ENVIRONMENT = context
        _ENVIRONMENT_LOCKED = True
        
        logger.info(
            f"🔒 ENVIRONMENT LOCKED: {context.environment.value}",
            extra=context.to_dict()
        )
        
        # Production safety check
        if context.is_production():
            logger.critical(
                "🚨 PRODUCTION ENVIRONMENT ACTIVE - Maximum security enforcement enabled",
                extra={
                    "environment": "production",
                    "security_level": 3,
                    "audit_required": True,
                }
            )
        
        return context


def get_current_environment() -> EnvironmentContext:
    """
    Get current canonical environment.
    
    Thread-safe: Can be called from multiple threads concurrently.
    
    Returns:
        Immutable EnvironmentContext
        
    Raises:
        EnvironmentAccessError: If environment not bootstrapped and auto-bootstrap disabled
    """
    with _ENVIRONMENT_LOCK:
        if _CANONICAL_ENVIRONMENT is None:
            # Check if we're in pytest (auto-bootstrap for tests)
            if "pytest" in sys.modules:
                logger.debug(
                    "⚠️ Environment accessed before bootstrap in pytest. "
                    "Auto-bootstrapping with TEST environment."
                )
                return bootstrap_environment(override="test")
            
            # Auto-bootstrap with warning (backward compatibility)
            logger.warning(
                "⚠️ Environment accessed before bootstrap. "
                "Auto-bootstrapping with defaults. "
                "Call bootstrap_environment() explicitly at startup."
            )
            return bootstrap_environment()
        
        return _CANONICAL_ENVIRONMENT


def reset_environment() -> None:
    """
    Reset environment (FOR TESTING ONLY).
    
    This function is ONLY for test isolation.
    NEVER call this in production code.
    
    Thread-safe: Blocks until all concurrent accesses complete.
    
    Raises:
        EnvironmentLockViolation: If called in production environment
    """
    global _CANONICAL_ENVIRONMENT, _ENVIRONMENT_LOCKED
    
    with _ENVIRONMENT_LOCK:
        # Safety check: prevent reset in production
        if _CANONICAL_ENVIRONMENT is not None:
            if _CANONICAL_ENVIRONMENT.is_production():
                raise EnvironmentLockViolation(
                    "CRITICAL: Attempted to reset environment in PRODUCTION. "
                    "This operation is FORBIDDEN in production."
                )
            
            logger.debug(
                f"🔓 Environment reset (was: {_CANONICAL_ENVIRONMENT.environment.value})"
            )
            
            # Record transition
            _record_transition(
                _CANONICAL_ENVIRONMENT.environment.value,
                "RESET",
                "test_isolation"
            )
        
        _CANONICAL_ENVIRONMENT = None
        _ENVIRONMENT_LOCKED = False


@contextmanager
def temporary_environment(env: str):
    """
    Temporarily override environment (FOR TESTING ONLY).
    
    Context manager for test isolation. Automatically restores
    previous environment on exit.
    
    Example:
        with temporary_environment("test"):
            # Code runs with TEST environment
            assert is_test()
        # Previous environment restored
    
    Args:
        env: Temporary environment name
        
    Yields:
        EnvironmentContext for temporary environment
        
    Raises:
        EnvironmentLockViolation: If used in production
    """
    global _CANONICAL_ENVIRONMENT, _ENVIRONMENT_LOCKED
    
    # Safety check
    if _CANONICAL_ENVIRONMENT is not None and _CANONICAL_ENVIRONMENT.is_production():
        raise EnvironmentLockViolation(
            "CRITICAL: Cannot use temporary_environment in PRODUCTION"
        )
    
    # Save current state
    previous_env = _CANONICAL_ENVIRONMENT
    previous_locked = _ENVIRONMENT_LOCKED
    
    try:
        # Reset and bootstrap with override
        reset_environment()
        context = bootstrap_environment(override=env)
        yield context
    finally:
        # Restore previous state
        with _ENVIRONMENT_LOCK:
            _CANONICAL_ENVIRONMENT = previous_env
            _ENVIRONMENT_LOCKED = previous_locked
            
            if previous_env:
                logger.debug(
                    f"🔄 Environment restored to: {previous_env.environment.value}"
                )


def is_environment_locked() -> bool:
    """
    Check if environment has been locked.
    
    Thread-safe.
    """
    with _ENVIRONMENT_LOCK:
        return _ENVIRONMENT_LOCKED


def get_transition_history() -> List[EnvironmentTransition]:
    """
    Get audit trail of environment transitions.
    
    Returns:
        List of environment transitions (for forensic analysis)
    """
    with _ENVIRONMENT_LOCK:
        return list(_TRANSITION_HISTORY)  # Return copy for safety


# Convenience functions for common checks
def is_production() -> bool:
    """
    Check if running in production.
    
    Thread-safe convenience function.
    """
    return get_current_environment().is_production()


def is_development() -> bool:
    """
    Check if running in development.
    
    Thread-safe convenience function.
    """
    return get_current_environment().is_development()


def is_test() -> bool:
    """
    Check if running in test.
    
    Thread-safe convenience function.
    """
    return get_current_environment().is_test()


def is_staging() -> bool:
    """
    Check if running in staging.
    
    Thread-safe convenience function.
    """
    return get_current_environment().is_staging()


def get_environment_name() -> str:
    """
    Get current environment name as string.
    
    Thread-safe convenience function.
    """
    return get_current_environment().environment.value


def get_security_level() -> int:
    """
    Get current security enforcement level (0-3).
    
    Returns:
        0: Development (minimal enforcement)
        1: Test (deterministic enforcement)
        2: Staging (production-like enforcement)
        3: Production (maximum enforcement)
    """
    return get_current_environment().get_security_level()


def requires_audit_trail() -> bool:
    """
    Check if current environment requires audit trail.
    
    Returns True for staging and production.
    """
    return get_current_environment().requires_audit_trail()


def allows_unsafe_operations() -> bool:
    """
    Check if current environment allows unsafe operations.
    
    Returns True only for development.
    """
    return get_current_environment().allows_unsafe_operations()


# Diagnostic and debugging functions
def get_environment_diagnostics() -> Dict[str, Any]:
    """
    Get comprehensive environment diagnostics.
    
    Returns:
        Dictionary with environment state, history, and metadata
    """
    with _ENVIRONMENT_LOCK:
        context = _CANONICAL_ENVIRONMENT
        
        return {
            "current_environment": context.to_dict() if context else None,
            "is_locked": _ENVIRONMENT_LOCKED,
            "transition_count": len(_TRANSITION_HISTORY),
            "transitions": [
                {
                    "from": t.from_env,
                    "to": t.to_env,
                    "timestamp": t.timestamp.isoformat(),
                    "source": t.source,
                    "thread_id": t.thread_id,
                    "process_id": t.process_id,
                }
                for t in _TRANSITION_HISTORY
            ],
            "thread_id": threading.get_ident(),
            "process_id": os.getpid(),
        }


def validate_environment_integrity() -> bool:
    """
    Validate environment integrity (for health checks).
    
    Returns:
        True if environment is properly configured, False otherwise
    """
    try:
        with _ENVIRONMENT_LOCK:
            if not _ENVIRONMENT_LOCKED:
                logger.warning("Environment not locked")
                return False
            
            if _CANONICAL_ENVIRONMENT is None:
                logger.error("Environment locked but context is None")
                return False
            
            # Validate environment enum
            if not isinstance(_CANONICAL_ENVIRONMENT.environment, MahounEnvironment):
                logger.error("Invalid environment type")
                return False
            
            # Validate immutability
            if not isinstance(_CANONICAL_ENVIRONMENT, EnvironmentContext):
                logger.error("Invalid context type")
                return False
            
            return True
    except Exception as e:
        logger.error(f"Environment integrity check failed: {e}")
        return False


# Module initialization logging
logger.debug(
    "🏛️ MAHOUN Canonical Environment Authority loaded",
    extra={
        "module": __name__,
        "version": "2.0.0",
        "thread_safe": True,
        "audit_enabled": True,
    }
)
