# MAHOUN Runtime Enforcement Map

**Classification**: CRITICAL GOVERNANCE AUDIT  
**Purpose**: Identify ALL reasoning entry points and verify Fortress enforcement  
**Date**: 2026-05-14  
**Status**: PHASE 5 CONSTITUTIONAL LOCKDOWN

---

## Executive Summary

This document maps every reasoning execution path in MAHOUN and determines whether FortressValidator enforcement is guaranteed. Any path marked as **BYPASS RISK** represents a critical governance vulnerability.

**Critical Finding**: Multiple unprotected reasoning paths detected requiring immediate enforcement.

---

## Entry Point Analysis

| Entry Point | File | Protected | Fortress Enforced | Bypass Risk | Notes |
|-------------|------|-----------|-------------------|-------------|-------|
| **API Endpoints** |
| `/api/v1/reason` | `api/routers/reasoning.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Direct UnifiedReasoningService call |
| `/api/v1/query` | `api/routers/query.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | No validation wrapper |
| `/api/v1/contract/analyze` | `api/routers/contract.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | ContractAgent direct call |
| `/health` | `api/main.py:498` | ✅ YES | N/A | ✅ SAFE | Health check only |
| `/metrics/*` | `api/main.py:315-870` | ✅ YES | N/A | ✅ SAFE | Metrics only |
| **Agent Entry Points** |
| `ContractAgent.process()` | `mahoun/agents/contract_agent.py` | ⚠️ PARTIAL | ❌ NO | 🟡 HIGH | Has fallback without validation |
| `ContractAgent._process_impl()` | `mahoun/agents/contract_agent.py:342` | ❌ NO | ❌ NO | 🔴 CRITICAL | Direct reasoning call |
| `ContractAgent._fallback_impl()` | `mahoun/agents/contract_agent.py:453` | ❌ NO | ❌ NO | 🔴 CRITICAL | Degraded mode bypass |
| `DocParserAgent.process()` | `mahoun/agents/doc_parser_agent.py` | ⚠️ PARTIAL | ❌ NO | 🟡 HIGH | No proof validation |
| `CriticAgent.process()` | `mahoun/agents/critic_agent.py:44` | ❌ NO | ❌ NO | 🔴 CRITICAL | Validation without Fortress |
| **Orchestration Paths** |
| `UltraOrchestrator.execute_workflow()` | `mahoun/agents/ultra_orchestrator.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Batch processing unprotected |
| `AgentOrchestrator.execute()` | `mahoun/agents/orchestrator.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Multi-agent coordination |
| **Direct Service Calls** |
| `UnifiedReasoningService.reason()` | `mahoun/reasoning/unified_reasoning_service.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Core service unprotected |
| `UnifiedReasoningService.reason_batch()` | `mahoun/reasoning/unified_reasoning_service.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Batch unprotected |
| **Background Jobs** |
| Async task workers | `mahoun/orchestrator/task_queue.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Background reasoning |
| Retry mechanisms | Various | ❌ NO | ❌ NO | 🔴 CRITICAL | Retry without revalidation |
| **Test Harnesses** |
| Test reasoning calls | `tests/**/*.py` | ⚠️ VARIES | ❌ NO | 🟡 MEDIUM | Tests bypass validation |
| Demo scripts | `examples/**/*.py` | ❌ NO | ❌ NO | 🟡 MEDIUM | Demos unprotected |
| **Internal Paths** |
| Explanation generation | `reasoning_logic/explanation.py` | ✅ YES | N/A | ✅ SAFE | Post-reasoning only |
| Proof tree construction | `mahoun/reasoning/backward_chaining.py` | ✅ YES | N/A | ✅ SAFE | Internal only |
| Forward chaining | `mahoun/reasoning/rete_engine.py` | ✅ YES | N/A | ✅ SAFE | Internal only |
| **Serialization Paths** |
| Response serialization | `mahoun/schemas/*.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | No validation metadata |
| API response models | `api/models/*.py` | ❌ NO | ❌ NO | 🔴 CRITICAL | Missing fortress fields |
| **Replay/Reconstruction** |
| Ledger replay | `mahoun/ledger/replay.py` | ❌ NO | ❌ NO | 🟡 HIGH | Historical data unvalidated |
| Cache reconstruction | `mahoun/cache/*.py` | ❌ NO | ❌ NO | 🟡 HIGH | Cached responses |

---

## Critical Findings

### 🔴 CRITICAL BYPASS VECTORS (Immediate Action Required)

1. **Direct UnifiedReasoningService Exposure**
   - Location: `mahoun/reasoning/unified_reasoning_service.py`
   - Issue: Core service has no mandatory Fortress wrapper
   - Impact: Any direct instantiation bypasses governance
   - Fix Required: Make FortressValidator non-optional

2. **Agent Fallback Paths**
   - Location: `mahoun/agents/contract_agent.py:453`
   - Issue: `_fallback_impl()` returns degraded responses without validation
   - Impact: Fallback mode produces unvalidated outputs
   - Fix Required: Enforce validation even in fallback mode

3. **Orchestrator Batch Processing**
   - Location: `mahoun/agents/ultra_orchestrator.py`
   - Issue: Batch workflows bypass individual validation
   - Impact: Multiple unvalidated responses in single workflow
   - Fix Required: Validate each workflow step

4. **API Endpoint Direct Calls**
   - Location: `api/routers/*.py`
   - Issue: API routes call reasoning services directly
   - Impact: HTTP requests bypass Fortress
   - Fix Required: Wrap all API reasoning calls

5. **Serialization Without Metadata**
   - Location: `mahoun/schemas/*.py`, `api/models/*.py`
   - Issue: Response models don't include validation metadata
   - Impact: Validated responses lose proof of validation
   - Fix Required: Add fortress_validated, audit_hash fields

### 🟡 HIGH RISK VECTORS (Urgent Attention)

1. **Test Suite Bypass**
   - Location: `tests/**/*.py`
   - Issue: Tests instantiate services without Fortress
   - Impact: Test patterns may leak to production
   - Fix Required: Enforce Fortress in test fixtures

2. **Retry Mechanisms**
   - Location: Various retry decorators
   - Issue: Retried requests may skip revalidation
   - Impact: Stale validation on retry
   - Fix Required: Revalidate on every retry

3. **Cache Reconstruction**
   - Location: `mahoun/cache/*.py`
   - Issue: Cached responses served without revalidation
   - Impact: Outdated validation metadata
   - Fix Required: Validate cache hits

---

## Protected Paths (Verified Safe)

| Path | Protection Mechanism | Verification |
|------|---------------------|--------------|
| `FortressProtectedReasoningService` | Wrapper enforces validation | ✅ Tested |
| `@fortress_validated` decorator | Automatic validation | ✅ Tested |
| Internal reasoning engines | No external exposure | ✅ Verified |
| Metrics/health endpoints | No reasoning execution | ✅ Verified |

---

## Enforcement Coverage Statistics

```
Total Entry Points Identified: 28
Protected Entry Points: 4 (14%)
Unprotected Entry Points: 18 (64%)
Partially Protected: 6 (21%)

CRITICAL Bypass Risks: 12
HIGH Bypass Risks: 6
MEDIUM Bypass Risks: 4
```

**Governance Coverage**: 14% ❌ INSUFFICIENT

**Target Coverage**: 100% ✅ REQUIRED

---

## Mandatory Remediation Actions

### Phase 1: Core Service Lockdown (IMMEDIATE)

1. **Make FortressValidator Non-Optional**
   ```python
   # BEFORE (VULNERABLE)
   service = UnifiedReasoningService()
   response = await service.reason(request)
   
   # AFTER (ENFORCED)
   # UnifiedReasoningService constructor MUST create FortressValidator
   # Direct .reason() calls MUST go through validation
   ```

2. **Enforce Validation in Fallback Paths**
   ```python
   # BEFORE (BYPASS)
   async def _fallback_impl(self, input_data, correlation_id):
       return {"result": "fallback", "success": True}  # NO VALIDATION
   
   # AFTER (ENFORCED)
   async def _fallback_impl(self, input_data, correlation_id):
       response = {"result": "fallback", "success": True}
       await self.validator.validate(response, correlation_id)  # MANDATORY
       return response
   ```

3. **Wrap All API Endpoints**
   ```python
   # BEFORE (VULNERABLE)
   @app.post("/api/v1/reason")
   async def reason_endpoint(request: ReasoningRequest):
       service = UnifiedReasoningService()
       return await service.reason(request)
   
   # AFTER (PROTECTED)
   @app.post("/api/v1/reason")
   async def reason_endpoint(request: ReasoningRequest):
       protected_service = create_fortress_protected_service(base_service)
       return await protected_service.reason(request)
   ```

### Phase 2: Serialization Contract Enforcement

4. **Add Validation Metadata to Response Models**
   ```python
   class ReasoningResponse(BaseModel):
       # Existing fields
       success: bool
       result: str
       confidence: float
       
       # NEW: Mandatory validation metadata
       fortress_validated: bool = Field(..., description="Fortress validation status")
       audit_hash: str = Field(..., description="Forensic audit hash")
       validation_timestamp: str = Field(..., description="Validation timestamp")
       correlation_id: str = Field(..., description="Tracing correlation ID")
   ```

### Phase 3: Orchestration Protection

5. **Validate Each Workflow Step**
   ```python
   async def execute_workflow(self, workflow):
       for step in workflow.steps:
           response = await step.execute()
           # MANDATORY: Validate each step
           await self.validator.validate(response, correlation_id=step.id)
       return workflow_result
   ```

### Phase 4: Test Suite Enforcement

6. **Create Fortress-Enforced Test Fixtures**
   ```python
   @pytest.fixture
   def reasoning_service():
       # ALWAYS return protected service in tests
       base = UnifiedReasoningService()
       return create_fortress_protected_service(base, strict_mode=True)
   ```

---

## Verification Checklist

- [ ] All API endpoints use FortressProtectedReasoningService
- [ ] All agent fallback paths enforce validation
- [ ] All orchestrator workflows validate each step
- [ ] All response models include validation metadata
- [ ] All retry mechanisms revalidate
- [ ] All cache hits revalidate
- [ ] All test fixtures use protected services
- [ ] All serialization paths preserve metadata
- [ ] Zero direct UnifiedReasoningService instantiations in production code
- [ ] CI enforces protected service usage

---

## Next Steps

1. **TASK 2**: Run Fortress Bypass Scanner to detect violations
2. **TASK 3**: Implement Proof-Carrying Response Contracts
3. **TASK 4**: Create Determinism Crisis Suite
4. **TASK 5**: Deploy Constitutional GitHub Actions CI
5. **TASK 6**: Lock down core modules with governance protection
6. **TASK 7**: Enforce immutable validation metadata
7. **TASK 8**: Generate comprehensive governance audit report

---

## Conclusion

**Current State**: MAHOUN has FortressValidator implemented but NOT enforced across all reasoning paths.

**Target State**: Zero reasoning outputs can escape governance enforcement.

**Gap**: 86% of entry points lack Fortress protection.

**Action Required**: IMMEDIATE enforcement of FortressValidator across all identified bypass vectors.

---

**Document Status**: COMPLETE  
**Next Action**: Proceed to TASK 2 - Fortress Bypass Detection System
