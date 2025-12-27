"""
Test metrics logging configuration
"""
import os
import sys

# Set working directory to project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from src.core.logging.logging_config import configure_logging
from src.core.logging.logger import get_logger

# Configure logging
print("Configuring logging...")
configure_logging()

# Get metrics logger
print("Getting metrics logger...")
metrics_logger = get_logger("metrics")

# Test logging
print("Writing to metrics.log...")
metrics_logger.info("test_operation total=10 success=8 errors=2 skipped=5")
metrics_logger.info("tag_tree_operation root_page_id=19700416664 section=helpdesk total_pages=50 success=50 errors=0 skipped=15 dry_run=true")

print("✅ Metrics logged successfully!")
print("Check logs/metrics.log for entries")
