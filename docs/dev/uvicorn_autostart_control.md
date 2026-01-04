# Uvicorn Autostart Control

## Overview

Ensures uvicorn server NEVER autostarts during pytest execution, preventing test interference.

## How It Works

1. **Guard in run_server.py**
   - Check `DISABLE_UVICORN_AUTOSTART=1` env var
   - Only start uvicorn if not set (production) or unset (development)

2. **conftest.py Protection**
   - Set `os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"` at import time
   - Applies to all pytest sessions

3. **CI Verification**
   - `ci/check_no_uvicorn_in_tests.py` runs pytest and validates no uvicorn startup
   - Checks for forbidden messages: "Started server process", "Uvicorn running", "Application startup complete"

## Usage

### Development (no tests)
```bash
# Uvicorn starts normally
python run_server.py
```

### Running tests
```bash
# Uvicorn guard is active via conftest.py
pytest tests/ -v
```

### Manual test run with explicit guard
```bash
DISABLE_UVICORN_AUTOSTART=1 pytest tests/ -v
```

### CI Pipeline
```bash
DISABLE_UVICORN_AUTOSTART=1 pytest -v
python ci/check_no_uvicorn_in_tests.py
```

## Why This Matters

- Prevents port conflicts (test suite vs. dev server on same port)
- Isolates tests from server lifecycle
- Allows test discovery without side effects
- Reduces startup time during test runs
