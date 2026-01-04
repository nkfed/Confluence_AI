# Documentation structure v4.0 proposal

Generated: 2026-01-02
Sources: audits 01–05 (tree, duplicates, terms, broken links, deprecated files), INDEX/README.

## Proposed folder tree (docs/)
```
docs/
├── README.md                  # entry-point quick map + onboarding
├── INDEX.md                   # canonical index, no broken links
├── AUDIT_REPORT_2026-01.md    # historical audit
├── architecture/
│   ├── agent-modes-overview.md
│   ├── agent-mode-router.md
│   ├── agent-mode-lifecycle.md
│   ├── agent-mode-errors.md
│   ├── AI_ROUTER_INTEGRATION.md
│   ├── AI_ROUTING_MODES.md
│   ├── AI_ROUTING_INSPECTOR.md
│   ├── MULTI_AI_ARCHITECTURE.md
│   └── (remove or archive) UNIFIED_BULK_ARCHITECTURE.md
├── bulk-operations/
│   ├── TAG_PAGES_ENDPOINT.md           # canonical
│   ├── TAG_TREE_ENDPOINT.md            # canonical
│   ├── TAG_SPACE_ENDPOINT.md (create only if endpoint exists; else drop)
│   ├── DRY_RUN_RESPONSE_STANDARD.md    # canonical dry-run schema
│   ├── RESET_TAGS_ROOT_ID.md           # canonical reset guide
│   ├── TAG_TREE_WHITELIST.md
│   ├── TAG_SPACE_WHITELIST_ALWAYS_ON.md
│   ├── TAG_SPACE_EMPTY_BODY_FIX.md
│   ├── EXPAND_PARAMETER_FIX.md
│   ├── TAG_PAGES_WHITELIST.md
│   └── (remove/merge) Quickstarts/Summaries/legacy listed below
├── guides/
│   ├── PROMPT_ENGINEERING.md
│   ├── TESTING_GUIDELINES.md
│   └── VSCODE_OPTIMIZATION.md
├── logging/
│   ├── logging_guide.md
│   ├── AI_COST_TRACKING.md
│   ├── AI_ERROR_HANDLING.md
│   ├── AI_LOGGING_LAYER.md
│   └── AI_RATE_LIMITING.md
├── spaces/
│   ├── SPACES_METADATA_FILTERING.md    # canonical
│   └── (remove/merge) SPACES_METADATA_SUMMARY.md, SPACES_FILTERING_FIX.md, SPACES_NORMALIZATION_FIX.md
├── whitelist/
│   ├── WHITELIST_MECHANISM.md          # canonical
│   ├── WHITELIST_QUICK_START.md        # minimal quickstart pointing to mechanism
│   └── WHITELIST_RECURSIVE_FIX.md
├── archive/                           # move deprecated/legacy here
│   ├── agent-mode-system_SPLIT.md
│   ├── UNIFIED_BULK_ARCHITECTURE.md
│   ├── RESET_TAGS_ROOT_ID_SUMMARY.md
│   ├── TAG_PAGES_INTEGRATION_SUMMARY.md
│   ├── BULK_TAGGING_FILES.md
│   ├── BULK_TAGGING_IMPLEMENTATION.md
│   ├── BULK_TAGGING_QUICKSTART.md (if merged)
│   ├── TAG_PAGES_QUICKSTART.md (if merged)
│   ├── SPACES_METADATA_SUMMARY.md
│   ├── SPACES_FILTERING_FIX.md
│   ├── SPACES_NORMALIZATION_FIX.md
│   ├── WHITELIST_ENV_REMOVAL.md
│   └── BULK_ENDPOINTS_AUDIT_REPORT_DEPRECATED.md
└── audit/
    ├── 01_docs_tree.md
    ├── 02_duplicates_analysis.md
    ├── 03_terms_consistency.md
    ├── 04_broken_links.md
    ├── 05_deprecated_files.md
    └── 06_structure_v4.md (this doc)
```

