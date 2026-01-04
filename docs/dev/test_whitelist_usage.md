# Test Whitelist Usage Guide

## Overview

Tests use an isolated whitelist configuration file (`tests/fixtures/whitelist_config.json`) to prevent dependency on production Confluence IDs and ensure reproducible test runs.

## Test Whitelist File

**Location:** [tests/fixtures/whitelist_config.json](../../tests/fixtures/whitelist_config.json)

**Contains:**
- Test space keys: `euheals`, `nkfedba`, `TEST`
- Test page IDs: 100–300 range (safe for testing)
- Root pages marked with `"root": true`
- Child/grandchild relationships for tree-traversal tests

## How It Works

### 1. Automatic via conftest.py
- `use_test_whitelist_config` fixture (autouse=True)
- Sets `WHITELIST_CONFIG_PATH` to test whitelist at pytest startup
- Applies to all tests automatically

### 2. Manual Override (if needed)
```bash
WHITELIST_CONFIG_PATH=tests/fixtures/whitelist_config.json pytest tests/ -v
```

### 3. CI Pipeline
```bash
TEST_WHITELIST_ENABLED=1 \
DISABLE_UVICORN_AUTOSTART=1 \
pytest -v

python ci/check_test_whitelist_usage.py
```

## Test Whitelist Content

### euheals space
- Root: 19493847570 (real Confluence page for integration tests)
- Test nodes: 111, 222, 333, 456, 789 (synthetic IDs)
- Hierarchy roots: 100, 200, 300

### nkfedba space
- Root: 19699862097 (real, whitelisted)
- Children: 19699862098, 19700089019

### TEST space
- Synthetic test page: 123

## Guards

- conftest.py validates whitelist file exists
- CI check ensures TEST_WHITELIST_ENABLED is set
- No production ID hardcoding allowed in tests

## Isolation

Tests never:
- Fetch real Confluence spaces (mocked in fixtures)
- Use production page IDs without explicit test setup
- Depend on Confluence API availability

## Adding New Test IDs

To add a test page:
1. Edit `tests/fixtures/whitelist_config.json`
2. Use ID range 100–9999 (avoid 10000+ which are production ranges)
3. Run `pytest` to verify config loads
4. No need to update code; fixture auto-loads new IDs
