"""
Sections module for documentation organization and whitelist management.
"""
from src.sections.section_detector import detect_section, detect_section_safe, SECTION_MAP
from src.sections.whitelist import WHITELIST_BY_SECTION, get_allowed_labels, get_default_labels

__all__ = [
    "detect_section",
    "detect_section_safe",
    "SECTION_MAP",
    "WHITELIST_BY_SECTION",
    "get_allowed_labels",
    "get_default_labels",
]
