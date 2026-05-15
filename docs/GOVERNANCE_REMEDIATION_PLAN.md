# MAHOUN Governance Security Remediation Plan
## Operational Action Plan for Production Readiness

**Version:** 1.0.0  
**Date:** 2026-05-14  
**Status:** ACTIVE  
**Owner:** Engineering Security Team  

---

## Executive Summary

This document provides a **step-by-step operational plan** to remediate the security vulnerabilities identified in the Governance Security Audit Report.

**Timeline:** 3-4 weeks (132 hours total effort)  
**Resources Required:** 1 senior engineer + 1 security reviewer  
**Success Criteria:** All P0 items resolved, trustworthiness score ≥ 8/10  

---

## Phase 1: Critical Blockers (P0) - Week 1

**Objective:** Fix deployment-blocking vulnerabilities  
**Duration:** 12 hours  
**Status:** 🔴 NOT STARTED  

### Task 1.1: Integrate GovernanceLock (2 hours)

**Priority:** P0 - CRITICAL  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Steps:**

1. **Modify `mahoun/reasoning/unified_reasoning_service.py`**
   ```python
   # OLD (line ~180)
   def _enforce_contract(self) -> bool:
       import os
       return os.getenv("MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT", "true").lower() != "false"
   
   # NEW
   def _enforce_contract(self) -> bool:
       from mahoun.core.governance_lock import should_enforce_proof_carrying_contract
       return should_enforce_proof_carrying_contract()
   ```

2. **Add GovernanceLock initialization to `api/main.py`**
   ```python
   from mahoun.core.governance_lock import initialize_governance_at_startup
   
   @app.on_event("startup")
   async def startup():
       # Initialize governance lock (ONCE per process)
       initialize_governance_at_startup()
       logger.info("Governance lock initialized")
   ```

3. **Add GovernanceLock to test fixtures**
   ```python
   # tests/conftest.py
   import pytest
   from mahoun.core.governance_lock import GovernanceLock, GovernanceMode
   
   @pytest.fixture(autouse=True)
   def reset_governance_lock():
       """Reset governance lock before each test"""
       GovernanceLock._reset()
       GovernanceLock.initialize(mode=GovernanceMode.DISABLED, 
                                  authorization_token=generate_test_token())
       yield
       GovernanceLock._reset()
   ```

4. **Remove or protect `_reset()` method**
   ```python
   # mahoun/core/governance_lock.py
   @classmethod
   def _reset(cls):
       """INTERNAL: Reset lock (for testing ONLY)"""
       # Add runtime protection
       import os
       if os.getenv("MAHOUN_ENV") != "test":
           raise RuntimeError("_reset() can only be called in test environment")
       cls._initialized = False
       # ...
   ```

**Verification:**
```bash
# Run tests
pytest tests/test_proof_carrying_contracts.py -v

# Verify governance lock is active
python -c "from mahoun.core.governance_lock import GovernanceLock; print(GovernanceLock.get_mode())"
```

**Success Criteria:**
- ✅ All tests pass
- ✅ GovernanceLock initialized at startup
- ✅ Environment variable bypass eliminated
- ✅ `_reset()` protected

---

### Task 1.2: Fix Audit Hash Coverage (4 hours)

**Priority:** P0 - CRITICAL  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Steps:**

1. **Implement canonical serialization helper**
   ```python
   # mahoun/core/fortress_validator.py
   
   import json
   from typing import Any, Dict
   
   def _canonical_serialize(obj: Any) -> str:
       """
       Canonical serialization for hash computation.
       
       Properties:
       - Deterministic field ordering (sorted keys)
       - Consistent float representation
       - Unicode normalization
       - Null handling
       """
       if isinstance(obj, dict):
           # Sort keys for deterministic ordering
           sorted_dict = {k: _canonical_serialize(v) for k, v in sorted(obj.items())}
           return json.dumps(sorted_dict, sort_keys=True, ensure_ascii=False)
       elif isinstance(obj, (list, tuple)):
           return json.dumps([_canonical_serialize(item) for item in obj], ensure_ascii=False)
       elif isinstance(obj, float):
           # Consistent float representation (6 decimal places)
           return f"{obj:.6f}"
       elif obj is None:
           return "null"
       else:
           return str(obj)
   ```

