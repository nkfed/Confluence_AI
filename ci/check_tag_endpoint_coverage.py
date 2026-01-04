"""
Generate test coverage summary for tag endpoints.
Checks which test modes (TEST, SAFE_TEST, PROD) are covered.
"""
import subprocess
import sys
import json
import re
from pathlib import Path


def extract_mode_from_test(test_nodeid):
    """Extract mode (TEST/SAFE_TEST/PROD) from test name."""
    if "test_mode_test" in test_nodeid or "TEST mode" in test_nodeid:
        return "TEST"
    elif "test_mode_prod" in test_nodeid or "PROD mode" in test_nodeid:
        return "PROD"
    else:
        return "SAFE_TEST"  # default


def collect_tag_endpoint_tests():
    """Collect all tag-endpoint related tests."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.split("\n")
    tests = {}
    
    # Pattern: tests/path/file.py::test_name
    pattern = re.compile(r"(tests/.*?\.py)::(test_.*)")
    
    for line in lines:
        match = pattern.search(line)
        if match:
            file_path = match.group(1)
            test_name = match.group(2)
            
            # Filter for tag-related tests
            if any(x in test_name.lower() for x in ["tag_pages", "tag_tree", "tag_space", "auto_tag", "tagging"]):
                endpoint = "tag-pages" if "tag_pages" in test_name else \
                          "tag-tree" if "tag_tree" in test_name else \
                          "tag-space" if "tag_space" in test_name else \
                          "auto-tag" if "auto_tag" in test_name else \
                          "tagging"
                
                if endpoint not in tests:
                    tests[endpoint] = {"TEST": [], "SAFE_TEST": [], "PROD": []}
                
                mode = extract_mode_from_test(test_name)
                tests[endpoint][mode].append(test_name)
    
    return tests


def check_mode_coverage():
    """Check if all modes are covered for each endpoint."""
    tests = collect_tag_endpoint_tests()
    
    print("\n" + "=" * 80)
    print("TAG ENDPOINT TEST COVERAGE BY MODE")
    print("=" * 80)
    
    all_modes = {"TEST", "SAFE_TEST", "PROD"}
    coverage_ok = True
    
    for endpoint in sorted(tests.keys()):
        modes = tests[endpoint]
        covered_modes = {m for m in all_modes if modes[m]}
        missing_modes = all_modes - covered_modes
        
        status = "[OK] FULL" if not missing_modes else "[WARN] PARTIAL"
        
        print(f"\n{endpoint:15s} {status}")
        for mode in ["TEST", "SAFE_TEST", "PROD"]:
            count = len(modes[mode])
            marker = "[Y]" if count > 0 else "[N]"
            print(f"  {marker} {mode:10s}: {count:2d} tests")
            if count == 0:
                coverage_ok = False
        
        if modes["TEST"] or modes["SAFE_TEST"] or modes["PROD"]:
            sample = (modes["TEST"] or modes["SAFE_TEST"] or modes["PROD"])[0]
            print(f"      Sample: {sample[:50]}...")
    
    print("\n" + "=" * 80)
    print("COVERAGE SUMMARY")
    print("=" * 80)
    
    total_endpoints = len(tests)
    fully_covered = sum(1 for e in tests if all(tests[e][m] for m in all_modes))
    
    print(f"Endpoints with full coverage:    {fully_covered}/{total_endpoints}")
    print(f"All modes covered:               {'[OK] YES' if coverage_ok else '[FAIL] NO'}")
    
    if not coverage_ok:
        print("\n[WARN] WARNING: Some endpoints lack complete mode coverage")
        print("Add tests for missing modes to ensure consistent behavior across TEST/SAFE_TEST/PROD")
    
    return coverage_ok


if __name__ == "__main__":
    ok = check_mode_coverage()
    sys.exit(0 if ok else 1)
