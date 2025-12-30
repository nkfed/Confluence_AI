# Tag-Tree Refactoring - Dynamic Whitelist Architecture

## Overview

This document describes the refactoring of the `/bulk/tag-tree` endpoint to support dynamic whitelist-based tagging per documentation section, replacing the previous policy.txt-based approach.

## Architecture Changes

### New Modules

#### 1. `src/sections/section_detector.py`
- **Purpose**: Detect documentation section by root page ID
- **Key Function**: `detect_section(root_page_id: str) -> str`
- **Section Mapping**:
  - `prompting`: Pages related to prompt engineering
  - `helpdesk`: Helpdesk site documentation
  - `rehab`: Rehabilitation system docs
  - `personal`: Personal documentation
  - `onboarding`: Onboarding materials

#### 2. `src/sections/whitelist.py`
- **Purpose**: Define allowed tags per section
- **Key Constant**: `WHITELIST_BY_SECTION`
- **Key Function**: `get_allowed_labels(section: str) -> List[str]`

#### 3. `src/agents/prompt_builder.py`
- **Purpose**: Build AI prompts with dynamic content
- **Key Methods**:
  - `build_tag_tree_prompt()`: For tag-tree with dynamic whitelist
  - `build_tag_pages_prompt()`: For tag-pages (backward compatible, uses policy.txt)

### Updated Modules

#### 1. `src/agents/summary_agent.py`
- **New Method**: `generate_tags_for_tree(content, allowed_labels, dry_run)`
  - Uses PromptBuilder for dynamic prompt construction
  - Filters AI response to only include allowed_labels
  - Returns filtered tags

#### 2. `src/services/bulk_tagging_service.py`
- **Updated Method**: `tag_tree(root_page_id, dry_run)`
  - Detects section from root_page_id
  - Gets allowed_labels for that section
  - Collects all page_ids in tree (temporary whitelist)
  - For each page:
    - Generates tags using allowed_labels filter
    - Compares with current labels
    - Updates labels (if not dry_run)

## Workflow

### /bulk/tag-tree/{root_page_id}

```
1. Detect Section
   ├─ section_detector.detect_section(root_page_id)
   └─ Returns: "prompting" | "helpdesk" | "rehab" | "personal" | "onboarding"

2. Get Allowed Labels
   ├─ whitelist.get_allowed_labels(section)
   └─ Returns: List[str] of allowed tags for this section

3. Collect Tree
   ├─ BulkTaggingService._collect_all_children(root_page_id)
   └─ Returns: List[str] of all page_ids in tree (TEMP_ALLOWED_PAGES)

4. For Each Page:
   ├─ Fetch page content
   ├─ SummaryAgent.generate_tags_for_tree(content, allowed_labels, dry_run)
   │  ├─ PromptBuilder.build_tag_tree_prompt(content, allowed_labels, dry_run)
   │  ├─ AI generates tags
   │  └─ Filter tags: only return those in allowed_labels
   ├─ Get current labels
   ├─ Calculate diff (labels_to_add)
   └─ If not dry_run: ConfluenceClient.update_labels(page_id, add, remove)

5. Return Results
   └─ Summary with section, allowed_labels, success/error counts, details
```

### /bulk/tag-pages (Unchanged)

```
1. Parse page_ids from request
2. Filter by ALLOWED_TAGGING_PAGES setting
3. For each allowed page:
   ├─ Fetch content
   ├─ Generate tags using policy.txt (old method)
   └─ Update labels
4. Return results
```

## Prompt Structure

### Tag-Tree Prompt (New)
```
[base.txt]

ALLOWED TAGS:
- doc-tech
- domain-helpdesk-site
- kb-overview
[... dynamic list ...]

[test.txt or prod.txt]

CONTENT TO ANALYZE:
[page content]

Return ONLY JSON with selected tags.
```

### Tag-Pages Prompt (Unchanged)
```
[base.txt]

[policy.txt]

[test.txt or prod.txt]

CONTENT TO ANALYZE:
[page content]

Return ONLY JSON with selected tags.
```

## Logging

All operations log:
- Section detection: `[tag-tree] Detected section: {section}`
- Allowed labels: `[tag-tree] Allowed labels for section '{section}': {allowed_labels}`
- Tree collection: `[tag-tree] Collected {count} pages in tree (TEMP_ALLOWED_PAGES)`
- AI suggestions: `[tag-tree] AI suggested {count} tags: {tags}`
- Filtering: `[tag-tree] Filtered to {count} allowed tags: {filtered_tags}`
- Removals: `[tag-tree] Removed {count} disallowed tags: {removed_tags}`
- Updates: `[tag-tree] Successfully updated labels for page {page_id}`
- Dry-run: `[tag-tree] [DRY-RUN] Would update labels for {page_id}`

## Testing

### Unit Tests

#### `tests/test_sections.py`
- `TestSectionDetector`: Tests for section detection logic
- `TestWhitelist`: Tests for whitelist retrieval

#### `tests/test_prompt_builder.py`
- `TestPromptBuilder`: Tests for prompt construction
- `TestSummaryAgentTagging`: Tests for tag filtering logic

### Test Coverage
- Section detection with valid/invalid page IDs
- Whitelist retrieval for all sections
- Prompt structure validation
- Tag filtering (allowed vs disallowed)
- Empty allowed_labels handling
- AI response parsing

## Backward Compatibility

### Preserved Functionality
- `/bulk/tag-pages` endpoint unchanged
- TaggingAgent unchanged
- SummaryAgent existing methods unchanged
- PromptBuilder provides separate method for tag-pages

### No Breaking Changes
- Existing tagging workflows continue to work
- Policy.txt still used for tag-pages
- All existing tests pass

## Example Usage

### Tag-Tree Request
```bash
POST /bulk/tag-tree/19713687690?dry_run=true
```

### Response
```json
{
  "status": "completed",
  "section": "prompting",
  "allowed_labels": [
    "doc-prompt-template",
    "doc-tech",
    "domain-helpdesk-site",
    "tool-rovo-agent",
    "doc-architecture",
    "domain-ai-integration"
  ],
  "root_page_id": "19713687690",
  "total": 15,
  "processed": 15,
  "success": 14,
  "errors": 1,
  "dry_run": true,
  "details": [...]
}
```

## Files Modified

### New Files
- `src/sections/__init__.py`
- `src/sections/section_detector.py`
- `src/sections/whitelist.py`
- `src/agents/prompt_builder.py`
- `tests/test_sections.py`
- `tests/test_prompt_builder.py`

### Modified Files
- `src/agents/summary_agent.py`: Added `generate_tags_for_tree()` method
- `src/services/bulk_tagging_service.py`: Refactored `tag_tree()` method

### Unchanged Files
- `src/agents/tagging_agent.py`
- `src/api/routers/bulk.py` (endpoint definitions unchanged)
- `src/prompts/tagging/policy.txt` (still used by tag-pages)

## Migration Notes

No migration required. The refactoring is fully backward compatible.

## Future Enhancements

1. **Dynamic Section Detection**: Auto-detect sections by analyzing page content
2. **Configurable Whitelists**: Store whitelists in database instead of code
3. **Section Inheritance**: Support hierarchical section relationships
4. **Label Removal Logic**: Add smart label removal based on section changes
5. **Batch Processing**: Optimize tree processing with parallel execution