## Canonical files (keep & maintain)
- [architecture/agent-modes-overview.md](architecture/agent-modes-overview.md)
- [architecture/agent-mode-router.md](architecture/agent-mode-router.md)
- [architecture/agent-mode-lifecycle.md](architecture/agent-mode-lifecycle.md)
- [architecture/agent-mode-errors.md](architecture/agent-mode-errors.md)
- [architecture/MULTI_AI_ARCHITECTURE.md](architecture/MULTI_AI_ARCHITECTURE.md)
- [architecture/AI_ROUTER_INTEGRATION.md](architecture/AI_ROUTER_INTEGRATION.md)
- [architecture/AI_ROUTING_MODES.md](architecture/AI_ROUTING_MODES.md)
- [architecture/AI_ROUTING_INSPECTOR.md](architecture/AI_ROUTING_INSPECTOR.md)
- [bulk-operations/TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md)
- [bulk-operations/TAG_TREE_ENDPOINT.md](bulk-operations/TAG_TREE_ENDPOINT.md)
- [bulk-operations/DRY_RUN_RESPONSE_STANDARD.md](bulk-operations/DRY_RUN_RESPONSE_STANDARD.md)
- [bulk-operations/RESET_TAGS_ROOT_ID.md](bulk-operations/RESET_TAGS_ROOT_ID.md)
- [bulk-operations/TAG_TREE_WHITELIST.md](bulk-operations/TAG_TREE_WHITELIST.md)
- [bulk-operations/TAG_SPACE_WHITELIST_ALWAYS_ON.md](bulk-operations/TAG_SPACE_WHITELIST_ALWAYS_ON.md)
- [bulk-operations/TAG_SPACE_EMPTY_BODY_FIX.md](bulk-operations/TAG_SPACE_EMPTY_BODY_FIX.md)
- [bulk-operations/EXPAND_PARAMETER_FIX.md](bulk-operations/EXPAND_PARAMETER_FIX.md)
- [bulk-operations/TAG_PAGES_WHITELIST.md](bulk-operations/TAG_PAGES_WHITELIST.md)
- [guides/PROMPT_ENGINEERING.md](guides/PROMPT_ENGINEERING.md)
- [guides/TESTING_GUIDELINES.md](guides/TESTING_GUIDELINES.md)
- [guides/VSCODE_OPTIMIZATION.md](guides/VSCODE_OPTIMIZATION.md)
- [logging/logging_guide.md](logging/logging_guide.md)
- [logging/AI_COST_TRACKING.md](logging/AI_COST_TRACKING.md)
- [logging/AI_ERROR_HANDLING.md](logging/AI_ERROR_HANDLING.md)
- [logging/AI_LOGGING_LAYER.md](logging/AI_LOGGING_LAYER.md)
- [logging/AI_RATE_LIMITING.md](logging/AI_RATE_LIMITING.md)
- [spaces/SPACES_METADATA_FILTERING.md](spaces/SPACES_METADATA_FILTERING.md)
- [whitelist/WHITELIST_MECHANISM.md](whitelist/WHITELIST_MECHANISM.md)
- [whitelist/WHITELIST_QUICK_START.md](whitelist/WHITELIST_QUICK_START.md) (minimal)
- [whitelist/WHITELIST_RECURSIVE_FIX.md](whitelist/WHITELIST_RECURSIVE_FIX.md)

## Files to merge/consolidate
- Merge [bulk-operations/RESET_TAGS_ROOT_ID_SUMMARY.md](bulk-operations/RESET_TAGS_ROOT_ID_SUMMARY.md) into [bulk-operations/RESET_TAGS_ROOT_ID.md](bulk-operations/RESET_TAGS_ROOT_ID.md) (summary/changelog section), then archive summary.
- Merge [bulk-operations/TAG_PAGES_QUICKSTART.md](bulk-operations/TAG_PAGES_QUICKSTART.md) into [bulk-operations/TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md) as a quickstart section; archive standalone quickstart.
- Merge [bulk-operations/TAG_PAGES_INTEGRATION_SUMMARY.md](bulk-operations/TAG_PAGES_INTEGRATION_SUMMARY.md) into [bulk-operations/TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md) changelog; archive summary.
- Consolidate bulk tagging cluster: [bulk-operations/BULK_TAGGING_QUICKSTART.md](bulk-operations/BULK_TAGGING_QUICKSTART.md), [bulk-operations/BULK_TAGGING_IMPLEMENTATION.md](bulk-operations/BULK_TAGGING_IMPLEMENTATION.md), [bulk-operations/BULK_TAGGING_FILES.md](bulk-operations/BULK_TAGGING_FILES.md) into one canonical guide (keep under bulk-operations, e.g., BULK_TAGGING_GUIDE.md) and archive the old trio.
- Merge [spaces/SPACES_METADATA_SUMMARY.md](spaces/SPACES_METADATA_SUMMARY.md) into [spaces/SPACES_METADATA_FILTERING.md](spaces/SPACES_METADATA_FILTERING.md) as "What changed"; archive summary.
- Move content of [spaces/SPACES_FILTERING_FIX.md](spaces/SPACES_FILTERING_FIX.md) and [spaces/SPACES_NORMALIZATION_FIX.md](spaces/SPACES_NORMALIZATION_FIX.md) into canonical spaces doc (or changelog section) if still relevant; otherwise archive.

