# Uvicorn Autostart Fix (v4.2)

## Locations Found
- run_server.py — main entry point for uvicorn.run()
- src/main.py — FastAPI app definition (no uvicorn call, just app creation)
- conftest.py — test configuration fixture

## Changes Made

### 1. run_server.py
- Added guard: `if __name__ == "__main__" and os.getenv("DISABLE_UVICORN_AUTOSTART") != "1":`
- Prevents uvicorn.run() if env var set

### 2. conftest.py
- Added: `os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"` at import time
- Applies to all pytest sessions

### 3. ci/check_no_uvicorn_in_tests.py
- New CI guard script
- Runs pytest and validates no uvicorn startup messages
- Exits with code 1 if violations found

## Behavior

### Before
- pytest triggers uvicorn via run_server.py if imported
- Server on port 8000 blocks test execution
- Reloader conflicts with test discovery

### After
- conftest.py sets guard before any imports
- run_server.py respects guard, skips uvicorn.run()
- Tests execute without server interference
