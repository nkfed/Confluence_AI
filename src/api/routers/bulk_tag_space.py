"""
API роутер для bulk-тегування простору Confluence.

POST /bulk/tag-space/{space_key}
"""

from typing import Optional
from fastapi import APIRouter, Path, Query
from src.core.bulk_tag_orchestrator import BulkTagOrchestrator
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/bulk", tags=["bulk"])


@router.post("/tag-space/{space_key}")
async def bulk_tag_space(
    space_key: str = Path(..., description="Confluence space key"),
    dry_run: Optional[bool] = Query(
        default=None,
        description="Override dry-run mode. If None, uses TAGGING_AGENT_MODE"
    ),
    exclude_archived: bool = Query(
        default=True,
        description="Exclude archived pages"
    ),
    exclude_index_pages: bool = Query(
        default=True,
        description="Exclude index pages"
    ),
    exclude_templates: bool = Query(
        default=True,
        description="Exclude template pages"
    ),
    exclude_empty_pages: bool = Query(
        default=True,
        description="Exclude empty pages"
    ),
    exclude_by_title_regex: Optional[str] = Query(
        default=None,
        description="Exclude pages matching title regex"
    )
):
    """
    Bulk-тегування всіх сторінок у просторі Confluence.
    
    Режимна логіка:
    - TEST: завжди dry_run=True, тільки whitelist
    - SAFE_TEST:
        - dry_run=True → тільки симуляція, whitelist
        - dry_run=False → реальний запис, whitelist
    - PROD:
        - dry_run визначає запис
        - whitelist не застосовується
    
    Фільтри:
    - exclude_archived: виключити архівовані сторінки
    - exclude_index_pages: виключити індексні сторінки
    - exclude_templates: виключити шаблони
    - exclude_empty_pages: виключити порожні сторінки (< 50 символів)
    - exclude_by_title_regex: виключити за регулярним виразом
    - SAFE_TEST whitelist: автоматично застосовується у TEST/SAFE_TEST режимах
    
    Для кожної сторінки:
    - Отримує контент
    - Визначає allowed_labels (default для bulk)
    - Будує промпт через PromptBuilder
    - Викликає TaggingAgent для AI-аналізу
    - Застосовує limit_tags_per_category()
    - Формує структуру тегів (proposed, existing, to_add, added)
    - Якщо запис дозволено → додає теги
    
    Args:
        space_key: Ключ простору Confluence
        dry_run: Перевизначення dry-run режиму (None = авто)
        exclude_archived: Виключити архівовані
        exclude_index_pages: Виключити індексні
        exclude_templates: Виключити шаблони
        exclude_empty_pages: Виключити порожні
        exclude_by_title_regex: Regex для виключення
        
    Returns:
        {
            "total": int,                  # Всього сторінок у просторі
            "processed": int,              # Оброблено сторінок
            "success": int,                # Успішно оброблено
            "errors": int,                 # Помилки
            "skipped_count": int,          # Пропущено фільтрами
            "dry_run": bool,               # Чи був dry-run
            "mode": str,                   # Режим (TEST/SAFE_TEST/PROD)
            "details": [                   # Деталі по кожній сторінці
                {
                    "page_id": str,
                    "title": str,
                    "status": "updated" | "dry_run" | "forbidden" | "error" | "skipped",
                    "tags": {
                        "proposed": [],    # AI-згенеровані теги
                        "existing": [],    # Існуючі теги
                        "to_add": [],      # Dry-run: що буде додано
                        "added": [],       # Реально додано
                        "skipped": [],     # Пропущено (forbidden)
                        "errors": []       # Помилки
                    }
                }
            ],
            "skipped_pages": [             # Сторінки, пропущені фільтрами
                {
                    "page_id": str,
                    "title": str,
                    "reason": str
                }
            ]
        }
    """
    logger.info(f"POST /bulk/tag-space/{space_key}: dry_run={dry_run}")
    
    try:
        orchestrator = BulkTagOrchestrator()
        
        result = await orchestrator.tag_space(
            space_key=space_key,
            dry_run_override=dry_run,
            exclude_archived=exclude_archived,
            exclude_index_pages=exclude_index_pages,
            exclude_templates=exclude_templates,
            exclude_empty_pages=exclude_empty_pages,
            exclude_by_title_regex=exclude_by_title_regex
        )
        
        logger.info(f"Bulk tagging complete for space {space_key}")
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk tag space {space_key}: {e}")
        return {
            "total": 0,
            "processed": 0,
            "success": 0,
            "errors": 1,
            "skipped_count": 0,
            "dry_run": dry_run if dry_run is not None else True,
            "mode": "UNKNOWN",
            "error": str(e),
            "details": [],
            "skipped_pages": []
        }
