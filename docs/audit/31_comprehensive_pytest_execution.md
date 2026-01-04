# Comprehensive Pytest Execution (v4.3)

## What Was Added

### 1. Pytest Timing Plugin
- **File:** ci/pytest_timing_plugin.py
- **Function:** Logs execution time for each test
- **Output:** Console summary of top 20 slowest tests
- **Metrics:** Total time, average time, individual timings

### 2. Tag Endpoint Coverage Checker
- **File:** ci/check_tag_endpoint_coverage.py
- **Function:** Validates TEST/SAFE_TEST/PROD mode coverage
- **Output:** Coverage matrix per endpoint
- **Markers:** Identifies coverage gaps

### 3. MCP Agent Prompt
- **File:** ci/mcp_pytest_agent_prompt.py
- **Function:** Defines automated execution steps for agents
- **Steps:** 7-step workflow from setup → summary report
- **Target:** GitHub Copilot Coding Agent, other autonomous agents

### 4. Test Summary Generator
- **File:** ci/generate_test_summary.py
- **Function:** Creates comprehensive execution report
- **Output:** docs/reports/test_execution_summary_*.md
- **Contents:** Tests, timing, coverage, CI guard status

### 5. Enhanced pytest.ini
- **Updates:** Added timing plugin, HTML report, logging
- **Markers:** Added mode/endpoint markers
- **Addopts:** --html, --self-contained-html, --log-cli

### 6. Documentation
- **File:** docs/dev/comprehensive_pytest_guide.md
- **Contents:** Quick start, markers, CI integration, troubleshooting

## Key Features

### Test Timing
```
Top 20 Slowest Tests:
  23.45s [SAFE_TEST] tests/bulk/test_tag_space.py::test_tag_space_integration
   5.67s [TEST     ] tests/tagging/test_prepare_ai_context.py::test_prepare
   ...
Total: 142.3s over 87 tests (avg 1.64s)
```

### Mode Coverage
```
tag-pages        ✅ FULL
  [✓] TEST      : 3 tests
  [✓] SAFE_TEST : 5 tests
  [✓] PROD      : 2 tests

tag-tree         ⚠️  PARTIAL
  [✓] TEST      : 2 tests
  [✓] SAFE_TEST : 4 tests
  [✗] PROD      : 0 tests  ← GAP!
```

### Automated Execution (via Agent)
```bash
# Agent follows 7-step workflow:
1. Setup environment (DISABLE_UVICORN_AUTOSTART, etc.)
2. Run pytest with plugins and HTML output
3. Analyze execution timing
4. Check tag endpoint mode coverage
5. Validate CI guards (uvicorn, whitelist)
6. Generate summary report
7. Exit with appropriate code + message
```

## CI Pipeline Example

```yaml
- name: Run comprehensive tests
  run: |
    export DISABLE_UVICORN_AUTOSTART=1
    export TEST_WHITELIST_ENABLED=1
    pytest tests/ -v --tb=short
    python ci/check_tag_endpoint_coverage.py
    python ci/check_no_uvicorn_in_tests.py
    python ci/check_test_whitelist_usage.py
    python ci/generate_test_summary.py

- name: Upload test report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-report
    path: test_report.html

- name: Upload summary
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-summary
    path: docs/reports/test_execution_summary_*.md
```

## Test Markers for Organization

```python
# Usage in tests
@pytest.mark.mode_test
@pytest.mark.tag_pages
async def test_tag_pages_test_mode():
    ...

# Run by mode
pytest -m mode_test      # All TEST mode tests
pytest -m mode_safe_test # All SAFE_TEST tests
pytest -m mode_prod      # All PROD tests

# Run by endpoint
pytest -m tag_pages      # All tag-pages tests
pytest -m tag_tree       # All tag-tree tests
pytest -m tag_space      # All tag-space tests
```

## Report Outputs

### test_report.html
- Interactive test results
- Pass/fail status
- Execution time per test
- Test parameters
- Stdout/stderr capture
- Stacktraces on failure

### test_execution_summary_*.md
- Execution summary
- Test count (passed/failed)
- Timing analysis (top 20 slowest)
- Tag endpoint mode coverage matrix
- CI guard status (uvicorn, whitelist)
- Recommendations

## Performance Baselines

| Test Type | Target | Notes |
|-----------|--------|-------|
| Unit test | < 1s | Context prep, whitelist, utils |
| Integration | < 10s | Mocked Confluence calls |
| Mode test | < 5s | Each mode (TEST/SAFE_TEST/PROD) |
| Full suite | < 5min | 80+ tests, CI environment |

## Execution Path (Agent)

```
[Agent Start]
    ↓
[Set Environment Vars]
    ↓
[pytest + Plugins] → test_report.html
    ↓
[Check Coverage] → endpoint matrix
    ↓
[Validate Guards] → uvicorn, whitelist status
    ↓
[Generate Report] → docs/reports/test_execution_summary_*.md
    ↓
[Exit + Message] → Agent complete
```
