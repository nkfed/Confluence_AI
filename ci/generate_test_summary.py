"""
Generate test execution summary report.
Combines pytest output, timing analysis, and coverage checks.
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


def generate_summary():
    """Generate comprehensive test execution summary."""
    
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path("docs/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = report_dir / f"test_execution_summary_{timestamp}.md"
    
    # Collect information
    lines = []
    lines.append(f"# Test Execution Summary — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Pytest execution
    lines.append("## Pytest Execution\n")
    
    if Path("pytest.log").exists():
        with open("pytest.log", "r") as f:
            content = f.read()
            # Extract summary line
            for line in content.split("\n"):
                if "passed" in line.lower() or "failed" in line.lower():
                    lines.append(f"```\n{line}\n```\n")
                    break
    
    # 2. HTML Report
    lines.append("## Test Report\n")
    if Path("test_report.html").exists():
        lines.append("- **HTML Report:** [test_report.html](../../test_report.html)\n")
    else:
        lines.append("- HTML report not found (run pytest with --html flag)\n")
    
    # 3. Mode Coverage
    lines.append("\n## Tag Endpoint Mode Coverage\n")
    result = subprocess.run(
        [sys.executable, "ci/check_tag_endpoint_coverage.py"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        lines.append("✅ **Full mode coverage achieved**\n")
    else:
        lines.append("⚠️  **Coverage gaps detected** — See details below\n")
    
    lines.append(f"```\n{result.stdout}\n```\n")
    
    # 4. CI Guards
    lines.append("\n## CI Guard Status\n")
    
    guards = [
        ("uvicorn autostart", "ci/check_no_uvicorn_in_tests.py"),
        ("test whitelist usage", "ci/check_test_whitelist_usage.py")
    ]
    
    for guard_name, guard_script in guards:
        result = subprocess.run(
            [sys.executable, guard_script],
            capture_output=True,
            text=True,
            env={**os.environ, "TEST_WHITELIST_ENABLED": "1", "DISABLE_UVICORN_AUTOSTART": "1"}
        )
        
        status = "✅ PASS" if result.returncode == 0 else "❌ FAIL"
        lines.append(f"- {guard_name}: {status}\n")
    
    # 5. Execution environment
    lines.append("\n## Execution Environment\n")
    lines.append(f"- Python: {sys.version.split()[0]}\n")
    lines.append(f"- Timestamp: {datetime.now().isoformat()}\n")
    lines.append(f"- Pytest plugins: pytest-html, pytest-asyncio, pytest_timing_plugin\n")
    
    # 6. Recommendations
    lines.append("\n## Recommendations\n")
    lines.append("1. Review test_report.html for detailed results\n")
    lines.append("2. Address any failing tests before merge\n")
    lines.append("3. Ensure full mode coverage for tag endpoints\n")
    lines.append("4. Monitor execution time trends (target: <5s per test)\n")
    
    # Write report
    with open(report_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"[OK] Summary report generated: {report_file}")
    return str(report_file)


if __name__ == "__main__":
    report_file = generate_summary()
    print(f"Report: {report_file}")
