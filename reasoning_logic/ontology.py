"""
Legal Ontology Management
==========================

Externalized ontology configuration for Legal-DSL validation.

This module provides a flexible, extensible ontology system that can be:
- Loaded from JSON/YAML files
- Extended at runtime
- Versioned for backward compatibility
- Customized per jurisdiction

STRICT MODE:
- When strict_mode=True (default in production): Only whitelisted predicates allowed
- When strict_mode=False (test/research): All predicates allowed (validation bypassed)
- Environment variable MAHOUN_ENV controls default behavior

Author: MAHOUN Team
"""

from typing import Dict, List, Optional, Set
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class LegalOntology:
    """
    Legal ontology for DSL validation
    
    Manages predicates, term types, and validation rules for legal reasoning.
    """
    
    # Default built-in ontology (fallback)
    DEFAULT_ONTOLOGY = {
        "predicates": {
            "has_obligation": {"arity": 2, "term_types": ["Person", "Contract"]},
            "is_proxy": {"arity": 2, "term_types": ["Person", "Person"]},
            "violates_article": {"arity": 2, "term_types": ["Contract", "Article"]},
            "applies_to_jurisdiction": {"arity": 2, "term_types": ["Article", "Jurisdiction"]},
            "signed_by": {"arity": 2, "term_types": ["Contract", "Person"]},
            "breach_of_contract": {"arity": 2, "term_types": ["Person", "Contract"]},
            "liable_for": {"arity": 2, "term_types": ["Person", "Liability"]},
        },
        "term_types": [
            "Person", "Contract", "Article", "Jurisdiction", "Liability",
            "Date", "Amount", "Court", "Verdict"
        ],
        "version": "1.0.0",
        "jurisdiction": "default"
    }
    
    def __init__(self, ontology_file: Optional[str] = None, strict_mode: Optional[bool] = None):
        """
        Initialize legal ontology
        
        Args:
            ontology_file: Path to JSON ontology file (optional)
            strict_mode: Enable strict predicate validation (optional)
                        - True: Only whitelisted predicates allowed (production default)
                        - False: All predicates allowed (test/research mode)
                        - None: Auto-detect from canonical environment
        
        Environment:
            Uses canonical environment authority (mahoun.core.environment)
            - production: strict_mode=True
            - test/development/staging: strict_mode=False
        """
        self.predicates: Dict[str, Dict] = {}
        self.term_types: Set[str] = set()
        self.version: str = "unknown"
        self.jurisdiction: str = "default"
        
        # Determine strict_mode from canonical environment if not explicitly set
        if strict_mode is None:
            try:
                from mahoun.core.environment import get_current_environment
                env_context = get_current_environment()
                self.strict_mode = env_context.is_production()
                env_name = env_context.environment.value
            except Exception as e:
                # Fallback for edge cases (should not happen in normal operation)
                logger.warning(f"Failed to get canonical environment: {e}. Defaulting to strict_mode=True")
                self.strict_mode = True
                env_name = "unknown"
        else:
            self.strict_mode = strict_mode
            env_name = "explicit"
        
        # Log strict_mode status for audit trail
        if not self.strict_mode:
            logger.warning(
                "⚠️  ONTOLOGY STRICT MODE DISABLED - All predicates will be accepted. "
                "This should ONLY be used in test/research environments. "
                f"Environment={env_name}"
            )
        else:
            logger.info(
                "✓ Ontology strict mode ENABLED - Only whitelisted predicates allowed. "
                f"Environment={env_name}"
            )
        
        if ontology_file:
            self.load_from_file(ontology_file)
        else:
            self.load_default()
    
    def load_default(self):
        """Load default built-in ontology"""
        self._load_from_dict(self.DEFAULT_ONTOLOGY)
        logger.info("Loaded default legal ontology")
    
    def load_from_file(self, path: str):
        """
        Load ontology from JSON file
        
        Args:
            path: Path to JSON ontology file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        file_path = Path(path)
        
        if not file_path.exists():
            logger.warning(f"Ontology file not found: {path}. Loading default.")
            self.load_default()
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._load_from_dict(data)
            logger.info(f"Loaded legal ontology from {path} (version: {self.version})")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ontology file {path}: {e}")
            raise ValueError(f"Invalid ontology file format: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load ontology from {path}: {e}")
            raise
    
    def _load_from_dict(self, data: dict):
        """Load ontology from dictionary"""
        self.predicates = data.get("predicates", {})
        self.term_types = set(data.get("term_types", []))
        self.version = data.get("version", "unknown")
        self.jurisdiction = data.get("jurisdiction", "default")
    
    def register_predicate(self, name: str, arity: int, term_types: List[str]):
        """
        Register a new predicate at runtime
        
        Args:
            name: Predicate name
            arity: Number of arguments
            term_types: Expected term types for each argument
            
        Raises:
            ValueError: If arity doesn't match term_types length
        """
        if len(term_types) != arity:
            raise ValueError(
                f"Arity mismatch: {arity} != {len(term_types)} for predicate '{name}'"
            )
        
        self.predicates[name] = {
            "arity": arity,
            "term_types": term_types
        }
        
        logger.debug(f"Registered predicate: {name}/{arity}")
    
    def register_term_type(self, term_type: str):
        """
        Register a new term type
        
        Args:
            term_type: Term type name
        """
        self.term_types.add(term_type)
        logger.debug(f"Registered term type: {term_type}")
    
    def validate_predicate(self, name: str, arity: int) -> bool:
        """
        Validate that predicate exists with correct arity
        
        Args:
            name: Predicate name
            arity: Number of arguments
            
        Returns:
            True if valid, False otherwise
        
        Behavior:
            - If strict_mode=False: Always returns True (bypass validation)
            - If strict_mode=True: Validates against whitelist
        """
        # SOFT MODE: Bypass validation if strict_mode is disabled
        if not self.strict_mode:
            return True
        
        # STRICT MODE: Enforce whitelist validation
        if name not in self.predicates:
            logger.debug(
                f"Predicate '{name}' not in ontology whitelist. "
                f"Available: {list(self.predicates.keys())}"
            )
            return False
        
        expected_arity = self.predicates[name]["arity"]
        if arity != expected_arity:
            logger.debug(
                f"Predicate '{name}' arity mismatch: expected {expected_arity}, got {arity}"
            )
            return False
        
        return True
    
    def get_predicate_info(self, name: str) -> Optional[Dict]:
        """
        Get predicate information
        
        Args:
            name: Predicate name
            
        Returns:
            Dictionary with arity and term_types, or None if not found
        """
        return self.predicates.get(name)
    
    def get_expected_term_types(self, predicate: str) -> Optional[List[str]]:
        """
        Get expected term types for predicate
        
        Args:
            predicate: Predicate name
            
        Returns:
            List of expected term types, or None if predicate not found
        """
        info = self.get_predicate_info(predicate)
        return info["term_types"] if info else None
    
    def export_to_file(self, path: str):
        """
        Export ontology to JSON file
        
        Args:
            path: Output file path
        """
        data = {
            "predicates": self.predicates,
            "term_types": list(self.term_types),
            "version": self.version,
            "jurisdiction": self.jurisdiction
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported ontology to {path}")
    
    def merge(self, other: 'LegalOntology'):
        """
        Merge another ontology into this one
        
        Args:
            other: Another LegalOntology instance
        """
        self.predicates.update(other.predicates)
        self.term_types.update(other.term_types)
        logger.info(f"Merged ontology from {other.jurisdiction}")
    
    def __repr__(self) -> str:
        strict_status = "STRICT" if self.strict_mode else "PERMISSIVE"
        return (
            f"LegalOntology(version={self.version}, jurisdiction={self.jurisdiction}, "
            f"predicates={len(self.predicates)}, term_types={len(self.term_types)}, "
            f"mode={strict_status})"
        )


# Global default ontology instance (lazy initialization)
# Note: Uses environment-based strict_mode detection
# Set MAHOUN_ENV=production for strict validation
# Set MAHOUN_ENV=test for permissive validation (default for testing)
_DEFAULT_ONTOLOGY: Optional[LegalOntology] = None


def get_default_ontology() -> LegalOntology:
    """
    Get or create the default ontology instance (lazy initialization)
    
    This ensures MAHOUN_ENV is read at runtime, not at module import time.
    This is CRITICAL for test environments where MAHOUN_ENV is set after import.
    
    Returns:
        Default LegalOntology instance
    """
    global _DEFAULT_ONTOLOGY
    if _DEFAULT_ONTOLOGY is None:
        _DEFAULT_ONTOLOGY = LegalOntology()
        logger.debug(f"Lazy-initialized DEFAULT_ONTOLOGY with strict_mode={_DEFAULT_ONTOLOGY.strict_mode}")
    return _DEFAULT_ONTOLOGY


def reset_default_ontology():
    """
    Reset the default ontology (for testing purposes)
    
    This allows tests to change MAHOUN_ENV and get a fresh ontology instance.
    """
    global _DEFAULT_ONTOLOGY
    _DEFAULT_ONTOLOGY = None
    logger.debug("Reset DEFAULT_ONTOLOGY for re-initialization")


# Backward compatibility: DEFAULT_ONTOLOGY will be lazy-loaded
# Use get_default_ontology() for guaranteed lazy initialization
DEFAULT_ONTOLOGY = None  # Will be set on first access