2. **Update `_compute_response_hash()` to include all fields**
   ```python
   def _compute_response_hash(self, response: ReasoningResponse) -> str:
       """
       Compute cryptographic hash of response for audit trail.
       
       Includes ALL fields to prevent tampering:
       - result, confidence, reasoning_mode
       - proof_tree, derived_facts
       - fortress_validated, validation_timestamp, correlation_id
       """
       # Build hash input with all critical fields
       hash_data = {
           "result": response.result,
           "confidence": response.confidence,
           "reasoning_mode": response.reasoning_mode,
           "proof_tree": str(response.proof_tree) if response.proof_tree else None,
           "derived_facts": response.derived_facts,
           "fortress_validated": response.fortress_validated,
           "validation_timestamp": response.validation_timestamp,
           "correlation_id": response.correlation_id,
       }
       
       # Canonical serialization
       canonical_input = _canonical_serialize(hash_data)
       
       # Full 256-bit hash (no truncation)
       return hashlib.sha256(canonical_input.encode('utf-8')).hexdigest()
   ```

3. **Add hash verification method**
   ```python
   def verify_audit_hash(self, response: ReasoningResponse) -> bool:
       """
       Verify audit hash integrity.
       
       Returns:
           True if hash is valid, False if tampered
       """
       if response.audit_hash is None:
           return False
       
       # Recompute hash
       expected_hash = self._compute_response_hash(response)
       
       # Constant-time comparison (prevent timing attacks)
       import hmac
       return hmac.compare_digest(expected_hash, response.audit_hash)
   ```

4. **Add tests for hash integrity**
   ```python
   # tests/test_fortress_validator.py
   
   @pytest.mark.asyncio
   async def test_audit_hash_includes_all_fields():
       """Test that audit hash covers all critical fields"""
       validator = FortressValidator()
       
       response = create_valid_response()
       result = await validator.validate(response)
       
       original_hash = response.audit_hash
       
       # Tamper with each field and verify hash changes
       response.result = "TAMPERED"
       assert not validator.verify_audit_hash(response)
       
       response.result = original_result
       response.proof_tree = None
       assert not validator.verify_audit_hash(response)
       
       # ... test all fields
   ```

**Verification:**
```bash
# Run hash integrity tests
pytest tests/test_fortress_validator.py::test_audit_hash_includes_all_fields -v

# Verify hash length (should be 64 characters)
python -c "from mahoun.core.fortress_validator import FortressValidator; v = FortressValidator(); print(len(v._compute_response_hash(response)))"
```

**Success Criteria:**
- ✅ Hash includes ALL fields
- ✅ Hash is full 256-bit (64 hex characters)
- ✅ Canonical serialization implemented
- ✅ Tampering detection tests pass

---

### Task 1.3: Add Concurrency Locks (3 hours)

**Priority:** P0 - HIGH  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Steps:**

1. **Add async locks to FortressValidator**
   ```python
   # mahoun/core/fortress_validator.py
   
   import asyncio
   
   class FortressValidator:
       def __init__(self, ...):
           # ... existing code ...
           
           # Concurrency protection
           self._stats_lock = asyncio.Lock()
           self._audit_lock = asyncio.Lock()
   ```

2. **Protect stats mutations**
   ```python
   async def _update_stats(self, passed: bool, violations: List[Dict], execution_time_ms: float):
       """Update validation statistics (thread-safe)"""
       async with self._stats_lock:
           self.stats["total_validations"] += 1
           
           if passed:
               self.stats["passed"] += 1
           else:
               self.stats["failed"] += 1
           
           # ... rest of stats update ...
   ```