## Files to archive (legacy/obsolete)
- [architecture/agent-mode-system.md](architecture/agent-mode-system.md)
- [architecture/UNIFIED_BULK_ARCHITECTURE.md](architecture/UNIFIED_BULK_ARCHITECTURE.md) (unless rewritten without TAG_SPACE/AUTO_TAG)
- [bulk-operations/RESET_TAGS_ROOT_ID_SUMMARY.md](bulk-operations/RESET_TAGS_ROOT_ID_SUMMARY.md)
- [bulk-operations/TAG_PAGES_INTEGRATION_SUMMARY.md](bulk-operations/TAG_PAGES_INTEGRATION_SUMMARY.md)
- [bulk-operations/BULK_TAGGING_FILES.md](bulk-operations/BULK_TAGGING_FILES.md)
- [bulk-operations/BULK_TAGGING_IMPLEMENTATION.md](bulk-operations/BULK_TAGGING_IMPLEMENTATION.md)
- [bulk-operations/BULK_TAGGING_QUICKSTART.md](bulk-operations/BULK_TAGGING_QUICKSTART.md) (after consolidation)
- [bulk-operations/TAG_PAGES_QUICKSTART.md](bulk-operations/TAG_PAGES_QUICKSTART.md)
- [spaces/SPACES_METADATA_SUMMARY.md](spaces/SPACES_METADATA_SUMMARY.md)
- [spaces/SPACES_FILTERING_FIX.md](spaces/SPACES_FILTERING_FIX.md)
- [spaces/SPACES_NORMALIZATION_FIX.md](spaces/SPACES_NORMALIZATION_FIX.md)
- [whitelist/WHITELIST_ENV_REMOVAL.md](whitelist/WHITELIST_ENV_REMOVAL.md)
- [archive/BULK_ENDPOINTS_AUDIT_REPORT_DEPRECATED.md](archive/BULK_ENDPOINTS_AUDIT_REPORT_DEPRECATED.md) (keep in archive, no references)

## Files to rename (fix paths/links)
- In INDEX/README, fix links to:
  - [bulk-operations/TAG_PAGES_WHITELIST.md](bulk-operations/TAG_PAGES_WHITELIST.md) (currently TAG_pages)
  - [bulk-operations/TAG_PAGES_ENDPOINT.md](bulk-operations/TAG_PAGES_ENDPOINT.md) (ensure consistent case)
  - [logging/logging_guide.md](logging/logging_guide.md) (currently referenced as logging_guide.md at root)
  - [guides/PROMPT_ENGINEERING.md](guides/PROMPT_ENGINEERING.md), [guides/TESTING_GUIDELINES.md](guides/TESTING_GUIDELINES.md), [guides/VSCODE_OPTIMIZATION.md](guides/VSCODE_OPTIMIZATION.md) (README links missing folder)
- Remove references to non-existent TAG_SPACE_ENDPOINT and AUTO_TAG_ENDPOINT unless a real doc is added.

## Recommendations for INDEX.md / README.md
- Remove or archive rows that reference TAG_SPACE_ENDPOINT and AUTO_TAG_ENDPOINT; if tag-space doc is needed, add a real canonical file, else drop from table.
- Update all links to include proper folder prefixes (guides/, logging/, bulk-operations/).
- Mark archived files only in Archive section; avoid listing archived/legacy in main sections.
- Add a "Quickstart vs Canonical" note in INDEX explaining which files are entry-level vs deep-dive.
- Ensure no links to code files under src/tests from docs; prefer describing behavior and linking to canonical API docs.

## Quickstart vs canonical rules
- Quickstart = minimal steps + 1–2 examples; must point to the canonical doc for full API/edge cases; avoid duplicating schema/details.
- Canonical doc = single source of truth for API, parameters, modes, response schema, error handling, and changelog.
- If quickstart exists, keep it co-located as a section inside the canonical doc; avoid standalone quickstart files unless absolutely needed for onboarding.

## Summary/Changelog rules
- Each canonical doc should start with a short "What changed" or "Changelog" section (dates + bullets) summarizing recent updates.
- Avoid separate SUMMARY files; fold summary into the main doc.
- For fixes (e.g., *_FIX.md) either integrate as a changelog entry or archive after the fix is merged and documented.
- Keep release-wide notes in RELEASE_NOTES_*; keep per-endpoint changes in the endpoint doc.

## Action checklist (high level)
1) Fix INDEX.md/README.md broken links and remove non-existent endpoints.
2) Consolidate/merge quickstart & summary files into canonical docs (see merge list).
3) Move listed legacy files to archive/ and update links.
4) Decide fate of TAG_SPACE_ENDPOINT (create real doc or drop all references) and AUTO_TAG references (remove).
5) Rewrite UNIFIED_BULK_ARCHITECTURE.md or archive it due to legacy endpoints.
6) Re-run link checker after moves to ensure no broken links.
