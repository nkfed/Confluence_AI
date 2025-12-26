"""
Sections module for documentation organization and whitelist management.
"""
from src.sections.section_detector import detect_section, SECTION_MAP
from src.sections.whitelist import WHITELIST_BY_SECTION

__all__ = [
    "detect_section",
    "SECTION_MAP",
    "WHITELIST_BY_SECTION",
]
