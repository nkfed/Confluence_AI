# docs deprecated/legacy files audit

Generated: 2026-01-02
Scope: markdown files under docs/ that look legacy, duplicated, or reference removed endpoints/architecture.

| Файл | Причина застарілості | Рекомендація | Нове місце (якщо архівувати) |
|------|----------------------|--------------|------------------------------|
| architecture/agent-mode-system.md | Монолітний файл, розділений на 4 нові (overview/lifecycle/router/errors); не в INDEX як канон | Позначити як archived, залишити лінк на нові файли | archive/agent-mode-system_SPLIT.md |
| architecture/UNIFIED_BULK_ARCHITECTURE.md | Містить посилання на неіснуючі TAG_SPACE/AUTO_TAG endpoint, описує стару bulk-схему | Переписати без legacy endpoint, або тимчасово перенести в archive | archive/UNIFIED_BULK_ARCHITECTURE.md |
| bulk-operations/RESET_TAGS_ROOT_ID_SUMMARY.md | Дублює основний RESET_TAGS_ROOT_ID.md, не додає нової інформації | Обʼєднати в основний файл і архівувати summary | archive/RESET_TAGS_ROOT_ID_SUMMARY.md |
| bulk-operations/TAG_PAGES_INTEGRATION_SUMMARY.md | Повторює зміни, що вже описані в TAG_PAGES_ENDPOINT.md; посилання на src/tests, яких немає в docs | Перенести зміст у changelog секцію TAG_PAGES_ENDPOINT.md, файл архівувати | archive/TAG_PAGES_INTEGRATION_SUMMARY.md |
| bulk-operations/BULK_TAGGING_FILES.md | Частина кластеру quickstart/implementation/files, дублює опис структури | Злити з BULK_TAGGING_IMPLEMENTATION.md у єдиний гайд; цю версію архівувати | archive/BULK_TAGGING_FILES.md |
| bulk-operations/BULK_TAGGING_IMPLEMENTATION.md | Перетинається з BULK_TAGGING_QUICKSTART.md та BULK_TAGGING_FILES.md | Зробити один актуальний гайд; цю версію або обʼєднати, або в archive після консолідації | archive/BULK_TAGGING_IMPLEMENTATION.md |
| bulk-operations/TAG_PAGES_QUICKSTART.md | Дублює приклади з TAG_PAGES_ENDPOINT.md; лінк на WHITELIST_MECHANISM без шляху | Вбудувати quickstart у TAG_PAGES_ENDPOINT.md або додати правильний шлях; за потреби перенести в archive | archive/TAG_PAGES_QUICKSTART.md |
| spaces/SPACES_METADATA_SUMMARY.md | Короткий summary, дублює SPACES_METADATA_FILTERING.md; лінки на src/tests | Інтегрувати "What changed" у основний файл, summary архівувати | archive/SPACES_METADATA_SUMMARY.md |
| spaces/SPACES_FILTERING_FIX.md | Патч-нотатка про фільтрацію, посилання на src/tests; ймовірно закрита зміна | Перевірити актуальність; якщо зміна вмерджена і задокументована в основних гайдах — архівувати | archive/SPACES_FILTERING_FIX.md |
| spaces/SPACES_NORMALIZATION_FIX.md | Локальний фікс, посилання на src/tests; немає в INDEX | Злити у основний гайд по normalization або архівувати | archive/SPACES_NORMALIZATION_FIX.md |
| whitelist/WHITELIST_ENV_REMOVAL.md | Описує видалені env-перемінні; містить приклади старої поведінки | Перемістити в archive як історичну довідку | archive/WHITELIST_ENV_REMOVAL.md |
| archive/BULK_ENDPOINTS_AUDIT_REPORT_DEPRECATED.md | Документує BulkTagRequest (видалено) та старі bulk endpoints | Залишити в archive; не посилатися з активних гайдів | archive/BULK_ENDPOINTS_AUDIT_REPORT_DEPRECATED.md |
