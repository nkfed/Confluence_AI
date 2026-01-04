# Diff — Test Whitelist Integration

## File: conftest.py
```diff
 pytest_plugins = ("pytest_asyncio",)
 
 import os
 import pathlib
 import pytest
 
 # Prevent uvicorn autostart during tests
 os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"
 
 # Set default value for ALLOWED_TAGGING_PAGES
 os.environ.setdefault("ALLOWED_TAGGING_PAGES", "100,101,102")
 
+# Ensure test whitelist is always used
+TEST_WHITELIST_PATH = "tests/fixtures/whitelist_config.json"
+os.environ["TEST_WHITELIST_ENABLED"] = "1"
 
 
 @pytest.fixture(autouse=True)
 def use_test_whitelist_config(monkeypatch):
 	"""Point whitelist config to tests/fixtures/whitelist_config.json for all tests."""
 	base_dir = pathlib.Path(__file__).resolve().parent
-	config_path = base_dir / "tests" / "fixtures" / "whitelist_config.json"
+	config_path = base_dir / TEST_WHITELIST_PATH
+	if not config_path.exists():
+		raise FileNotFoundError(f"Test whitelist not found: {config_path}")
 	monkeypatch.setenv("WHITELIST_CONFIG_PATH", str(config_path))
+	monkeypatch.setenv("TEST_WHITELIST_ENABLED", "1")
```

## File: ci/check_test_whitelist_usage.py (NEW)
- New CI validation script
- Checks TEST_WHITELIST_ENABLED environment variable
- Validates whitelist file exists
- Runs sample pytest to verify integration

## File: docs/dev/test_whitelist_usage.md (NEW)
- User guide for test whitelist
- Explains isolation and ID ranges
- CI integration instructions
