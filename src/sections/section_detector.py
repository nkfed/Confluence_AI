"""
Section detector for determining documentation section by root page ID.
"""
from typing import Optional

# Mapping of documentation sections to their root page IDs
SECTION_MAP = {
    "prompting": ["19713687690", "19712901293"],
    "helpdesk": ["19700089019", "19700416664"],
    "rehab": ["19711229963"],
    "personal": ["19699862097"],
    "onboarding": ["19701137575"],
    "tagging-policy": [
        "19716112385",  # Tag table/policy page
        "19716145153",  # Tag reference page
        "19713622141",  # Tag dictionary page
        "19713622133",  # Tag policy page
        "19713687690",  # Prompting root (also in tagging-policy for debugging)
        "19712868463"   # Additional tag policy page
    ]
}


def detect_section(root_page_id: str) -> str:
    """
    Detect documentation section by root page ID.
    
    Args:
        root_page_id: The root page ID to detect section for
        
    Returns:
        Section name (e.g., "prompting", "helpdesk", "rehab", "personal", "onboarding")
        
    Raises:
        ValueError: If root_page_id is not found in any section
        
    Example:
        >>> detect_section("19713687690")
        'prompting'
        >>> detect_section("19700089019")
        'helpdesk'
    """
    for section, page_ids in SECTION_MAP.items():
        if root_page_id in page_ids:
            return section
    
    raise ValueError(
        f"Unknown root_page_id '{root_page_id}' for tag-tree operation. "
        f"Valid IDs: {[pid for ids in SECTION_MAP.values() for pid in ids]}"
    )


def detect_section_safe(root_page_id: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely detect documentation section by root page ID.
    
    Returns default if root_page_id is not found (useful for PROD mode).
    
    Args:
        root_page_id: The root page ID to detect section for
        default: Default section to return if not found (e.g., "unknown")
        
    Returns:
        Section name or default value
        
    Example:
        >>> detect_section_safe("19713687690")
        'prompting'
        >>> detect_section_safe("99999999999", default="unknown")
        'unknown'
    """
    try:
        return detect_section(root_page_id)
    except ValueError:
        return default


def get_all_section_page_ids() -> list[str]:
    """
    Get all page IDs from all sections.
    
    Returns:
        List of all page IDs across all sections
    """
    return [page_id for page_ids in SECTION_MAP.values() for page_id in page_ids]


def get_section_page_ids(section: str) -> Optional[list[str]]:
    """
    Get page IDs for a specific section.
    
    Args:
        section: Section name
        
    Returns:
        List of page IDs for the section, or None if section doesn't exist
    """
    return SECTION_MAP.get(section)
