#!/usr/bin/env python3
"""
Gate 0b: Secrets Scanner
=========================
Detects potential secrets, keys, and sensitive data in code.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

# Paths to scan (everything except excluded)
EXCLUDE_PATTERNS = {
    '__pycache__',
    '.pytest_cache',
    'venv',
    'venv.old.conda',
    '.git',
    'node_modules',
    'dist',
    'build',
    '*.pyc',
    'test_',
    'tests/',
}

# Secret patterns to detect
SECRET_PATTERNS = [
    # Pattern, Description, Severity (1=low, 2=medium, 3=critical)
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID', 3),
    (r'aws_secret_access_key\s*=\s*["\'][^"\']{20,}["\']', 'AWS Secret Access Key', 3),
    (r'-----BEGIN (?:RSA |DSA )?PRIVATE KEY-----', 'Private Key', 3),
    (r'(?i)password\s*=\s*["\'][^"\']{8,}["\']', 'Hardcoded password', 3),
    (r'(?i)api_key\s*=\s*["\'][^"\']{20,}["\']', 'API Key', 3),
    (r'(?i)secret_key\s*=\s*["\'][^"\']{20,}["\']', 'Secret Key', 3),
    (r'(?i)token\s*=\s*["\'][^"\']{20,}["\']', 'Authentication Token', 3),
    (r'sk_live_[0-9a-zA-Z]{24,}', 'Stripe Live Secret Key', 3),
    (r'sk_test_[0-9a-zA-Z]{24,}', 'Stripe Test Secret Key', 2),
    (r'ghp_[0-9a-zA-Z]{36}', 'GitHub Personal Access Token', 3),
    (r'gho_[0-9a-zA-Z]{36}', 'GitHub OAuth Token', 3),
    (r'glpat-[0-9a-zA-Z_\-]{20,}', 'GitLab Personal Access Token', 3),
    (r'AIza[0-9A-Za-z_\-]{35}', 'Google API Key', 2),
    (r'ya29\.[0-9A-Za-z_\-]{68,}', 'Google OAuth Token', 3),
    (r'[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com', 'Google OAuth Client ID', 2),
    (r'xox[baprs]-[0-9]{10,}-[0-9]{10,}-[0-9A-Za-z]{24,}', 'Slack Token', 3),
    (r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+', 'Slack Webhook', 2),
]

# Allowed patterns (won't trigger)
ALLOWED_PATTERNS = [
    r'password\s*=\s*["\']YOUR_',  # Placeholder
    r'password\s*=\s*["\']CHANGEME',  # Placeholder
    r'password\s*=\s*["\']example',  # Example
    r'password\s*=\s*["\']test',  # Test
    r'password\s*=\s*["\']<',  # Template
    r'api_key\s*=\s*["\']YOUR_',  # Placeholder
    r'api_key\s*=\s*["\']sk_test',  # Stripe test (already caught separately)
    r'token\s*=\s*["\']<',  # Template
]


def should_exclude_path(path: Path) -> bool:
    """Check if path should be excluded from scanning."""
    path_str = str(path)
    
    # Exclude by pattern
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    
    return False


def is_allowed_match(line: str) -> bool:
    """Check if the line matches an allowed pattern (false positive)."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def scan_file(file_path: Path) -> List[Tuple[int, str, str, int]]:
    """
    Scan a single file for secrets.
    
    Returns:
        List of (line_number, line_content, pattern_description, severity)
    """
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check each pattern
            for pattern, description, severity in SECRET_PATTERNS:
                if re.search(pattern, line):
                    # Check if it's an allowed pattern
                    if not is_allowed_match(line):
                        # Redact the actual secret in output
                        redacted_line = re.sub(
                            r'["\'][^"\']{8,}["\']',
                            '"***REDACTED***"',
                            line.rstrip()
                        )
                        issues.append((line_num, redacted_line, description, severity))
    
    except Exception:
        # Skip files that can't be read
        return issues
    
    return issues


