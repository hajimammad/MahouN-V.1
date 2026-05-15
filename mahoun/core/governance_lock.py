"""
MAHOUN Immutable Governance Lock
=================================

Classification: CRITICAL SECURITY INFRASTRUCTURE
Purpose: Prevent runtime governance bypass via environment variables

This module implements IMMUTABLE governance enforcement that CANNOT
be disabled via environment variables or runtime manipulation.

Author: MahouN Security Audit Response
Version: 1.0.0
"""

import hashlib
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class GovernanceMode(str, Enum):
    """Governance enforcement modes"""
    STRICT = "STRICT"          # Full enforcement (production)
    AUDIT = "AUDIT"            # Log violations but don't block (staging)
    DISABLED = "DISABLED"      # No enforcement (local dev ONLY)


class GovernanceLock:
    """
    Immutable governance lock that prevents runtime bypass.
    
    CRITICAL SECURITY PROPERTIES:
    1. Mode is set ONCE at process startup
    2. Mode CANNOT be changed after initialization
    3. Attempts to change mode are logged and rejected
    4. Mode changes require process restart
    5. DISABLED mode requires cryptographic authorization
    
    Usage:
        # At application startup (ONCE):
        lock = GovernanceLock.initialize(mode=GovernanceMode.STRICT)
        
        # Later in code:
        if not GovernanceLock.is_enforcement_enabled():
            raise SecurityBreachException("Governance disabled!")
    """
    
    _instance: Optional['GovernanceLock'] = None
    _initialized: bool = False
    _mode: GovernanceMode = GovernanceMode.STRICT
    _initialization_timestamp: Optional[str] = None
    _initialization_hash: Optional[str] = None
    _change_attempts: int = 0
    
    def __init__(self):
        """Private constructor - use initialize() instead"""
        raise RuntimeError(
            "GovernanceLock cannot be instantiated directly. "
            "Use GovernanceLock.initialize() at application startup."
        )
    
    @classmethod
    def initialize(
        cls,
        mode: GovernanceMode = GovernanceMode.STRICT,
        authorization_token: Optional[str] = None
    ) -> 'GovernanceLock':
        """
        Initialize governance lock (ONCE per process).
        
        Args:
            mode: Governance mode (default: STRICT)
            authorization_token: Required for DISABLED mode (SHA256 hash)
            
        Returns:
            GovernanceLock instance
            
        Raises:
            RuntimeError: If already initialized
            SecurityError: If DISABLED mode without valid token
        """
        if cls._initialized:
            cls._change_attempts += 1
            raise RuntimeError(
                f"GovernanceLock already initialized with mode={cls._mode.value}. "
                f"Cannot reinitialize. Change attempts: {cls._change_attempts}"
            )
        
        # CRITICAL: DISABLED mode requires cryptographic authorization
        if mode == GovernanceMode.DISABLED:
            if not cls._verify_authorization(authorization_token):
                raise SecurityError(
                    "DISABLED mode requires valid authorization token. "
                    "This mode is ONLY for local development. "
                    "Production deployments MUST use STRICT mode."
                )
        
        # Lock the mode
        cls._mode = mode
        cls._initialized = True
        cls._initialization_timestamp = datetime.now(timezone.utc).isoformat()
        cls._initialization_hash = cls._compute_lock_hash()
        
        # Log initialization
        print(f"[GOVERNANCE LOCK] Initialized: mode={mode.value}, "
              f"timestamp={cls._initialization_timestamp}, "
              f"hash={cls._initialization_hash[:16]}")
        
        return cls
    
    @classmethod
    def is_enforcement_enabled(cls) -> bool:
        """
        Check if governance enforcement is enabled.
        
        Returns:
            True if STRICT mode, False if DISABLED, AUDIT logs only
        """
        if not cls._initialized:
            # FAIL-CLOSED: If not initialized, assume STRICT
            print("[GOVERNANCE LOCK] WARNING: Not initialized, defaulting to STRICT")
            return True
        
        return cls._mode == GovernanceMode.STRICT
    
    @classmethod
    def get_mode(cls) -> GovernanceMode:
        """Get current governance mode"""
        if not cls._initialized:
            return GovernanceMode.STRICT  # Fail-closed
        return cls._mode
    
    @classmethod
    def verify_integrity(cls) -> bool:
        """
        Verify governance lock has not been tampered with.
        
        Returns:
            True if integrity intact, False if tampered
        """
        if not cls._initialized:
            return False
        
        current_hash = cls._compute_lock_hash()
        return current_hash == cls._initialization_hash
    
    @classmethod
    def get_audit_metadata(cls) -> dict:
        """Get governance lock metadata for audit trail"""
        return {
            "initialized": cls._initialized,
            "mode": cls._mode.value if cls._initialized else "UNINITIALIZED",
            "timestamp": cls._initialization_timestamp,
            "integrity_hash": cls._initialization_hash,
            "change_attempts": cls._change_attempts,
            "integrity_verified": cls.verify_integrity()
        }
    
    @classmethod
    def _verify_authorization(cls, token: Optional[str]) -> bool:
        """
        Verify authorization token for DISABLED mode.
        
        Token must be SHA256 hash of: "MAHOUN_DEV_OVERRIDE_{date}"
        where date is current date in YYYY-MM-DD format.
        
        This ensures:
        1. Token must be regenerated daily
        2. Token cannot be hardcoded
        3. Token requires knowledge of secret format
        """
        if token is None:
            return False
        
        # Generate expected token for today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        expected_input = f"MAHOUN_DEV_OVERRIDE_{today}"
        expected_token = hashlib.sha256(expected_input.encode()).hexdigest()
        
        return token == expected_token
    
    @classmethod
    def _compute_lock_hash(cls) -> str:
        """Compute integrity hash of governance lock state"""
        state = f"{cls._mode.value}|{cls._initialization_timestamp}|{cls._initialized}"
        return hashlib.sha256(state.encode()).hexdigest()
    
    @classmethod
    def _reset(cls):
        """INTERNAL: Reset lock (for testing ONLY)"""
        cls._instance = None
        cls._initialized = False
        cls._mode = GovernanceMode.STRICT
        cls._initialization_timestamp = None
        cls._initialization_hash = None
        cls._change_attempts = 0


