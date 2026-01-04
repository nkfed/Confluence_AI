# Diff — Uvicorn Autostart Fix

## File: run_server.py
```diff
 import sys
 import os
 import uvicorn
 from settings import settings
 
 BASE_DIR = os.path.dirname(os.path.abspath(__file__))
 if BASE_DIR not in sys.path:
     sys.path.insert(0, BASE_DIR)
 
+# Prevent uvicorn autostart during pytest/testing
-if __name__ == "__main__":
+if __name__ == "__main__" and os.getenv("DISABLE_UVICORN_AUTOSTART") != "1":
     print("Starting FastAPI server...")
     uvicorn.run(...)
```

## File: conftest.py
```diff
 pytest_plugins = ("pytest_asyncio",)
 
 import os
 import pathlib
 import pytest
 
+# Prevent uvicorn autostart during tests
+os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"
+
 # Set default value for ALLOWED_TAGGING_PAGES
 os.environ.setdefault("ALLOWED_TAGGING_PAGES", "100,101,102")
```

## File: ci/check_no_uvicorn_in_tests.py (NEW)
- New validation script
- Checks for uvicorn startup in pytest output
- Validates DISABLE_UVICORN_AUTOSTART is set
