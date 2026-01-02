"""
⚠️  DEPRECATED MODULE ⚠️

BulkTagOrchestrator is DEPRECATED and replaced by BulkTaggingService.

DO NOT USE THIS CLASS FOR NEW DEVELOPMENT.

Reason for deprecation:
- Uses old whitelist mechanism (AgentModeResolver + env vars)
- Does not use WhitelistManager or whitelist_config.json
- In PROD mode, ignores whitelist completely
- Does not support unified dry_run matrix
- Does not support task_id for cancellation
- Uses deprecated exclude_* parameters

Use instead:
    from src.services.bulk_tagging_service import BulkTaggingService
    service = BulkTaggingService()
    result = await service.tag_space(space_key=space_key, dry_run=dry_run)

Kept temporarily for backward compatibility.
Will be removed in future versions.

---

OLD DOCUMENTATION (for reference only):

BulkTagOrchestrator — оркестратор для bulk-тегування просторів Confluence.

Відповідальність:
- Отримання сторінок простору
- Застосування фільтрів
- Визначення режиму роботи (TEST/SAFE_TEST/PROD)
- Виклик TaggingAgent для кожної сторінки
- Контроль dry_run режиму
- Формування агрегованої відповіді
- Логування всіх етапів
"""

from typing import Dict, Any, List, Optional
from src.clients.confluence_client import ConfluenceClient
from src.agents.tagging_agent import TaggingAgent
from src.agents.prompt_builder import PromptBuilder
from src.services.page_filter_service import PageFilterService
from src.core.agent_mode_resolver import AgentModeResolver
from src.core.whitelist.whitelist_manager import WhitelistManager
from src.core.logging.logger import get_logger
from src.utils.tag_structure import limit_tags_per_category
from src.sections.whitelist import get_default_labels
from settings import AgentMode

logger = get_logger(__name__)


