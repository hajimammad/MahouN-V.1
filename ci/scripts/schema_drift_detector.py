#!/usr/bin/env python3
"""
MAHOUN Schema Drift Detector
==============================

Classification: CRITICAL / CI-GATING
Purpose: Detect schema drift by comparing schema hashes against a baseline.

This script is run in CI to ensure that schema changes are intentional
and tracked. Any untracked schema change fails the pipeline.

Usage:
    python ci/scripts/schema_drift_detector.py [--update-baseline]

Author: MAHOUN Platform Governance Council
Version: 1.0.0
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict


SCHEMA_PATHS = [
    "mahoun/schemas/legal_struct_schema.py",
    "mahoun/schemas/text_schema.py",
    "mahoun/schemas/contracts/core_contracts.py",
    "mahoun/schemas/contracts/graph_contracts.py",
    "mahoun/schemas/contracts/invariants_contracts.py",
    "mahoun/schemas/contracts/ledger_contracts.py",
    "mahoun/schemas/contracts/reasoning_contracts.py",
    "mahoun/schemas/contracts/schemas_contracts.py",
    "mahoun/core/governance/violations.py",
    "mahoun/core/governance/policies.py",
    "mahoun/core/governance/ontology_enforcer.py",
    "mahoun/core/protocols.py",
    "constitution/RedLines.yaml",
    "core_manifest.yaml",
]

BASELINE_PATH = Path("ci/schema_baseline.json")


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    if not file_path.exists():
        return "MISSING"
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def compute_current_hashes(root: Path) -> Dict[str, str]:
    """Compute hashes for all tracked schema files."""
    hashes: Dict[str, str] = {}
    for rel_path in sorted(SCHEMA_PATHS):
        full_path = root / rel_path
        hashes[rel_path] = compute_file_hash(full_path)
    return hashes


def load_baseline(baseline_path: Path) -> Dict[str, str]:
    """Load baseline hashes from file."""
    if not baseline_path.exists():
        return {}
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(baseline_path: Path, hashes: Dict[str, str]) -> None:
    """Save current hashes as new baseline."""
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, sort_keys=True)


def main() -> None:
    update_mode = "--update-baseline" in sys.argv

    print("🔍 MAHOUN Schema Drift Detector starting...")
    root = Path.cwd()
    current = compute_current_hashes(root)
    baseline = load_baseline(root / BASELINE_PATH)

    if update_mode:
        save_baseline(root / BASELINE_PATH, current)
        print(f"✅ Baseline updated: {root / BASELINE_PATH}")
        print(f"   Tracked files: {len(current)}")
        sys.exit(0)

    if not baseline:
        print("⚠️  No baseline found. Run with --update-baseline first.")
        print("   Creating initial baseline...")
        save_baseline(root / BASELINE_PATH, current)
        print(f"✅ Initial baseline created: {root / BASELINE_PATH}")
        sys.exit(0)

    # Compare
    drifted = []
    new_files = []
    removed_files = []

    for path, current_hash in current.items():
        baseline_hash = baseline.get(path)
        if baseline_hash is None:
            new_files.append(path)
        elif current_hash != baseline_hash:
            drifted.append(path)

    for path in baseline:
        if path not in current:
            removed_files.append(path)

    # Report
    if drifted:
        print("❌ SCHEMA DRIFT DETECTED:")
        for path in drifted:
            print(f"   CHANGED: {path}")
            print(f"     baseline: {baseline[path][:16]}...")
            print(f"     current:  {current[path][:16]}...")

    if new_files:
        print("❌ NEW UNTRACKED SCHEMA FILES:")
        for path in new_files:
            print(f"   NEW: {path}")

    if removed_files:
        print("❌ REMOVED SCHEMA FILES:")
        for path in removed_files:
            print(f"   REMOVED: {path}")

    total_issues = len(drifted) + len(new_files) + len(removed_files)

    if total_issues > 0:
        print("-" * 50)
        print(
            f"🚨 SCHEMA DRIFT: {total_issues} issue(s) detected.",
            file=sys.stderr,
        )
        print(
            "   Run 'python ci/scripts/schema_drift_detector.py --update-baseline' "
            "to accept changes.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"✅ Schema integrity verified. {len(current)} files unchanged.")
    sys.exit(0)


if __name__ == "__main__":
    main()