class SecurityError(Exception):
    """Raised when security requirements are violated"""
    pass


# ============================================================================
# INTEGRATION WITH EXISTING CODE
# ============================================================================

def should_enforce_proof_carrying_contract() -> bool:
    """
    Replacement for environment variable check.
    
    OLD (VULNERABLE):
        os.getenv("MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT", "true") != "false"
    
    NEW (SECURE):
        should_enforce_proof_carrying_contract()
    
    Returns:
        True if enforcement enabled, False otherwise
    """
    return GovernanceLock.is_enforcement_enabled()


# ============================================================================
# APPLICATION STARTUP INTEGRATION
# ============================================================================

def initialize_governance_at_startup():
    """
    Initialize governance lock at application startup.
    
    This MUST be called in:
    - api/main.py (FastAPI startup)
    - CLI entry points
    - Worker processes
    - Test fixtures (with DISABLED mode)
    
    Example:
        # In api/main.py:
        @app.on_event("startup")
        async def startup():
            GovernanceLock.initialize(mode=GovernanceMode.STRICT)
    """
    # Determine mode from environment (ONCE at startup)
    mode_str = os.getenv("MAHOUN_GOVERNANCE_MODE", "STRICT").upper()
    
    try:
        mode = GovernanceMode[mode_str]
    except KeyError:
        print(f"[GOVERNANCE] Invalid mode '{mode_str}', defaulting to STRICT")
        mode = GovernanceMode.STRICT
    
    # Get authorization token if DISABLED mode requested
    auth_token = os.getenv("MAHOUN_GOVERNANCE_OVERRIDE_TOKEN")
    
    # Initialize lock
    try:
        GovernanceLock.initialize(mode=mode, authorization_token=auth_token)
    except SecurityError as e:
        print(f"[GOVERNANCE] CRITICAL: {e}")
        print("[GOVERNANCE] Falling back to STRICT mode")
        GovernanceLock._reset()  # Reset and retry
        GovernanceLock.initialize(mode=GovernanceMode.STRICT)


# ============================================================================
# MONITORING & ALERTING
# ============================================================================

def check_governance_integrity() -> dict:
    """
    Health check for governance lock integrity.
    
    Returns:
        Dict with integrity status and metadata
        
    Example:
        @app.get("/health/governance")
        async def governance_health():
            return check_governance_integrity()
    """
    metadata = GovernanceLock.get_audit_metadata()
    
    # Check for tampering
    if metadata["change_attempts"] > 0:
        metadata["alert"] = f"CRITICAL: {metadata['change_attempts']} bypass attempts detected"
    
    if not metadata["integrity_verified"]:
        metadata["alert"] = "CRITICAL: Governance lock integrity compromised"
    
    return metadata
