Title:
docs: Complete documentation refactoring (Stage 2–3)

Description:
This PR completes the full documentation refactoring for the Confluence AI project
(Stage 2–3), based on the audit results from AUDIT_REPORT_2026-01.md.

Key Improvements:
- Fixed 6 broken links (100% resolved)
- Renamed bulk/ → bulk-operations/
- Consolidated prompts/, testing/, vscode/ → guides/
- Split agent-mode-system.md into 4 focused documents:
  agent-modes-overview.md
  agent-mode-router.md
  agent-mode-lifecycle.md
  agent-mode-errors.md
- Added INDEX.md (documentation map)
- Added REPORT_STAGE2-3.md (refactoring report)
- Archived deprecated files

Stats:
- Files changed: 59
- Insertions: +1911
- Deletions: -291
- New files: 6
- Commit: 6d2a713

Updated Structure:
- 8 logical categories
- 48 markdown files
- 0 broken links
- Clean navigation (README + INDEX)

Ready for merge:
CI/CD expected to pass cleanly.