3. **Protect audit trail appends**
   ```python
   async def validate(self, response, correlation_id):
       # ... validation logic ...
       
       # Store forensic context (thread-safe)
       async with self._audit_lock:
           self.audit_trail.append(forensic_ctx)
   ```

4. **Make metadata injection atomic**
   ```python
   def _inject_proof_carrying_metadata(
       self,
       response: ReasoningResponse,
       forensic_ctx: ForensicContext,
       correlation_id: str
   ) -> None:
       """
       Inject proof-carrying metadata atomically.
       
       All fields are set in a single operation to prevent
       partial state visibility to concurrent readers.
       """
       # Build metadata dict
       metadata = {
           "fortress_validated": True,
           "audit_hash": forensic_ctx.response_hash,
           "validation_timestamp": forensic_ctx.timestamp,
           "correlation_id": correlation_id
       }
       
       # Atomic update (all fields at once)
       for key, value in metadata.items():
           setattr(response, key, value)
   ```

5. **Add concurrency stress tests**
   ```python
   # tests/test_fortress_validator_concurrency.py
   
   @pytest.mark.asyncio
   async def test_concurrent_validation_stress():
       """Test 1000 concurrent validations"""
       validator = FortressValidator()
       
       # Create 1000 validation tasks
       tasks = [
           validator.validate(create_valid_response(), correlation_id=f"req-{i}")
           for i in range(1000)
       ]
       
       # Execute concurrently
       results = await asyncio.gather(*tasks, return_exceptions=True)
       
       # Verify no exceptions
       exceptions = [r for r in results if isinstance(r, Exception)]
       assert len(exceptions) == 0
       
       # Verify stats consistency
       assert validator.stats["total_validations"] == 1000
       assert validator.stats["passed"] + validator.stats["failed"] == 1000
   ```

**Verification:**
```bash
# Run concurrency tests
pytest tests/test_fortress_validator_concurrency.py -v

# Run stress test
pytest tests/test_fortress_validator_concurrency.py::test_concurrent_validation_stress -v --timeout=30
```

**Success Criteria:**
- ✅ Async locks added
- ✅ Stats mutations protected
- ✅ Audit trail appends protected
- ✅ Metadata injection atomic
- ✅ Concurrency stress tests pass

---

### Task 1.4: Make Response Immutable (1 hour)

**Priority:** P0 - HIGH  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Steps:**

1. **Add `frozen=True` to ReasoningResponse**
   ```python
   # mahoun/reasoning/unified_reasoning_service.py
   
   @dataclass(frozen=True)  # Make immutable
   class ReasoningResponse:
       success: bool
       result: Any
       confidence: float
       # ... rest of fields ...
   ```

2. **Handle immutability in FortressValidator**
   ```python
   # Since response is frozen, we need to create a new instance with metadata
   
   def _inject_proof_carrying_metadata(
       self,
       response: ReasoningResponse,
       forensic_ctx: ForensicContext,
       correlation_id: str
   ) -> ReasoningResponse:
       """
       Create new response with proof-carrying metadata.
       
       Since ReasoningResponse is frozen, we create a new instance
       with all original fields plus proof-carrying metadata.
       """
       from dataclasses import replace
       
       return replace(
           response,
           fortress_validated=True,
           audit_hash=forensic_ctx.response_hash,
           validation_timestamp=forensic_ctx.timestamp,
           correlation_id=correlation_id
       )
   ```

3. **Update validate() to return new instance**
   ```python
   async def validate(self, response, correlation_id):
       # ... validation logic ...
       
       # If passed, create new response with metadata
       if passed:
           response = self._inject_proof_carrying_metadata(
               response, forensic_ctx, correlation_id
           )
       
       return ValidationResult(...), response  # Return both
   ```

4. **Add immutability tests**
   ```python
   def test_response_immutability():
       """Test that ReasoningResponse is immutable"""
       response = ReasoningResponse(...)
       
       # Attempt mutation (should raise FrozenInstanceError)
       with pytest.raises(dataclasses.FrozenInstanceError):
           response.fortress_validated = False
   ```

