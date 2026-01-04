"""
CI check: Ensure uvicorn does NOT autostart during pytest runs.
"""
import subprocess
import sys
import os


def check_uvicorn_in_pytest_logs():
    """
    Run pytest with DISABLE_UVICORN_AUTOSTART=1 and check output for uvicorn startup messages.
    If uvicorn starts, exit with code 1.
    """
    env = os.environ.copy()
    env["DISABLE_UVICORN_AUTOSTART"] = "1"

    # Run pytest
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/tagging/test_prepare_ai_context.py", "-v", "-s"],
        env=env,
        capture_output=True,
        text=True
    )

    output = result.stdout + result.stderr

    # Check for uvicorn startup messages
    forbidden_messages = [
        "Started server process",
        "Uvicorn running",
        "Application startup complete"
    ]

    for msg in forbidden_messages:
        if msg in output:
            print(f"❌ CI CHECK FAILED: Found '{msg}' in pytest output")
            print(f"Output:\n{output}")
            return False

    # Check if DISABLE_UVICORN_AUTOSTART is set
    if env.get("DISABLE_UVICORN_AUTOSTART") != "1":
        print("⚠️  WARNING: DISABLE_UVICORN_AUTOSTART not set in CI environment")
        return False

    print("[OK] CI CHECK PASSED: uvicorn did not autostart during pytest")
    return True


if __name__ == "__main__":
    if check_uvicorn_in_pytest_logs():
        sys.exit(0)
    else:
        sys.exit(1)
