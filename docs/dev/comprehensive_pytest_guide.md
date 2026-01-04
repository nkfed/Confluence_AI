# Comprehensive Pytest Execution Guide

## Overview

Run full test suite with:
- Test execution timing per test
- HTML report generation
- Tag endpoint mode coverage verification
- CI guard validation
- Summary report generation

## Quick Start

### 1. Run Full Suite with HTML Report
```bash
export DISABLE_UVICORN_AUTOSTART=1
export TEST_WHITELIST_ENABLED=1
export TAGGING_MAX_CONTEXT_CHARS=3000

pytest tests/ -v --tb=short
```

**Output:**
- `test_report.html` — Interactive report
- Console timing summary

### 2. Check Tag Endpoint Coverage
```bash
python ci/check_tag_endpoint_coverage.py
```

Shows which test modes (TEST/SAFE_TEST/PROD) are covered per endpoint.

### 3. Validate CI Guards
```bash
python ci/check_no_uvicorn_in_tests.py
python ci/check_test_whitelist_usage.py
```

Ensures uvicorn doesn't autostart and test whitelist is used.

### 4. Generate Summary Report
```bash
python ci/generate_test_summary.py
```

Creates comprehensive report in `docs/reports/test_execution_summary_*.md`

## MCP Agent Execution

For autonomous agent (e.g., GitHub Copilot):

```bash
python ci/mcp_pytest_agent_prompt.py
```

This shows the full prompt designed for automated execution.

## Test Markers

Tag tests with mode/endpoint markers for better organization:

```python
@pytest.mark.mode_test
@pytest.mark.tag_pages
async def test_tag_pages_in_test_mode():
    ...

@pytest.mark.mode_safe_test
@pytest.mark.tag_tree
async def test_tag_tree_in_safe_test_mode():
    ...

@pytest.mark.mode_prod
@pytest.mark.tag_space
async def test_tag_space_in_prod_mode():
    ...
```

### Run by Mode
```bash
pytest -m mode_test          # Only TEST mode tests
pytest -m mode_safe_test     # Only SAFE_TEST mode tests
pytest -m mode_prod          # Only PROD mode tests
```

### Run by Endpoint
```bash
pytest -m tag_pages          # Only tag-pages tests
pytest -m tag_tree           # Only tag-tree tests
pytest -m tag_space          # Only tag-space tests
```

## CI Pipeline Integration

```bash
#!/bin/bash
set -e

# Setup
export DISABLE_UVICORN_AUTOSTART=1
export TEST_WHITELIST_ENABLED=1
export TAGGING_MAX_CONTEXT_CHARS=3000

# Run tests
pytest tests/ -v --tb=short

# Check coverage
python ci/check_tag_endpoint_coverage.py

# Validate guards
python ci/check_no_uvicorn_in_tests.py
python ci/check_test_whitelist_usage.py

# Generate report
python ci/generate_test_summary.py

echo "✅ All checks passed!"
```

## Plugins Loaded

- `pytest-asyncio` — Async test support
- `pytest-html` — HTML report generation
- `ci.pytest_timing_plugin` — Execution timing per test

## Expected Output Files

- `test_report.html` — Interactive test results (auto-opened in browser after run)
- `docs/reports/test_execution_summary_*.md` — Execution summary with trends
- Console: Test count, timings, mode coverage summary

## Performance Targets

| Metric | Target | Note |
|--------|--------|------|
| Avg test time | < 2s | Unit tests only |
| Max test time | < 30s | Integration tests allowed |
| Total suite | < 5min | Full run on CI |
| HTML report size | < 10MB | Self-contained |

## Troubleshooting

### uvicorn starts during tests
- Check `DISABLE_UVICORN_AUTOSTART=1` is set
- Run: `python ci/check_no_uvicorn_in_tests.py`

### Tests use production whitelist
- Check `TEST_WHITELIST_ENABLED=1` is set
- Run: `python ci/check_test_whitelist_usage.py`

### Missing HTML report
- Install: `pip install pytest-html`
- Check pytest.ini has `--html` flag

### Slow tests
- Review timing output: slowest tests listed first
- Consider marking slow tests: `@pytest.mark.slow`
- Run only fast: `pytest -m "not slow"`
