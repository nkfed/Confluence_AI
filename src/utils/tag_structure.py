"""
Unified tag structure helper for all endpoints
"""
from typing import List, Set, Optional
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY, TAG_CATEGORIES


def limit_tags_per_category(tags_dict: dict) -> dict:
    """
    Обмежує кількість тегів на категорію згідно з MAX_TAGS_PER_CATEGORY.
    
    Post-processing функція для жорсткого обмеження результатів AI.
    Навіть якщо AI повернув більше тегів, ця функція обріже їх до максимуму.
    
    Args:
        tags_dict: Словник з категоріями тегів {"doc": [...], "domain": [...], ...}
        
    Returns:
        Новий словник з обмеженою кількістю тегів на категорію
        
    Example:
        >>> tags = {
        ...     "doc": ["doc-tech", "doc-architecture", "doc-business", "doc-process"],
        ...     "domain": ["domain-helpdesk-site"],
        ...     "kb": [],
        ...     "tool": ["tool-rovo-agent", "tool-confluence", "tool-vscode", "tool-pycharm"]
        ... }
        >>> limited = limit_tags_per_category(tags)
        >>> limited["doc"]  # Only first 3 (or MAX_TAGS_PER_CATEGORY)
        ['doc-tech', 'doc-architecture', 'doc-business']
        >>> limited["tool"]  # Only first 3
        ['tool-rovo-agent', 'tool-confluence', 'tool-vscode']
    """
    limited = {}
    
    for category in TAG_CATEGORIES:
        tag_list = tags_dict.get(category, [])
        # Обмежити до MAX_TAGS_PER_CATEGORY перших тегів
        limited[category] = tag_list[:MAX_TAGS_PER_CATEGORY]
    
    return limited


def create_unified_tags_structure(
    proposed: Set[str] | List[str],
    existing: Set[str] | List[str],
    dry_run: bool
) -> dict:
    """
    Create unified tags structure for all endpoints.
    
    Єдина структура тегів:
    {
        "proposed": [...],   # AI-згенеровані теги
        "existing": [...],   # теги, що вже є на сторінці
        "to_add": [...],     # dry-run: що буде додано
        "added": [...]       # реально додано (dry-run → [])
    }
    
    Args:
        proposed: AI-generated tags (set or list)
        existing: Existing tags on page (set or list)
        dry_run: Whether this is a dry-run
        
    Returns:
        Unified tags dictionary
    """
    # Convert to sets for calculation
    proposed_set = set(proposed) if not isinstance(proposed, set) else proposed
    existing_set = set(existing) if not isinstance(existing, set) else existing
    
    # Calculate difference
    to_add_set = proposed_set - existing_set
    to_add_list = sorted(list(to_add_set))  # Sorted for consistency
    
    # Dry-run logic
    if dry_run:
        return {
            "proposed": sorted(list(proposed_set)),
            "existing": sorted(list(existing_set)),
            "to_add": to_add_list,
            "added": []
        }
    else:
        return {
            "proposed": sorted(list(proposed_set)),
            "existing": sorted(list(existing_set)),
            "to_add": [],
            "added": to_add_list
        }


def create_unified_response(
    status: str,
    page_id: str,
    proposed: Set[str] | List[str] = None,
    existing: Set[str] | List[str] = None,
    dry_run: bool = None,
    message: str = None,
    **extra_fields
) -> dict:
    """
    Create unified response structure for all endpoints.
    
    Args:
        status: Response status ("updated", "dry_run", "forbidden", "error")
        page_id: Confluence page ID
        proposed: AI-generated tags (None for forbidden/error)
        existing: Existing tags on page (None for forbidden/error)
        dry_run: Whether this is a dry-run (None for forbidden/error)
        message: Optional error/forbidden message
        **extra_fields: Additional fields (title, skipped, etc.)
        
    Returns:
        Unified response dictionary
    """
    response = {
        "status": status,
        "page_id": page_id
    }
    
    # Add message for forbidden/error
    if message:
        response["message"] = message
    
    # Add tags structure (null for forbidden/error)
    if status in ["forbidden", "error"]:
        response["tags"] = None
    elif proposed is not None and existing is not None and dry_run is not None:
        response["tags"] = create_unified_tags_structure(proposed, existing, dry_run)
    
    # Add extra fields
    response.update(extra_fields)
    
    return response
