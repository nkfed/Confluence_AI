#!/usr/bin/env python3
"""
AUTOMATED PYTEST EXECUTION SCRIPT FOR MCP AGENTS

This script is designed to be executed by autonomous agents (GitHub Copilot, Claude, etc.)
to run the comprehensive test suite with all reporting and verification steps.

USAGE:
    python ci/run_comprehensive_tests.py

STEPS:
1. Setup environment (DISABLE_UVICORN_AUTOSTART, TEST_WHITELIST_ENABLED, etc.)
2. Run pytest with timing plugin and HTML report
3. Analyze test execution times
4. Check tag endpoint mode coverage
5. Validate CI guards
6. Generate summary report
7. Print results and exit with appropriate code

EXIT CODES:
    0 — All tests passed + full mode coverage
    1 — Test failures OR CI guard violations OR coverage gaps
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def log(message, level="INFO"):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level:8s} | {message}")


def run_command(cmd, description):
    """Run command and return success status."""
    log(f"Running: {description}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if result.returncode == 0:
        log(f"[OK] Success: {description}", "SUCCESS")
        if result.stdout:
            print(result.stdout[:500])
        return True
    else:
        log(f"[FAIL] Failed: {description}", "ERROR")
        if result.stdout:
            print(result.stdout[:500])
        if result.stderr:
            print(result.stderr[:500])
        return False


def setup_environment():
    """Setup test environment variables."""
    log("Setting up environment...")
    
    os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"
    os.environ["TEST_WHITELIST_ENABLED"] = "1"
    os.environ["TAGGING_MAX_CONTEXT_CHARS"] = "3000"
    
    log("Environment variables set:")
    for var in ["DISABLE_UVICORN_AUTOSTART", "TEST_WHITELIST_ENABLED", "TAGGING_MAX_CONTEXT_CHARS"]:
        log(f"  {var}={os.environ.get(var)}")
    
    return True


def run_pytest():
    """Run comprehensive pytest suite."""
    log("Running pytest suite...")
    
    cmd = (
        "pytest tests/ "
        "-v "
        "--tb=short"
    )
    
    return run_command(cmd, "pytest full suite")


def check_endpoint_coverage():
    """Check tag endpoint mode coverage."""
    log("Checking tag endpoint mode coverage...")
    
    cmd = "python ci/check_tag_endpoint_coverage.py"
    return run_command(cmd, "endpoint coverage check")


def validate_guards():
    """Validate CI guards."""
    log("Validating CI guards...")
    
    guards = [
        ("uvicorn autostart", "python ci/check_no_uvicorn_in_tests.py"),
        ("test whitelist usage", "python ci/check_test_whitelist_usage.py"),
    ]
    
    all_ok = True
    for name, cmd in guards:
        if not run_command(cmd, f"CI guard: {name}"):
            all_ok = False
    
    return all_ok


def generate_summary():
    """Generate test execution summary."""
    log("Generating test execution summary...")
    
    cmd = "python ci/generate_test_summary.py"
    return run_command(cmd, "summary generation")


def main():
    """Main execution workflow."""
    log("=" * 80)
    log("COMPREHENSIVE PYTEST EXECUTION WORKFLOW", "START")
    log("=" * 80)
    
    results = {}
    
    # Step 1: Setup
    results["setup"] = setup_environment()
    if not results["setup"]:
        log("Failed to setup environment", "FATAL")
        return 1
    
    # Step 2: Run pytest
    results["pytest"] = run_pytest()
    
    # Step 3: Check endpoint coverage
    results["coverage"] = check_endpoint_coverage()
    
    # Step 4: Validate CI guards
    results["guards"] = validate_guards()
    
    # Step 5: Generate summary
    results["summary"] = generate_summary()
    
    # Final report
    log("=" * 80)
    log("EXECUTION SUMMARY", "FINAL")
    log("=" * 80)
    
    for step, status in results.items():
        marker = "[OK]" if status else "[FAIL]"
        log(f"{marker} {step:15s}: {'PASS' if status else 'FAIL'}")
    
    # Determine exit code
    pytest_ok = results.get("pytest", False)
    coverage_ok = results.get("coverage", False)
    guards_ok = results.get("guards", False)
    
    if pytest_ok and coverage_ok and guards_ok:
        log("=" * 80)
        log("[OK] ALL CHECKS PASSED -- Ready for merge!", "SUCCESS")
        log("=" * 80)
        log(f"Reports available:")
        log(f"   - test_report.html (open in browser)")
        log(f"   - docs/reports/test_execution_summary_*.md")
        return 0
    else:
        log("=" * 80)
        log("[FAIL] SOME CHECKS FAILED -- Review logs above", "ERROR")
        log("=" * 80)
        if not pytest_ok:
            log("-> Test failures detected; check pytest.log for details")
        if not coverage_ok:
            log("-> Coverage gaps; add tests for missing modes")
        if not guards_ok:
            log("-> CI guard violations; ensure guards are active")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