**Verification:**
```bash
# Run immutability tests
pytest tests/test_proof_carrying_contracts.py::test_response_immutability -v
```

**Success Criteria:**
- ✅ ReasoningResponse is frozen
- ✅ Metadata injection creates new instance
- ✅ Mutation attempts raise exception
- ✅ All tests pass

---

### Task 1.5: Fix Failing Tests (2 hours)

**Priority:** P0 - MEDIUM  
**Assignee:** Backend Engineer  
**Dependencies:** Task 1.1 (GovernanceLock integration)  

**Steps:**

1. **Identify failing tests**
   ```bash
   pytest tests/test_proof_carrying_contracts.py -v
   # Expected: 5 failures related to environment variables
   ```

2. **Update test fixtures to use GovernanceLock**
   ```python
   # tests/conftest.py
   
   @pytest.fixture(autouse=True)
   def setup_governance_for_tests():
       """Setup governance lock for tests"""
       from mahoun.core.governance_lock import GovernanceLock, GovernanceMode
       import hashlib
       from datetime import datetime
       
       # Generate valid test token
       today = datetime.now().strftime("%Y-%m-%d")
       token = hashlib.sha256(f"MAHOUN_DEV_OVERRIDE_{today}".encode()).hexdigest()
       
       # Initialize in DISABLED mode for tests
       GovernanceLock._reset()
       GovernanceLock.initialize(mode=GovernanceMode.DISABLED, authorization_token=token)
       
       yield
       
       # Cleanup
       GovernanceLock._reset()
   ```

3. **Remove environment variable manipulation from tests**
   ```python
   # OLD (remove this)
   def test_contract_can_be_disabled_via_env_var(self, monkeypatch):
       monkeypatch.setenv("MAHOUN_ENFORCE_PROOF_CARRYING_CONTRACT", "false")
       # ...
   
   # NEW (use GovernanceLock)
   def test_contract_enforcement_respects_governance_lock(self):
       from mahoun.core.governance_lock import GovernanceLock, GovernanceMode
       
       # Governance lock already in DISABLED mode from fixture
       assert GovernanceLock.get_mode() == GovernanceMode.DISABLED
       
       # Contract enforcement should be disabled
       response = ReasoningResponse(...)  # No exception
   ```

4. **Run full test suite**
   ```bash
   pytest tests/test_proof_carrying_contracts.py -v
   # Expected: 16/16 passing
   ```

**Verification:**
```bash
# Run all tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=mahoun.core --cov=mahoun.reasoning --cov-report=html
```

**Success Criteria:**
- ✅ All 16 tests passing (0 failures)
- ✅ No environment variable manipulation
- ✅ GovernanceLock used consistently
- ✅ Test coverage maintained

---

## Phase 1 Completion Checklist

- [ ] Task 1.1: GovernanceLock integrated
- [ ] Task 1.2: Audit hash coverage fixed
- [ ] Task 1.3: Concurrency locks added
- [ ] Task 1.4: Response made immutable
- [ ] Task 1.5: All tests passing

**Phase 1 Success Criteria:**
- ✅ All P0 tasks completed
- ✅ All tests passing (0 failures)
- ✅ No critical vulnerabilities remaining
- ✅ Ready for Phase 2

**Estimated Completion:** End of Week 1

---

## Phase 2: Security Hardening (P1) - Weeks 2-3

**Objective:** Implement enterprise-grade security measures  
**Duration:** 40 hours  
**Status:** 🟡 PENDING (blocked by Phase 1)  

### Task 2.1: Implement HMAC-SHA256 (6 hours)

**Priority:** P1 - HIGH  
**Assignee:** Security Engineer  
**Dependencies:** Task 1.2 (audit hash coverage)  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 3.1

---

### Task 2.2: Persistent Audit Trail (8 hours)