# DEPRECATED — use BulkTaggingService instead
# See module docstring for details
class BulkTagOrchestrator:
    """Оркестратор для bulk-тегування просторів.
    
    ⚠️  DEPRECATED: Use BulkTaggingService instead.
    """
    
    AGENT_NAME = "TAGGING_AGENT"
    
    def __init__(
        self,
        confluence_client: ConfluenceClient = None,
        tagging_agent: TaggingAgent = None,
        mode: str = None
    ):
        """
        Ініціалізація BulkTagOrchestrator.
        
        Args:
            confluence_client: Клієнт Confluence (опціонально)
            tagging_agent: Агент тегування (опціонально)
            mode: Явне встановлення режиму (TEST, SAFE_TEST, PROD) - для тестування
        """
        self.confluence = confluence_client or ConfluenceClient()
        self.tagging_agent = tagging_agent or TaggingAgent()
        
        # Визначити режим (дозволяє явне встановлення для тестів)
        self.mode = mode or AgentModeResolver.resolve_mode(self.AGENT_NAME)
        
        # Ініціалізувати фільтр (whitelist буде завантажений у tag_space)
        self.filter_service = PageFilterService(whitelist=[])
        
        logger.info(f"BulkTagOrchestrator initialized: mode={self.mode}, whitelist_size=0 (loaded per space)")
    
    async def tag_space(
        self,
        space_key: str,
        dry_run_override: Optional[bool] = None,
        exclude_archived: bool = True,
        exclude_index_pages: bool = True,
        exclude_templates: bool = True,
        exclude_empty_pages: bool = True,
        exclude_by_title_regex: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Виконати bulk-тегування простору Confluence.
        
        Режимна логіка:
        - TEST: завжди dry_run=True, тільки whitelist
        - SAFE_TEST:
            - dry_run=True → тільки симуляція, whitelist
            - dry_run=False → реальний запис, whitelist
        - PROD:
            - dry_run визначає запис
            - whitelist не застосовується
        
        Args:
            space_key: Ключ простору Confluence
            dry_run_override: Перевизначення dry_run (None = auto)
            exclude_archived: Виключити архівовані сторінки
            exclude_index_pages: Виключити індексні сторінки
            exclude_templates: Виключити шаблони
            exclude_empty_pages: Виключити порожні сторінки
            exclude_by_title_regex: Регулярний вираз для виключення за назвою
            
        Returns:
            {
                "total": int,
                "processed": int,
                "success": int,
                "errors": int,
                "skipped_count": int,
                "dry_run": bool,
                "mode": str,
                "details": List[Dict],
                "skipped_pages": List[Dict]
            }
        """
        logger.info(f"Starting bulk tag for space {space_key}, mode={self.mode}")
        
        # Завантажити whitelist з конфігурації (єдине джерело)
        whitelist_manager = WhitelistManager()
        try:
            allowed_ids = await whitelist_manager.get_allowed_ids(space_key, self.confluence)
        except Exception as e:
            logger.error(f"[WHITELIST] Failed to load whitelist for {space_key}: {e}")
            return {
                "total": 0,
                "processed": 0,
                "success": 0,
                "errors": 1,
                "skipped_count": 0,
                "dry_run": False,
                "mode": self.mode,
                "error": f"Whitelist load failed: {e}",
                "details": [],
                "skipped_pages": []
            }
        logger.info(
            f"[WHITELIST] Loaded from whitelist_config.json for space={space_key}: {len(allowed_ids)} entries"
        )
        self.filter_service.whitelist = [str(pid) for pid in allowed_ids]
        
        # Визначити dry_run
        dry_run = self._resolve_dry_run(dry_run_override)
        logger.info(f"Resolved dry_run={dry_run} (override={dry_run_override}, mode={self.mode})")
        
        # Отримати всі сторінки простору
        try:
            pages = await self.confluence.get_pages_in_space(space_key, expand="body.storage,version")
            logger.info(f"Fetched {len(pages)} pages from space {space_key}")
        except Exception as e:
            logger.error(f"Failed to fetch pages from space {space_key}: {e}")
            return {
                "total": 0,
                "processed": 0,
                "success": 0,
                "errors": 1,
                "skipped_count": 0,
                "dry_run": dry_run,
                "mode": self.mode,
                "error": str(e),
                "details": [],
                "skipped_pages": []
            }
        
        # Фільтрувати сторінки
        filtered_pages, skipped_pages = self._filter_pages(
            pages=pages,
            exclude_archived=exclude_archived,
            exclude_index_pages=exclude_index_pages,
            exclude_templates=exclude_templates,
            exclude_empty_pages=exclude_empty_pages,
            exclude_by_title_regex=exclude_by_title_regex
        )
        
        logger.info(f"After filtering: {len(filtered_pages)} pages to process, {len(skipped_pages)} skipped")
        
        # Тегувати кожну сторінку
        details = []
        success_count = 0
        error_count = 0
        
        for page in filtered_pages:
            result = await self._tag_page(page, dry_run)
            details.append(result)
            
            if result.get("status") in ["updated", "dry_run"]:
                success_count += 1
            elif result.get("status") == "error":
                error_count += 1
        
        summary = {
            "total": len(pages),
            "processed": len(filtered_pages),
            "success": success_count,
            "errors": error_count,
            "skipped_count": len(skipped_pages),
            "dry_run": dry_run,
            "mode": self.mode,
            "details": details,
            "skipped_pages": skipped_pages
        }
        
        logger.info(f"Bulk tagging complete: {success_count} success, {error_count} errors, {len(skipped_pages)} skipped")
        return summary
    
    def _resolve_dry_run(self, override: Optional[bool]) -> bool:
        """
        Визначає dry_run режим згідно з режимною логікою.
        
        Args:
            override: Явне перевизначення dry_run
            
        Returns:
            True якщо dry_run режим
        """
        # TEST режим — завжди dry_run
        if self.mode == AgentMode.TEST:
            return True
        
        # Explicit override має пріоритет
        if override is not None:
            return override
        
        # SAFE_TEST та PROD — за замовчуванням dry_run=True (безпека)
        return True
    
    def _filter_pages(
        self,
        pages: List[Dict[str, Any]],
        exclude_archived: bool,
        exclude_index_pages: bool,
        exclude_templates: bool,
        exclude_empty_pages: bool,
        exclude_by_title_regex: Optional[str]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Фільтрує сторінки згідно з заданими критеріями.
        
        Returns:
            (filtered_pages, skipped_pages)
        """
        filtered = []
        skipped = []
        
        for page in pages:
            should_exclude, reason = self.filter_service.should_exclude_page(
                page=page,
                mode=self.mode,
                exclude_archived=exclude_archived,
                exclude_index_pages=exclude_index_pages,
                exclude_templates=exclude_templates,
                exclude_empty_pages=exclude_empty_pages,
                exclude_by_title_regex=exclude_by_title_regex
            )
            
            if should_exclude:
                skipped.append({
                    "page_id": page.get("id"),
                    "title": page.get("title"),
                    "reason": reason
                })
            else:
                filtered.append(page)
        
        return filtered, skipped
    
    async def _tag_page(self, page: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
        """
        Тегує одну сторінку.
        
        Args:
            page: Об'єкт сторінки Confluence
            dry_run: Чи це dry_run режим
            
        Returns:
            Результат тегування з уніфікованою структурою
        """
        page_id = page.get("id")
        page_title = page.get("title", "Unknown")
        
        logger.info(f"Tagging page {page_id} ({page_title}), dry_run={dry_run}")
        
        try:
            # Отримати контент сторінки
            content = page.get("body", {}).get("storage", {}).get("value", "")
            
            if not content:
                logger.warning(f"Page {page_id} has no content")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "skipped",
                    "reason": "No content",
                    "tags": {
                        "proposed": [],
                        "existing": [],
                        "to_add": [],
                        "added": [],
                        "skipped": [],
                        "errors": []
                    }
                }
            
            # Визначити allowed_labels (використовуємо default для bulk operation)
            allowed_labels = get_default_labels()
            
            # Побудувати промпт
            prompt = PromptBuilder.build_tag_tree_prompt(
                content=content,
                allowed_labels=allowed_labels,
                dry_run=dry_run
            )
            
            # Викликати AI для отримання тегів
            ai_response = await self.tagging_agent.suggest_tags(prompt)
            
            # Застосувати limit_tags_per_category
            limited_tags = limit_tags_per_category(ai_response)
            
            # Перетворити на flat список
            proposed_tags = []
            for category, tags in limited_tags.items():
                proposed_tags.extend(tags)
            
            # Отримати існуючі теги
            existing_tags = await self.confluence.get_labels(page_id)
            
            # Визначити теги для додавання
            to_add = [tag for tag in proposed_tags if tag not in existing_tags]
            
            # Якщо dry_run — не додавати
            if dry_run:
                logger.info(f"DRY RUN: Would add tags {to_add} to page {page_id}")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "dry_run",
                    "tags": {
                        "proposed": proposed_tags,
                        "existing": existing_tags,
                        "to_add": to_add,
                        "added": [],
                        "skipped": [],
                        "errors": []
                    }
                }
            
            # Перевірка режиму — чи можемо ми модифікувати сторінку
            can_modify = AgentModeResolver.can_modify_confluence(
                mode=self.mode,
                page_id=page_id,
                whitelist=self.filter_service.whitelist
            )
            
            if not can_modify:
                logger.warning(f"Page {page_id} modification forbidden in {self.mode} mode")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "forbidden",
                    "reason": f"Not allowed in {self.mode} mode",
                    "tags": {
                        "proposed": proposed_tags,
                        "existing": existing_tags,
                        "to_add": to_add,
                        "added": [],
                        "skipped": to_add,
                        "errors": []
                    }
                }
            
            # Додати теги
            if to_add:
                result = await self.confluence.add_labels(page_id, to_add)
                added = result.get("added", [])
                errors = result.get("errors", [])
                
                logger.info(f"Successfully added tags {added} to page {page_id}")
                
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "updated",
                    "tags": {
                        "proposed": proposed_tags,
                        "existing": existing_tags,
                        "to_add": [],
                        "added": added,
                        "skipped": [],
                        "errors": errors
                    }
                }
            else:
                logger.info(f"No new tags to add for page {page_id}")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "no_changes",
                    "tags": {
                        "proposed": proposed_tags,
                        "existing": existing_tags,
                        "to_add": [],
                        "added": [],
                        "skipped": [],
                        "errors": []
                    }
                }
        
        except Exception as e:
            logger.error(f"Error tagging page {page_id}: {e}")
            return {
                "page_id": page_id,
                "title": page_title,
                "status": "error",
                "error": str(e),
                "tags": {
                    "proposed": [],
                    "existing": [],
                    "to_add": [],
                    "added": [],
                    "skipped": [],
                    "errors": [{"error": str(e)}]
                }
            }
