"""
Whitelist definitions for allowed tags per documentation section.
"""

# Whitelist of allowed tags per documentation section
WHITELIST_BY_SECTION = {
    "prompting": [
        "doc-prompt-template",
        "doc-tech",
        "domain-helpdesk-site",
        "tool-rovo-agent",
        "doc-architecture",
        "domain-ai-integration"
    ],
    "helpdesk": [
        "doc-tech",
        "domain-helpdesk-site",
        "kb-overview",
        "kb-canonical",
        "kb-components",
        "doc-architecture",
        "doc-design",
        "domain-ai-integration"
    ],
    "rehab": [
        "domain-rehab-2-0",
        "domain-dzr",
        "kb-entities-hierarchy",
        "doc-business",
        "doc-tech",
        "kb-overview"
    ],
    "personal": [
        "doc-personal"
    ],
    "onboarding": [
        "doc-onboarding",
        "kb-overview"
    ],
    "tagging-policy": [
        "doc-process",
        "doc-knowledge-base",
        "kb-overview",
        "kb-canonical"
    ]
}


def get_allowed_labels(section: str) -> list[str]:
    """
    Get allowed labels for a specific section.
    
    Args:
        section: Section name
        
    Returns:
        List of allowed labels for the section
        
    Raises:
        KeyError: If section doesn't exist in whitelist
    """
    if section not in WHITELIST_BY_SECTION:
        raise KeyError(f"Section '{section}' not found in WHITELIST_BY_SECTION")
    
    return WHITELIST_BY_SECTION[section]


def is_label_allowed(label: str, section: str) -> bool:
    """
    Check if a label is allowed for a specific section.
    
    Args:
        label: Label to check
        section: Section name
        
    Returns:
        True if label is allowed, False otherwise
    """
    try:
        allowed = get_allowed_labels(section)
        return label in allowed
    except KeyError:
        return False


def get_default_labels() -> list[str]:
    """
    Get default labels for unknown sections (PROD mode fallback).
    
    Returns comprehensive set of common labels that can be used
    when section is not identified.
    
    Returns:
        List of default allowed labels
    """
    return [
        # Document types
        "doc-tech",
        "doc-business",
        "doc-process",
        "doc-architecture",
        "doc-design",
        "doc-prompt-template",
        "doc-knowledge-base",
        "doc-onboarding",
        
        # Domains
        "domain-helpdesk-site",
        "domain-ai-integration",
        "domain-rehab-2-0",
        "domain-dzr",
        
        # Knowledge base roles
        "kb-overview",
        "kb-canonical",
        "kb-components",
        "kb-entities-hierarchy",
        
        # Tools
        "tool-rovo-agent"
    ]