**Priority:** P1 - HIGH  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 4.1

---

### Task 2.3: Adversarial Test Suite (6 hours)

**Priority:** P1 - HIGH  
**Assignee:** QA Engineer  
**Dependencies:** Phase 1 complete  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 5.1

---

### Task 2.4: Branch Coverage + Mutation Testing (8 hours)

**Priority:** P1 - MEDIUM  
**Assignee:** QA Engineer  
**Dependencies:** Task 2.3  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 5.2

---

### Task 2.5: Post-Deserialization Validation (4 hours)

**Priority:** P1 - MEDIUM  
**Assignee:** Backend Engineer  
**Dependencies:** Task 1.4 (immutability)  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 6.1

---

### Task 2.6: Load Thresholds from RedLines.yaml (4 hours)

**Priority:** P1 - HIGH  
**Assignee:** Backend Engineer  
**Dependencies:** None  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 7.1

---

### Task 2.7: Proof Expiration (4 hours)

**Priority:** P1 - MEDIUM  
**Assignee:** Backend Engineer  
**Dependencies:** Task 1.2 (audit hash)  

**Implementation:** See `SECURITY_HARDENING_GUIDE.md` Section 8.1

---

## Phase 2 Completion Checklist

- [ ] Task 2.1: HMAC-SHA256 implemented
- [ ] Task 2.2: Persistent audit trail
- [ ] Task 2.3: Adversarial test suite
- [ ] Task 2.4: Branch/mutation coverage
- [ ] Task 2.5: Post-deserialization validation
- [ ] Task 2.6: Thresholds from RedLines.yaml
- [ ] Task 2.7: Proof expiration

**Phase 2 Success Criteria:**
- ✅ All P1 tasks completed
- ✅ Trustworthiness score ≥ 8/10
- ✅ Ready for production deployment

**Estimated Completion:** End of Week 3

---

## Phase 3: Enterprise Readiness (P2) - Week 4+

**Objective:** Achieve enterprise-grade compliance and scalability  
**Duration:** 80 hours  
**Status:** 🔵 FUTURE (blocked by Phase 2)  

**Tasks:** See `SECURITY_HARDENING_GUIDE.md` Section 9

---

## Progress Tracking

### Week 1 (Phase 1)
- [ ] Day 1-2: Tasks 1.1, 1.2
- [ ] Day 3: Task 1.3
- [ ] Day 4: Tasks 1.4, 1.5
- [ ] Day 5: Testing & verification

### Week 2-3 (Phase 2)
- [ ] Week 2: Tasks 2.1-2.4
- [ ] Week 3: Tasks 2.5-2.7

### Week 4+ (Phase 3)
- [ ] Long-term roadmap items

---

## Risk Management

### High-Risk Items
1. **Immutability changes** may break existing code
   - Mitigation: Comprehensive testing, gradual rollout
2. **HMAC key management** requires secure storage
   - Mitigation: Use environment variables, KMS integration
3. **Persistent audit trail** may impact performance
   - Mitigation: Async writes, connection pooling

### Contingency Plans
- If Phase 1 takes longer: Extend timeline, prioritize P0 items
- If tests fail: Roll back changes, investigate root cause
- If performance degrades: Optimize, add caching

---

## Success Metrics

### Phase 1 (P0)
- ✅ 0 critical vulnerabilities
- ✅ 0 test failures
- ✅ Trustworthiness score ≥ 7/10

### Phase 2 (P1)
- ✅ Trustworthiness score ≥ 8/10
- ✅ Branch coverage ≥ 90%
- ✅ Mutation score ≥ 80%

### Phase 3 (P2)
- ✅ Trustworthiness score ≥ 9/10
- ✅ SOC 2 compliance ready
- ✅ Production deployment approved

---

**END OF REMEDIATION PLAN**

**Next Steps:**
1. Review and approve plan
2. Assign resources
3. Begin Phase 1 execution
4. Track progress daily
5. Conduct security review after each phase

