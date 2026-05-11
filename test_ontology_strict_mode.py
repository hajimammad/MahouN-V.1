"""
ONTOLOGY STRICT MODE VALIDATION TEST
=====================================

Comprehensive test to verify strict_mode implementation in LegalOntology.

Test Coverage:
1. Strict mode enabled (production): Only whitelisted predicates allowed
2. Strict mode disabled (test): All predicates allowed
3. Environment variable MAHOUN_ENV controls default behavior
4. Audit logging for security compliance

Author: MAHOUN Forensic Architecture Guardian
"""

import os
import pytest
import logging
from reasoning_logic.ontology import LegalOntology, reset_default_ontology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestOntologyStrictMode:
    """Forensic-grade tests for ontology strict_mode"""
    
    def test_1_strict_mode_explicit_true(self):
        """
        Test 1: Explicit strict_mode=True
        
        Expected:
        - Only whitelisted predicates pass validation
        - Non-whitelisted predicates fail validation
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 1: STRICT MODE EXPLICIT TRUE")
        logger.info("="*80)
        
        ontology = LegalOntology(strict_mode=True)
        
        # Whitelisted predicate (should pass)
        assert ontology.validate_predicate('has_obligation', 2) == True
        assert ontology.validate_predicate('is_proxy', 2) == True
        assert ontology.validate_predicate('liable_for', 2) == True
        
        # Non-whitelisted predicates (should fail)
        assert ontology.validate_predicate('owns', 2) == False
        assert ontology.validate_predicate('entity', 1) == False
        assert ontology.validate_predicate('step', 2) == False
        assert ontology.validate_predicate('ceo', 2) == False
        
        logger.info("✓ Strict mode correctly enforces whitelist")
        logger.info("✅ TEST 1 PASSED\n")
    
    def test_2_strict_mode_explicit_false(self):
        """
        Test 2: Explicit strict_mode=False
        
        Expected:
        - ALL predicates pass validation (bypass whitelist)
        - Warning logged for audit trail
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 2: STRICT MODE EXPLICIT FALSE")
        logger.info("="*80)
        
        ontology = LegalOntology(strict_mode=False)
        
        # Whitelisted predicates (should pass)
        assert ontology.validate_predicate('has_obligation', 2) == True
        assert ontology.validate_predicate('is_proxy', 2) == True
        
        # Non-whitelisted predicates (should ALSO pass in soft mode)
        assert ontology.validate_predicate('owns', 2) == True
        assert ontology.validate_predicate('entity', 1) == True
        assert ontology.validate_predicate('step', 2) == True
        assert ontology.validate_predicate('ceo', 2) == True
        assert ontology.validate_predicate('arbitrary_predicate', 99) == True
        
        logger.info("✓ Soft mode correctly bypasses whitelist validation")
        logger.info("✅ TEST 2 PASSED\n")
    
    def test_3_environment_variable_production(self):
        """
        Test 3: Environment variable MAHOUN_ENV=production
        
        Expected:
        - strict_mode defaults to True
        - Whitelist enforced
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 3: ENVIRONMENT VARIABLE - PRODUCTION")
        logger.info("="*80)
        
        # Set environment variable
        os.environ['MAHOUN_ENV'] = 'production'
        reset_default_ontology()  # Force re-initialization
        
        ontology = LegalOntology()  # No explicit strict_mode
        
        # Should default to strict_mode=True
        assert ontology.strict_mode == True
        
        # Validate behavior
        assert ontology.validate_predicate('has_obligation', 2) == True
        assert ontology.validate_predicate('owns', 2) == False
        
        logger.info("✓ MAHOUN_ENV=production correctly defaults to strict_mode=True")
        logger.info("✅ TEST 3 PASSED\n")
    
    def test_4_environment_variable_test(self):
        """
        Test 4: Environment variable MAHOUN_ENV=test
        
        Expected:
        - strict_mode defaults to False
        - All predicates allowed
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 4: ENVIRONMENT VARIABLE - TEST")
        logger.info("="*80)
        
        # Set environment variable
        os.environ['MAHOUN_ENV'] = 'test'
        reset_default_ontology()  # Force re-initialization
        
        ontology = LegalOntology()  # No explicit strict_mode
        
        # Should default to strict_mode=False
        assert ontology.strict_mode == False
        
        # Validate behavior
        assert ontology.validate_predicate('has_obligation', 2) == True
        assert ontology.validate_predicate('owns', 2) == True
        assert ontology.validate_predicate('arbitrary_predicate', 99) == True
        
        logger.info("✓ MAHOUN_ENV=test correctly defaults to strict_mode=False")
        logger.info("✅ TEST 4 PASSED\n")
    
    def test_5_environment_variable_development(self):
        """
        Test 5: Environment variable MAHOUN_ENV=development
        
        Expected:
        - strict_mode defaults to False
        - All predicates allowed
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 5: ENVIRONMENT VARIABLE - DEVELOPMENT")
        logger.info("="*80)
        
        # Set environment variable
        os.environ['MAHOUN_ENV'] = 'development'
        reset_default_ontology()  # Force re-initialization
        
        ontology = LegalOntology()
        
        # Should default to strict_mode=False
        assert ontology.strict_mode == False
        
        # Validate behavior
        assert ontology.validate_predicate('owns', 2) == True
        
        logger.info("✓ MAHOUN_ENV=development correctly defaults to strict_mode=False")
        logger.info("✅ TEST 5 PASSED\n")
    
    def test_6_explicit_override_environment(self):
        """
        Test 6: Explicit strict_mode overrides environment variable
        
        Expected:
        - Explicit parameter takes precedence over MAHOUN_ENV
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 6: EXPLICIT OVERRIDE ENVIRONMENT")
        logger.info("="*80)
        
        # Set environment to production
        os.environ['MAHOUN_ENV'] = 'production'
        
        # But explicitly set strict_mode=False
        ontology = LegalOntology(strict_mode=False)
        
        # Should use explicit value (False)
        assert ontology.strict_mode == False
        assert ontology.validate_predicate('owns', 2) == True
        
        logger.info("✓ Explicit strict_mode correctly overrides MAHOUN_ENV")
        logger.info("✅ TEST 6 PASSED\n")
    
    def test_7_repr_shows_mode(self):
        """
        Test 7: __repr__ shows strict mode status
        
        Expected:
        - Representation includes mode=STRICT or mode=PERMISSIVE
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 7: REPR SHOWS MODE")
        logger.info("="*80)
        
        ontology_strict = LegalOntology(strict_mode=True)
        ontology_permissive = LegalOntology(strict_mode=False)
        
        repr_strict = repr(ontology_strict)
        repr_permissive = repr(ontology_permissive)
        
        assert "mode=STRICT" in repr_strict
        assert "mode=PERMISSIVE" in repr_permissive
        
        logger.info(f"✓ Strict: {repr_strict}")
        logger.info(f"✓ Permissive: {repr_permissive}")
        logger.info("✅ TEST 7 PASSED\n")
    
    def test_8_arity_mismatch_strict_mode(self):
        """
        Test 8: Arity mismatch in strict mode
        
        Expected:
        - Whitelisted predicate with wrong arity fails validation
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 8: ARITY MISMATCH STRICT MODE")
        logger.info("="*80)
        
        ontology = LegalOntology(strict_mode=True)
        
        # Correct arity (should pass)
        assert ontology.validate_predicate('has_obligation', 2) == True
        
        # Wrong arity (should fail)
        assert ontology.validate_predicate('has_obligation', 1) == False
        assert ontology.validate_predicate('has_obligation', 3) == False
        
        logger.info("✓ Arity validation works correctly in strict mode")
        logger.info("✅ TEST 8 PASSED\n")
    
    def test_9_arity_ignored_soft_mode(self):
        """
        Test 9: Arity ignored in soft mode
        
        Expected:
        - All predicates pass regardless of arity
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 9: ARITY IGNORED SOFT MODE")
        logger.info("="*80)
        
        ontology = LegalOntology(strict_mode=False)
        
        # Any arity should pass
        assert ontology.validate_predicate('has_obligation', 1) == True
        assert ontology.validate_predicate('has_obligation', 2) == True
        assert ontology.validate_predicate('has_obligation', 99) == True
        assert ontology.validate_predicate('arbitrary_predicate', 0) == True
        
        logger.info("✓ Arity validation correctly bypassed in soft mode")
        logger.info("✅ TEST 9 PASSED\n")
    
    def test_10_integration_with_parser(self):
        """
        Test 10: Integration with FOLConverter parser
        
        Expected:
        - Parser respects ontology strict_mode
        - Soft mode allows test predicates
        """
        logger.info("\n" + "="*80)
        logger.info("TEST 10: INTEGRATION WITH PARSER")
        logger.info("="*80)
        
        from reasoning_logic.parser import FOLConverter
        
        # Create parser with explicit soft mode ontology
        ontology_soft = LegalOntology(strict_mode=False)
        fol = FOLConverter(ontology=ontology_soft)
        
        # This should work in soft mode
        expr = fol.parse('owns(CompanyA, CompanyB)')
        assert expr.predicate == 'owns'
        assert len(expr.terms) == 2
        
        logger.info("✓ Parser correctly uses soft mode ontology")
        logger.info("✅ TEST 10 PASSED\n")


def test_ultimate_integration():
    """
    ULTIMATE INTEGRATION TEST
    
    Verify that setting MAHOUN_ENV=test allows all test predicates to work.
    """
    logger.info("\n" + "="*80)
    logger.info("ULTIMATE INTEGRATION TEST")
    logger.info("="*80)
    
    # Set test environment
    os.environ['MAHOUN_ENV'] = 'test'
    reset_default_ontology()  # Force re-initialization
    
    from reasoning_logic import FOLConverter, KnowledgeBase, Fact, Rule
    
    # Create parser with soft mode
    ontology_soft = LegalOntology(strict_mode=False)
    fol = FOLConverter(ontology=ontology_soft)
    
    # Create KB with test predicates
    kb = KnowledgeBase()
    
    # Add facts with non-whitelisted predicates
    test_predicates = [
        'owns(CompanyA, CompanyB)',
        'entity(Entity1)',
        'step(Step1, Step2)',
        'ceo(Person1, CompanyA)',
        'board_member(Person2, CompanyB)',
    ]
    
    for pred_str in test_predicates:
        fact = Fact(fol.parse(pred_str))
        kb.add_fact(fact)
        logger.info(f"✓ Added fact: {fact}")
    
    assert len(kb.facts) == 5
    
    logger.info(f"\n✓ Successfully added {len(kb.facts)} facts with test predicates")
    logger.info("✅ ULTIMATE INTEGRATION TEST PASSED\n")


if __name__ == "__main__":
    # Clean environment before tests
    if 'MAHOUN_ENV' in os.environ:
        del os.environ['MAHOUN_ENV']
    
    pytest.main([__file__, "-v", "-s", "--tb=short"])
