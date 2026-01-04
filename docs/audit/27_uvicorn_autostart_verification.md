# Verification — Uvicorn Autostart Fix (v4.2)

## Checks

- [ ] run_server.py has guard: `if __name__ == "__main__" and os.getenv("DISABLE_UVICORN_AUTOSTART") != "1":`
- [ ] conftest.py sets `os.environ["DISABLE_UVICORN_AUTOSTART"] = "1"` early
- [ ] ci/check_no_uvicorn_in_tests.py exists and validates pytest output
- [ ] Development mode (no guard): `python run_server.py` starts uvicorn normally
- [ ] Test mode: `pytest tests/ -v` does NOT start uvicorn
- [ ] CI mode: `DISABLE_UVICORN_AUTOSTART=1 pytest -v` prevents uvicorn

## Test Execution

```bash
# Verify guard is active
DISABLE_UVICORN_AUTOSTART=1 pytest tests/tagging/test_prepare_ai_context.py -v -s

# Expected: No "Started server process" or "Uvicorn running" in output
# Expected: Tests execute without server interference

# Run CI check
python ci/check_no_uvicorn_in_tests.py

# Expected: "✅ CI CHECK PASSED: uvicorn did not autostart during pytest"
```

## Files
- run_server.py — Guard added
- conftest.py — Guard set at import
- ci/check_no_uvicorn_in_tests.py — Validation script
- docs/dev/uvicorn_autostart_control.md — User guide
- docs/audit/25_*.md, 26_*.md, 27_*.md — Documentation

## CI Pipeline Integration
```yaml
- name: Run tests without uvicorn
  env:
    DISABLE_UVICORN_AUTOSTART: "1"
  run: pytest -v

- name: Validate no uvicorn in tests
  run: python ci/check_no_uvicorn_in_tests.py
```
