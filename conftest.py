pytest_plugins = ("pytest_asyncio",)

import os
import pathlib
import pytest


# Set default value for ALLOWED_TAGGING_PAGES in the test configuration
os.environ.setdefault("ALLOWED_TAGGING_PAGES", "100,101,102")


@pytest.fixture(autouse=True)
def use_test_whitelist_config(monkeypatch):
	"""Point whitelist config to tests/fixtures/whitelist_config.json for all tests."""
	base_dir = pathlib.Path(__file__).resolve().parent
	config_path = base_dir / "tests" / "fixtures" / "whitelist_config.json"
	monkeypatch.setenv("WHITELIST_CONFIG_PATH", str(config_path))
