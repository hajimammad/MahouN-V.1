#!/usr/bin/env python3
"""
MAHOUN Advanced Governance Enforcement Scanner
Classification: CRITICAL / CI-GATING
Purpose: Scans the codebase for forbidden architectural patterns, runtime violations, and entropy.
"""

import ast
import re
import sys
from pathlib import Path

# Paths that are allowed to access MAHOUN_ENV directly
ALLOWED_ENV_ACCESS_PATHS = [
    "mahoun/core/environment.py",
    "mahoun/core/governance_lock.py",
    "tests/conftest.py",
    "tests/determinism/conftest.py",
    "api/main.py",
    "scripts/"
]

class ASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.violations = []
        self.has_exception_pass = False

    def visit_ExceptHandler(self, node):
        # Detect "except Exception: pass" or "except: pass"
        if isinstance(node.type, ast.Name) and node.type.id == 'Exception' or node.type is None:
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                self.violations.append({
                    "rule": "Silent Exception Fallback",
                    "line": node.lineno,
                    "message": "Silent fallbacks (except Exception: pass) are completely forbidden in MAHOUN. All exceptions must be logged or raised."
                })
        self.generic_visit(node)

    def visit_Import(self, node):
        self._check_random_import(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self._check_random_import(node)
        self.generic_visit(node)
        
    def _check_random_import(self, node):
        # Avoid random and uuid in core reasoning (determinism breach)
        is_core = "mahoun/core/" in str(self.file_path) or "mahoun/reasoning/" in str(self.file_path)
        is_exempt = any(p in str(self.file_path) for p in ["fortress_validator.py", "governance_lock.py", "uid_generator.py"])
        if is_core and not is_exempt:
            for alias in getattr(node, 'names', []):
                if alias.name in ['random', 'uuid']:
                    self.violations.append({
                        "rule": "Unsafe Random in Reasoning",
                        "line": node.lineno,
                        "message": f"Randomness/UUID ({alias.name}) breaks determinism. Do not use in core reasoning paths."
                    })
            if hasattr(node, 'module') and node.module in ['random', 'uuid']:
                self.violations.append({
                    "rule": "Unsafe Random in Reasoning",
                    "line": node.lineno,
                    "message": f"Randomness/UUID ({node.module}) breaks determinism. Do not use in core reasoning paths."
                })

def check_env_vars(content: str, rel_path: str) -> list:
    violations = []
    # Check for MAHOUN_ENV bypassing canonical environment
    pattern = re.compile(r'os\.getenv\(["\']MAHOUN_ENV["\']\)|os\.environ\.get\(["\']MAHOUN_ENV["\']\)|os\.environ\[["\']MAHOUN_ENV["\']\]')
    
    is_exempt = False
    for exemption in ALLOWED_ENV_ACCESS_PATHS:
        if rel_path.endswith(exemption):
            is_exempt = True
            break
            
    if not is_exempt:
        for match in pattern.finditer(content):
            line_no = content.count('\n', 0, match.start()) + 1
            violations.append({
                "rule": "Direct MAHOUN_ENV Access",
                "line": line_no,
                "message": "Direct access to MAHOUN_ENV is forbidden. Use mahoun.core.environment.get_current_environment() instead."
            })
    return violations

def scan_file(file_path: Path) -> list:
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8")
        rel_path = str(file_path.relative_to(Path.cwd()))
        
        # Regex based checks
        violations.extend(check_env_vars(content, rel_path))
        
        # AST based checks
        tree = ast.parse(content, filename=str(file_path))
        visitor = ASTVisitor(file_path)
        visitor.visit(tree)
        for v in visitor.violations:
            v["file"] = rel_path
            violations.append(v)
            
    except Exception as e:
        print(f"Error reading/parsing {file_path}: {e}", file=sys.stderr)
        
    return violations

def main():
    print("🛡️  MAHOUN Advanced Governance Enforcement Scanner starting...")
    root_dir = Path.cwd()
    all_violations = []
    
    for py_file in root_dir.rglob("*.py"):
        # Skip system, virtualenv, and hidden directories
        skip_dirs = [".venv", "venv", ".pytest_cache", ".kilo", ".qoder", ".claude", ".deepseek"]
        if any(d in py_file.parts for d in skip_dirs):
            continue
            
        # Don't scan tests unless specifically needed
        if "tests/" in str(py_file.relative_to(root_dir)) and py_file.name != "conftest.py":
            continue

        all_violations.extend(scan_file(py_file))
        
    critical_count = len(all_violations)
    
    for v in all_violations:
        print(f"❌ CRITICAL: [{v['rule']}] in {v.get('file', 'unknown')}:{v['line']}")
        print(f"   Reason: {v['message']}")
            
    print("-" * 50)
    print(f"Scan complete. Found {critical_count} critical violations.")
    
    if critical_count > 0:
        print("🚨 GOVERNANCE DRIFT DETECTED. Pipeline failed.", file=sys.stderr)
        sys.exit(1)
    else:
        print("✅ Governance checks passed. No architectural drift detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