def scan_directory(base_path: Path) -> Dict[Path, List[Tuple]]:
    """
    Scan directories for secrets.
    
    Returns:
        Dictionary mapping file paths to lists of issues
    """
    all_issues = {}
    
    # Scan Python files
    for py_file in base_path.rglob('*.py'):
        if should_exclude_path(py_file):
            continue
        
        issues = scan_file(py_file)
        if issues:
            all_issues[py_file] = issues
    
    # Scan config files
    for pattern in ['*.json', '*.yml', '*.yaml', '*.env', '*.ini']:
        for config_file in base_path.rglob(pattern):
            if should_exclude_path(config_file):
                continue
            
            issues = scan_file(config_file)
            if issues:
                all_issues[config_file] = issues
    
    return all_issues


def print_results(all_issues: Dict[Path, List[Tuple]]) -> Tuple[int, int, int]:
    """
    Print scan results.
    
    Returns:
        (critical_count, medium_count, low_count)
    """
    critical_count = 0
    medium_count = 0
    low_count = 0
    
    # Sort by severity then by file path
    sorted_issues = sorted(all_issues.items(), key=lambda x: str(x[0]))
    
    for file_path, issues in sorted_issues:
        # Group by severity
        critical = [i for i in issues if i[3] == 3]
        medium = [i for i in issues if i[3] == 2]
        low = [i for i in issues if i[3] == 1]
        
        critical_count += len(critical)
        medium_count += len(medium)
        low_count += len(low)
        
        rel_path = file_path.relative_to(Path.cwd())
        print(f"\n{RED}{rel_path}:{NC}")
        
        # Print critical issues
        for line_num, line, desc, _ in critical:
            print(f"  {RED}🚨 CRITICAL{NC} Line {line_num}: {desc}")
            print(f"    {line.strip()}")
        
        # Print medium issues
        for line_num, line, desc, _ in medium:
            print(f"  {YELLOW}⚠️  MEDIUM{NC} Line {line_num}: {desc}")
            print(f"    {line.strip()}")
        
        # Print low issues
        for line_num, line, desc, _ in low:
            print(f"  {YELLOW}INFO{NC} Line {line_num}: {desc}")
            print(f"    {line.strip()}")
    
    return critical_count, medium_count, low_count


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scan for secrets and sensitive data in code'
    )
    parser.add_argument(
        '--fail-on-medium',
        action='store_true',
        help='Exit with error code for medium severity issues'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔐 Gate 0b: Secrets Scanner")
    print("=" * 60)
    print()
    
    # Get project root
    project_root = Path.cwd()
    
    print("🔍 Scanning for secrets and sensitive data...")
    print()
    
    # Scan
    all_issues = scan_directory(project_root)
    
    if not all_issues:
        print(f"{GREEN}✅ PASSED: No secrets detected{NC}")
        return 0
    
    # Print results
    critical, medium, low = print_results(all_issues)
    
    # Summary
    print()
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    total_files = len(all_issues)
    total_issues = critical + medium + low
    
    print(f"Files with issues: {total_files}")
    print(f"Total issues: {total_issues}")
    
    if critical > 0:
        print(f"  {RED}🚨 Critical: {critical}{NC}")
    if medium > 0:
        color = YELLOW if not args.fail_on_medium else RED
        print(f"  {color}⚠️  Medium: {medium}{NC}")
    if low > 0:
        print(f"  {YELLOW}Info: {low}{NC}")
    
    print()
    
    # Exit code
    if critical > 0:
        print(f"{RED}❌ CRITICAL: Secrets detected!{NC}")
        print()
        print("⚠️  IMMEDIATE ACTIONS REQUIRED:")
        print("1. DO NOT commit these files")
        print("2. Rotate/revoke exposed secrets immediately")
        print("3. Use environment variables or secret managers")
        print("4. Add secrets to .gitignore")
        print()
        return 2  # Critical exit code
    elif medium > 0 and args.fail_on_medium:
        print(f"{RED}❌ FAILED: Medium severity issues found{NC}")
        return 1
    elif medium > 0 or low > 0:
        print(f"{YELLOW}⚠️  WARNING: Potential secrets detected{NC}")
        print("Review these carefully before committing.")
        return 0  # Pass with warning
    else:
        print(f"{GREEN}✅ PASSED: No secrets detected{NC}")
        return 0


if __name__ == '__main__':
    sys.exit(main())






