"""
MCP AGENT PROMPT FOR RUNNING COMPREHENSIVE PYTEST SUITE

This prompt is designed for autonomous agents (e.g., GitHub Copilot Agent) to execute a complete
test suite with HTML reporting, timing analysis, and mode coverage verification.

OBJECTIVE:
Execute full pytest suite with comprehensive reporting, timing analysis, and coverage checks
for all tag endpoints across TEST/SAFE_TEST/PROD modes.

STEPS:

1. SETUP ENVIRONMENT
   - Set environment variables:
     DISABLE_UVICORN_AUTOSTART=1
     TEST_WHITELIST_ENABLED=1
     TAGGING_MAX_CONTEXT_CHARS=3000
   
2. RUN COMPREHENSIVE PYTEST
   - Command: pytest tests/ -v --tb=short -p ci.pytest_timing_plugin --html=test_report.html --self-contained-html
   - Plugins:
     * ci.pytest_timing_plugin — logs execution time per test
     * pytest-html — generates HTML report
   - Output files:
     * test_report.html — interactive test results
     * pytest.log — detailed execution log

3. ANALYZE TEST TIMING
   - Parse pytest output for execution times
   - Identify slowest tests (>5s)
   - Log summary:
     * Total execution time
     * Average test time
     * Top 20 slowest tests

4. CHECK TAG ENDPOINT COVERAGE
   - Run: python ci/check_tag_endpoint_coverage.py
   - Validates:
     * tag-pages: TEST, SAFE_TEST, PROD modes
     * tag-tree: TEST, SAFE_TEST, PROD modes
     * tag-space: TEST, SAFE_TEST, PROD modes
     * auto-tag: TEST, SAFE_TEST, PROD modes
   - Output: Coverage report showing gaps (if any)

5. VALIDATE CI GUARDS
   - Run: python ci/check_no_uvicorn_in_tests.py
   - Run: python ci/check_test_whitelist_usage.py
   - Ensure:
     * uvicorn did NOT autostart
     * test whitelist WAS used
     * all guards passed

6. GENERATE SUMMARY REPORT
   - File: docs/reports/test_execution_summary_<TIMESTAMP>.md
   - Contents:
     * Execution date & time
     * Total tests, passed, failed
     * Test execution timing (top 20)
     * Tag endpoint mode coverage
     * CI guard status
     * Recommendations (if any)

7. EXIT CONDITIONS
   - SUCCESS (exit 0): All tests passed + full mode coverage
   - WARNING (exit 0 with message): Tests passed but coverage gaps exist
   - FAILURE (exit 1): Test failures or CI guard violations

EXPECTED OUTPUT FILES:
- test_report.html — Interactive HTML test results
- docs/reports/test_execution_summary_*.md — Execution summary
- pytest.log — Pytest execution log (optional)

COMMANDS TO EXECUTE (in order):

```bash
# 1. Setup environment and run full pytest
export DISABLE_UVICORN_AUTOSTART=1
export TEST_WHITELIST_ENABLED=1
export TAGGING_MAX_CONTEXT_CHARS=3000

pytest tests/ \\
  -v \\
  --tb=short \\
  -p ci.pytest_timing_plugin \\
  --html=test_report.html \\
  --self-contained-html \\
  --log-cli=true \\
  --log-cli-level=INFO \\
  2>&1 | tee pytest.log

# 2. Check tag endpoint mode coverage
python ci/check_tag_endpoint_coverage.py

# 3. Validate CI guards
python ci/check_no_uvicorn_in_tests.py
python ci/check_test_whitelist_usage.py

# 4. Generate summary report
python ci/generate_test_summary.py
```

KEYWORDS FOR AGENT:
- pytest, testing, CI, HTML report, timing analysis, tag endpoints, mode coverage
- Confluence AI, bulk tagging, test automation
- automated agent execution, comprehensive testing

STATUS: Ready for autonomous agent execution
"""

# This is a documentation-only module; can be executed for verbose info
if __name__ == "__main__":
    import sys
    print(__doc__)
    sys.exit(0)
