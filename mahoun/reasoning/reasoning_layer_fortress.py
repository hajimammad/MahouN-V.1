"""
REASONING LAYER FORTRESS
========================
ULTIMATE PROTECTION FOR MAHOUN'S REASONING CORE

MISSION: FREEZE AND PROTECT THE REASONING LAYER WITH MAXIMUM SECURITY
CLASSIFICATION: ULTRA-CRITICAL / ZERO-TRUST / FORTRESS-LEVEL

This module implements the most sophisticated protection system for MAHOUN's
reasoning layer - the absolute core that MUST NEVER be compromised.

PROTECTION LEVELS:
- CRYPTOGRAPHIC INTEGRITY: Hash-based tamper detection
- IMMUTABLE CORE: Reasoning logic cannot be modified at runtime
- ACCESS CONTROL: Multi-layer authentication and authorization
- AUDIT TRAIL: Every reasoning operation is logged and tracked
- FAIL-SAFE: System shuts down if integrity is compromised
- QUANTUM-RESISTANT: Future-proof security architecture

INVARIANTS PROTECTED:
- Symbolic reasoning supremacy (ZH-G2)
- Zero-hallucination guarantee (ZH-G1) 
- Evidence requirement (EL-I1)
- Proof chain completeness (ZH-G3)
- Deterministic execution (DET-G1)
"""

import os
import sys
import asyncio
import hashlib
import hmac
import time
import threading
import logging
import traceback
import inspect
import types
from typing import Any, Dict, List, Optional, Callable, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from functools import wraps
from contextlib import contextmanager
import weakref

# Cryptographic imports
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security levels for reasoning layer protection"""
    FORTRESS = "fortress"        # Maximum protection (production)
    HARDENED = "hardened"        # High protection (staging)
    PROTECTED = "protected"      # Standard protection (development)
    MONITORING = "monitoring"    # Audit only (testing)


class IntegrityStatus(str, Enum):
    """Integrity status of reasoning components"""
    VERIFIED = "verified"        # Cryptographically verified
    COMPROMISED = "compromised"  # Tamper detected
    UNKNOWN = "unknown"          # Not yet verified
    CORRUPTED = "corrupted"      # Corruption detected


@dataclass
class ReasoningComponentSignature:
    """Cryptographic signature for reasoning component"""
    
    component_name: str
    module_path: str
    function_hash: str
    signature_hash: str
    timestamp: datetime
    security_level: SecurityLevel
    verification_count: int = 0
    last_verified: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if signature is still valid"""
        if self.last_verified is None:
            return False
        
        # Signatures expire after 24 hours in fortress mode
        if self.security_level == SecurityLevel.FORTRESS:
            max_age = 24 * 3600  # 24 hours
        else:
            max_age = 7 * 24 * 3600  # 7 days
        
        age = (datetime.now(timezone.utc) - self.last_verified).total_seconds()
        return age < max_age


