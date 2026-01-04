"""
Pytest plugin for logging test execution time and generating summary.
"""
import pytest
import time
from pathlib import Path


class TestTimingPlugin:
    def __init__(self):
        self.test_times = {}
        self.test_modes = {}

    def pytest_runtest_setup(self, item):
        """Log test setup start time."""
        item._start_time = time.time()

    def pytest_runtest_makereport(self, item, call):
        """Capture test execution time and mode."""
        if call.when == "call":
            elapsed = time.time() - item._start_time
            self.test_times[item.nodeid] = elapsed
            
            # Extract mode from test markers or env
            mode = "SAFE_TEST"  # default
            if "test_mode_test" in item.nodeid or "TEST mode" in item.name:
                mode = "TEST"
            elif "test_mode_prod" in item.nodeid or "PROD mode" in item.name:
                mode = "PROD"
            
            self.test_modes[item.nodeid] = mode

    def pytest_terminal_summary(self, terminalreporter, exitstatus):
        """Print timing summary after tests complete."""
        if self.test_times:
            terminalreporter.write_sep("=", "TEST EXECUTION TIMES")
            
            sorted_tests = sorted(self.test_times.items(), key=lambda x: x[1], reverse=True)
            
            total_time = sum(self.test_times.values())
            test_count = len(self.test_times)
            avg_time = total_time / test_count if test_count > 0 else 0
            
            for nodeid, elapsed in sorted_tests[:20]:  # Top 20 slowest
                mode = self.test_modes.get(nodeid, "UNKNOWN")
                terminalreporter.write(f"  {elapsed:7.2f}s [{mode:10s}] {nodeid}\n")
            
            terminalreporter.write_sep("=", "SUMMARY")
            terminalreporter.write(f"  Total tests: {test_count}\n")
            terminalreporter.write(f"  Total time:  {total_time:.2f}s\n")
            terminalreporter.write(f"  Average:     {avg_time:.2f}s\n")


def pytest_configure(config):
    """Register the plugin."""
    config.pluginmanager.register(TestTimingPlugin(), "test_timing")