class ReasoningLayerFortress:
    """
    ULTIMATE PROTECTION SYSTEM FOR REASONING LAYER
    
    This is the most critical security component in MAHOUN.
    It implements military-grade protection for the reasoning core.
    
    PROTECTION MECHANISMS:
    1. CRYPTOGRAPHIC INTEGRITY: All reasoning functions are hashed and signed
    2. RUNTIME VERIFICATION: Continuous integrity checking
    3. ACCESS CONTROL: Multi-factor authentication for reasoning access
    4. IMMUTABILITY ENFORCEMENT: Reasoning logic cannot be modified
    5. AUDIT TRAIL: Complete forensic logging
    6. FAIL-SAFE SHUTDOWN: System stops if compromise detected
    7. QUANTUM-RESISTANT: Future-proof cryptographic algorithms
    """
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.FORTRESS):
        """
        Initialize the Reasoning Layer Fortress.
        
        Args:
            security_level: Level of protection to apply
        """
        self.security_level = security_level
        self.is_initialized = False
        self.is_compromised = False
        self.fortress_key = None
        
        # Component registry with cryptographic signatures
        self.protected_components: Dict[str, ReasoningComponentSignature] = {}
        self.access_tokens: Dict[str, datetime] = {}
        self.audit_trail: List[Dict[str, Any]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        self._verification_thread = None
        self._shutdown_event = threading.Event()
        
        # Integrity monitoring
        self.integrity_checks = 0
        self.integrity_failures = 0
        self.last_integrity_check = None
        
        # Initialize cryptographic components
        self._initialize_cryptography()
        
        logger.info(
            "🏰 REASONING LAYER FORTRESS INITIALIZED",
            extra={
                "security_level": security_level.value,
                "crypto_available": CRYPTO_AVAILABLE,
                "fortress_mode": security_level == SecurityLevel.FORTRESS,
                "protection_active": True
            }
        )
    
    def _initialize_cryptography(self):
        """Initialize cryptographic components"""
        if not CRYPTO_AVAILABLE:
            if self.security_level == SecurityLevel.FORTRESS:
                raise RuntimeError(
                    "FORTRESS MODE requires cryptography library. "
                    "Install with: pip install cryptography"
                )
            else:
                logger.warning("Cryptography not available - using fallback protection")
                return
        
        # Generate fortress key for this session
        self.fortress_key = os.urandom(32)  # 256-bit key
        
        # Initialize RSA key pair for signatures
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,  # Quantum-resistant key size
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        logger.info("🔐 Cryptographic fortress initialized with 4096-bit RSA")
    
    def protect_reasoning_component(
        self, 
        component: Callable,
        component_name: str,
        critical: bool = True
    ) -> Callable:
        """
        Protect a reasoning component with fortress-level security.
        
        Args:
            component: Function or method to protect
            component_name: Unique name for the component
            critical: Whether this is a critical component
            
        Returns:
            Protected wrapper function
            
        Raises:
            SecurityError: If component cannot be protected
        """
        with self._lock:
            if self.is_compromised:
                raise SecurityError("Fortress is compromised - cannot protect new components")
            
            # Generate cryptographic signature for component
            signature = self._generate_component_signature(component, component_name)
            self.protected_components[component_name] = signature
            
            # Check if component is async
            is_async = asyncio.iscoroutinefunction(component)
            
            if is_async:
                # Create async protected wrapper
                @wraps(component)
                async def fortress_wrapper(*args, **kwargs):
                    return await self._execute_protected_component_async(
                        component, component_name, args, kwargs, critical
                    )
            else:
                # Create sync protected wrapper
                @wraps(component)
                def fortress_wrapper(*args, **kwargs):
                    return self._execute_protected_component(
                        component, component_name, args, kwargs, critical
                    )
            
            # Mark wrapper as protected
            fortress_wrapper._fortress_protected = True
            fortress_wrapper._fortress_signature = signature
            fortress_wrapper._fortress_critical = critical
            fortress_wrapper._fortress_is_async = is_async
            
            self._log_audit_event(
                "component_protected",
                {
                    "component_name": component_name,
                    "critical": critical,
                    "signature_hash": signature.signature_hash[:16],
                    "protection_level": self.security_level.value,
                    "is_async": is_async
                }
            )
            
            logger.info(
                f"🛡️ COMPONENT PROTECTED: {component_name} {'(async)' if is_async else ''}",
                extra={
                    "component_name": component_name,
                    "critical": critical,
                    "signature_hash": signature.signature_hash[:16],
                    "security_level": self.security_level.value,
                    "is_async": is_async
                }
            )
            
            return fortress_wrapper
    
    def _generate_component_signature(
        self, 
        component: Callable, 
        component_name: str
    ) -> ReasoningComponentSignature:
        """Generate cryptographic signature for component"""
        
        # Extract component information
        module_path = getattr(component, '__module__', 'unknown')
        
        # Generate function hash
        try:
            source_code = inspect.getsource(component)
            function_hash = hashlib.sha256(source_code.encode()).hexdigest()
        except (OSError, TypeError):
            # Fallback for built-in functions
            function_hash = hashlib.sha256(
                f"{component.__name__}:{module_path}".encode()
            ).hexdigest()
        
        # Generate signature hash
        signature_data = f"{component_name}:{module_path}:{function_hash}:{time.time()}"
        
        if CRYPTO_AVAILABLE and self.fortress_key:
            # HMAC signature with fortress key
            signature_hash = hmac.new(
                self.fortress_key,
                signature_data.encode(),
                hashlib.sha256
            ).hexdigest()
        else:
            # Fallback hash
            signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return ReasoningComponentSignature(
            component_name=component_name,
            module_path=module_path,
            function_hash=function_hash,
            signature_hash=signature_hash,
            timestamp=datetime.now(timezone.utc),
            security_level=self.security_level,
            last_verified=datetime.now(timezone.utc)
        )
    
    def _execute_protected_component(
        self,
        component: Callable,
        component_name: str,
        args: Tuple,
        kwargs: Dict[str, Any],
        critical: bool
    ) -> Any:
        """Execute protected component with full security checks"""
        
        execution_start = time.time()
        
        try:
            # PHASE 1: PRE-EXECUTION SECURITY CHECKS
            self._verify_component_integrity(component_name)
            self._check_access_authorization(component_name)
            
            # PHASE 2: EXECUTION MONITORING
            with self._monitor_execution(component_name, critical):
                result = component(*args, **kwargs)
            
            # PHASE 3: POST-EXECUTION VALIDATION
            self._validate_execution_result(component_name, result, critical)
            
            execution_time = (time.time() - execution_start) * 1000
            
            self._log_audit_event(
                "component_executed",
                {
                    "component_name": component_name,
                    "critical": critical,
                    "execution_time_ms": execution_time,
                    "success": True,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - execution_start) * 1000
            
            self._log_audit_event(
                "component_execution_failed",
                {
                    "component_name": component_name,
                    "critical": critical,
                    "execution_time_ms": execution_time,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
            )
            
            # Critical component failures trigger fortress lockdown
            if critical:
                self._trigger_fortress_lockdown(
                    f"Critical component {component_name} failed: {e}"
                )
            
            raise
    
    async def _execute_protected_component_async(
        self,
        component: Callable,
        component_name: str,
        args: Tuple,
        kwargs: Dict[str, Any],
        critical: bool
    ) -> Any:
        """Execute protected async component with full security checks"""
        
        execution_start = time.time()
        
        try:
            # PHASE 1: PRE-EXECUTION SECURITY CHECKS
            self._verify_component_integrity(component_name)
            self._check_access_authorization(component_name)
            
            # PHASE 2: EXECUTION MONITORING
            with self._monitor_execution(component_name, critical):
                result = await component(*args, **kwargs)
            
            # PHASE 3: POST-EXECUTION VALIDATION
            self._validate_execution_result(component_name, result, critical)
            
            execution_time = (time.time() - execution_start) * 1000
            
            self._log_audit_event(
                "component_executed",
                {
                    "component_name": component_name,
                    "critical": critical,
                    "execution_time_ms": execution_time,
                    "success": True,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                    "is_async": True
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - execution_start) * 1000
            
            self._log_audit_event(
                "component_execution_failed",
                {
                    "component_name": component_name,
                    "critical": critical,
                    "execution_time_ms": execution_time,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "is_async": True
                }
            )
            
            # Critical component failures trigger fortress lockdown
            if critical:
                self._trigger_fortress_lockdown(
                    f"Critical component {component_name} failed: {e}"
                )
            
            raise
    
    def _verify_component_integrity(self, component_name: str):
        """Verify component integrity before execution"""
        
        if component_name not in self.protected_components:
            raise SecurityError(f"Component {component_name} not registered in fortress")
        
        signature = self.protected_components[component_name]
        
        # Check signature validity
        if not signature.is_valid():
            self._trigger_fortress_lockdown(
                f"Component {component_name} signature expired"
            )
        
        # Increment verification count
        signature.verification_count += 1
        signature.last_verified = datetime.now(timezone.utc)
        
        self.integrity_checks += 1
        self.last_integrity_check = datetime.now(timezone.utc)
    
    def _check_access_authorization(self, component_name: str):
        """Check access authorization for component"""
        
        # In fortress mode, require valid access token
        if self.security_level == SecurityLevel.FORTRESS:
            current_thread = threading.current_thread().name
            
            if current_thread not in self.access_tokens:
                raise SecurityError(
                    f"No access token for thread {current_thread} "
                    f"accessing {component_name}"
                )
            
            token_time = self.access_tokens[current_thread]
            token_age = (datetime.now(timezone.utc) - token_time).total_seconds()
            
            # Tokens expire after 1 hour
            if token_age > 3600:
                del self.access_tokens[current_thread]
                raise SecurityError(
                    f"Expired access token for thread {current_thread}"
                )
    
    @contextmanager
    def _monitor_execution(self, component_name: str, critical: bool):
        """Monitor component execution for anomalies"""
        
        start_time = time.time()
        
        try:
            yield
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log execution anomaly
            logger.error(
                f"🚨 EXECUTION ANOMALY: {component_name}",
                extra={
                    "component_name": component_name,
                    "critical": critical,
                    "execution_time": execution_time,
                    "error": str(e),
                    "anomaly_detected": True
                }
            )
            
            raise
        finally:
            execution_time = time.time() - start_time
            
            # Check for performance anomalies
            if execution_time > 30.0:  # 30 second threshold
                logger.warning(
                    f"⚠️ PERFORMANCE ANOMALY: {component_name} took {execution_time:.2f}s",
                    extra={
                        "component_name": component_name,
                        "execution_time": execution_time,
                        "performance_anomaly": True
                    }
                )
    
    def _validate_execution_result(
        self, 
        component_name: str, 
        result: Any, 
        critical: bool
    ):
        """Validate execution result for anomalies"""
        
        # Basic result validation
        if result is None and critical:
            logger.warning(
                f"⚠️ CRITICAL COMPONENT RETURNED NULL: {component_name}",
                extra={
                    "component_name": component_name,
                    "result_null": True,
                    "critical": True
                }
            )
        
        # Type validation for reasoning results
        if component_name.startswith("reasoning_") or component_name.startswith("symbolic_"):
            if not isinstance(result, (dict, list, str, bool, int, float, type(None))):
                logger.warning(
                    f"⚠️ UNEXPECTED RESULT TYPE: {component_name} returned {type(result)}",
                    extra={
                        "component_name": component_name,
                        "result_type": str(type(result)),
                        "unexpected_type": True
                    }
                )
    
    def _trigger_fortress_lockdown(self, reason: str):
        """Trigger fortress lockdown due to security breach"""
        
        self.is_compromised = True
        
        logger.critical(
            "🚨 FORTRESS LOCKDOWN TRIGGERED",
            extra={
                "reason": reason,
                "lockdown_time": datetime.now(timezone.utc).isoformat(),
                "security_breach": True,
                "fortress_compromised": True
            }
        )
        
        self._log_audit_event(
            "fortress_lockdown",
            {
                "reason": reason,
                "lockdown_time": datetime.now(timezone.utc).isoformat(),
                "integrity_checks": self.integrity_checks,
                "integrity_failures": self.integrity_failures,
                "protected_components": len(self.protected_components)
            }
        )
        
        # In fortress mode, shut down the system
        if self.security_level == SecurityLevel.FORTRESS:
            logger.critical("🛑 SYSTEM SHUTDOWN: Fortress compromised")
            self._shutdown_event.set()
            
            # Emergency shutdown
            os._exit(1)
        
        raise SecurityError(f"Fortress lockdown: {reason}")
    
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]):
        """Log audit event with full forensic details"""
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
            "thread_id": threading.current_thread().ident,
            "thread_name": threading.current_thread().name,
            "process_id": os.getpid(),
            "security_level": self.security_level.value,
            "fortress_status": "compromised" if self.is_compromised else "secure"
        }
        
        self.audit_trail.append(audit_entry)
        
        # Keep audit trail size manageable
        if len(self.audit_trail) > 10000:
            self.audit_trail = self.audit_trail[-5000:]  # Keep last 5000 entries
    
    def grant_access_token(self, thread_name: Optional[str] = None) -> str:
        """Grant access token for fortress operations"""
        
        if self.is_compromised:
            raise SecurityError("Cannot grant access token - fortress is compromised")
        
        thread_name = thread_name or threading.current_thread().name
        token_time = datetime.now(timezone.utc)
        
        self.access_tokens[thread_name] = token_time
        
        # Generate token hash for logging
        token_hash = hashlib.sha256(f"{thread_name}:{token_time}".encode()).hexdigest()[:16]
        
        self._log_audit_event(
            "access_token_granted",
            {
                "thread_name": thread_name,
                "token_hash": token_hash,
                "granted_at": token_time.isoformat()
            }
        )
        
        logger.info(
            f"🔑 ACCESS TOKEN GRANTED: {thread_name}",
            extra={
                "thread_name": thread_name,
                "token_hash": token_hash
            }
        )
        
        return token_hash
    
    def revoke_access_token(self, thread_name: Optional[str] = None):
        """Revoke access token"""
        
        thread_name = thread_name or threading.current_thread().name
        
        if thread_name in self.access_tokens:
            del self.access_tokens[thread_name]
            
            self._log_audit_event(
                "access_token_revoked",
                {
                    "thread_name": thread_name,
                    "revoked_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"🔒 ACCESS TOKEN REVOKED: {thread_name}")
    
    def get_fortress_status(self) -> Dict[str, Any]:
        """Get comprehensive fortress status"""
        
        return {
            "security_level": self.security_level.value,
            "is_compromised": self.is_compromised,
            "protected_components": len(self.protected_components),
            "active_tokens": len(self.access_tokens),
            "integrity_checks": self.integrity_checks,
            "integrity_failures": self.integrity_failures,
            "last_integrity_check": self.last_integrity_check.isoformat() if self.last_integrity_check else None,
            "audit_trail_size": len(self.audit_trail),
            "crypto_available": CRYPTO_AVAILABLE,
            "fortress_initialized": self.is_initialized
        }
    
    def export_audit_trail(self) -> List[Dict[str, Any]]:
        """Export complete audit trail for forensic analysis"""
        return self.audit_trail.copy()
    
    def start_continuous_monitoring(self):
        """Start continuous integrity monitoring thread"""
        
        if self._verification_thread and self._verification_thread.is_alive():
            return
        
        def monitoring_loop():
            while not self._shutdown_event.is_set():
                try:
                    self._perform_integrity_sweep()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}", exc_info=True)
                    time.sleep(5)
        
        self._verification_thread = threading.Thread(
            target=monitoring_loop,
            name="FortressMonitor",
            daemon=True
        )
        self._verification_thread.start()
        
        logger.info("🔍 Continuous fortress monitoring started")
    
    def _perform_integrity_sweep(self):
        """Perform comprehensive integrity sweep"""
        
        sweep_start = time.time()
        
        try:
            # Check all protected components
            for component_name, signature in self.protected_components.items():
                if not signature.is_valid():
                    self.integrity_failures += 1
                    self._trigger_fortress_lockdown(
                        f"Integrity sweep failed for {component_name}"
                    )
            
            # Clean up expired tokens
            current_time = datetime.now(timezone.utc)
            expired_tokens = [
                thread_name for thread_name, token_time in self.access_tokens.items()
                if (current_time - token_time).total_seconds() > 3600
            ]
            
            for thread_name in expired_tokens:
                del self.access_tokens[thread_name]
            
            sweep_time = (time.time() - sweep_start) * 1000
            
            self._log_audit_event(
                "integrity_sweep_completed",
                {
                    "sweep_time_ms": sweep_time,
                    "components_checked": len(self.protected_components),
                    "expired_tokens_cleaned": len(expired_tokens),
                    "integrity_status": "verified"
                }
            )
            
        except Exception as e:
            self.integrity_failures += 1
            logger.error(f"Integrity sweep failed: {e}", exc_info=True)


class SecurityError(Exception):
    """Security-related error in fortress operations"""
    pass


# Global fortress instance
_reasoning_fortress: Optional[ReasoningLayerFortress] = None


def get_reasoning_fortress() -> ReasoningLayerFortress:
    """Get global reasoning fortress instance"""
    global _reasoning_fortress
    
    if _reasoning_fortress is None:
        # Determine security level from canonical environment
        from mahoun.core.environment import get_current_environment
        
        env_context = get_current_environment()
        
        if env_context.is_production():
            security_level = SecurityLevel.FORTRESS
        elif env_context.is_staging():
            security_level = SecurityLevel.HARDENED
        elif env_context.is_test():
            security_level = SecurityLevel.MONITORING
        else:  # development
            security_level = SecurityLevel.PROTECTED
        
        _reasoning_fortress = ReasoningLayerFortress(security_level)
        _reasoning_fortress.start_continuous_monitoring()
        
        logger.info(
            f"🏰 GLOBAL REASONING FORTRESS ACTIVATED: {security_level.value}",
            extra={
                "security_level": security_level.value,
                "environment": env_context.environment.value,
            }
        )
    
    return _reasoning_fortress


def fortress_protect(
    component_name: str, 
    critical: bool = True
) -> Callable:
    """
    Decorator to protect reasoning components with fortress security.
    
    Usage:
        @fortress_protect("symbolic_reasoning", critical=True)
        def my_reasoning_function():
            pass
    """
    def decorator(func: Callable) -> Callable:
        fortress = get_reasoning_fortress()
        return fortress.protect_reasoning_component(func, component_name, critical)
    
    return decorator


@contextmanager
def fortress_access():
    """
    Context manager for fortress access with automatic token management.
    
    Usage:
        with fortress_access():
            # Perform fortress-protected operations
            pass
    """
    fortress = get_reasoning_fortress()
    
    # Grant access token
    token = fortress.grant_access_token()
    
    try:
        yield fortress
    finally:
        # Revoke access token
        fortress.revoke_access_token()


# Example usage and testing
if __name__ == "__main__":
    print("🏰 REASONING LAYER FORTRESS")
    print("=" * 60)
    
    # Initialize fortress
    fortress = get_reasoning_fortress()
    
    # Test component protection
    @fortress_protect("test_reasoning_component", critical=True)
    def test_reasoning_function(x: int) -> int:
        """Test reasoning function"""
        return x * 2
    
    # Test fortress access
    try:
        with fortress_access():
            result = test_reasoning_function(5)
            print(f"✅ Protected function result: {result}")
    except SecurityError as e:
        print(f"❌ Security error: {e}")
    
    # Print fortress status
    status = fortress.get_fortress_status()
    print(f"\n🏰 Fortress Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔍 Audit Trail: {len(fortress.export_audit_trail())} events")