"""
TagResetService — сервіс для скидання тегів на сторінках Confluence.

Підтримує:
- Видалення тегів за категоріями
- Видалення всіх AI-тегів
- Dry-run режим
- Режимна логіка (TEST/SAFE_TEST/PROD)
"""

from typing import Dict, Any, List, Optional
from src.clients.confluence_client import ConfluenceClient
from src.core.logging.logger import get_logger
from src.config.tagging_settings import TAG_CATEGORIES

logger = get_logger(__name__)


class TagResetService:
    """Сервіс для скидання тегів на сторінках."""
    
    # AI-теги — всі теги, що починаються з префіксів категорій
    AI_TAG_PREFIXES = ["doc-", "domain-", "kb-", "tool-"]
    
    def __init__(self, confluence_client: ConfluenceClient = None):
        """
        Ініціалізація TagResetService.
        
        Args:
            confluence_client: Клієнт Confluence (опціонально)
        """
        self.confluence = confluence_client or ConfluenceClient()
    
    def is_ai_tag(self, label: str) -> bool:
        """
        Перевіряє, чи є тег AI-згенерованим.
        
        Args:
            label: Назва тегу
            
        Returns:
            True якщо тег є AI-згенерованим
        """
        return any(label.startswith(prefix) for prefix in self.AI_TAG_PREFIXES)
    
    def filter_tags_by_categories(
        self,
        labels: List[str],
        categories: Optional[List[str]] = None
    ) -> List[str]:
        """
        Фільтрує теги за категоріями.
        
        Args:
            labels: Список всіх тегів
            categories: Категорії для фільтрації (None = всі AI-теги)
            
        Returns:
            Список тегів, що відповідають критеріям
        """
        if not categories:
            # Всі AI-теги
            return [label for label in labels if self.is_ai_tag(label)]
        
        # Фільтрація за категоріями
        filtered = []
        for label in labels:
            for category in categories:
                if label.startswith(f"{category}-"):
                    filtered.append(label)
                    break
        
        return filtered
    
    async def reset_page_tags(
        self,
        page_id: str,
        page_title: str,
        categories: Optional[List[str]] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Скидає теги на одній сторінці.
        
        Args:
            page_id: ID сторінки
            page_title: Назва сторінки
            categories: Категорії тегів для видалення (None = всі AI-теги)
            dry_run: Чи це dry-run режим
            
        Returns:
            {
                "page_id": str,
                "title": str,
                "status": "removed" | "dry_run" | "no_tags",
                "removed_tags": List[str],
                "skipped": bool
            }
        """
        logger.info(f"Resetting tags for page {page_id} ({page_title}), dry_run={dry_run}")
        
        try:
            # Отримати поточні теги
            current_labels = await self.confluence.get_labels(page_id)
            
            # Фільтрувати теги для видалення
            tags_to_remove = self.filter_tags_by_categories(current_labels, categories)
            
            if not tags_to_remove:
                logger.info(f"No AI tags to remove on page {page_id}")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "no_tags",
                    "removed_tags": [],
                    "skipped": False
                }
            
            # Dry-run режим
            if dry_run:
                logger.info(f"DRY RUN: Would remove tags {tags_to_remove} from page {page_id}")
                return {
                    "page_id": page_id,
                    "title": page_title,
                    "status": "dry_run",
                    "removed_tags": tags_to_remove,
                    "skipped": False
                }
            
            # Видалити теги
            result = await self.confluence.remove_labels(page_id, tags_to_remove)
            
            logger.info(f"Successfully removed tags {tags_to_remove} from page {page_id}")
            return {
                "page_id": page_id,
                "title": page_title,
                "status": "removed",
                "removed_tags": result.get("removed", []),
                "skipped": False
            }
            
        except Exception as e:
            logger.error(f"Error resetting tags for page {page_id}: {e}")
            return {
                "page_id": page_id,
                "title": page_title,
                "status": "error",
                "error": str(e),
                "removed_tags": [],
                "skipped": True
            }
    
    async def reset_space_tags(
        self,
        pages: List[Dict[str, Any]],
        categories: Optional[List[str]] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Скидає теги на всіх сторінках простору.
        
        Args:
            pages: Список об'єктів сторінок
            categories: Категорії тегів для видалення (None = всі AI-теги)
            dry_run: Чи це dry-run режим
            
        Returns:
            {
                "total": int,
                "processed": int,
                "removed": int,
                "no_tags": int,
                "errors": int,
                "dry_run": bool,
                "details": List[Dict]
            }
        """
        logger.info(f"Resetting tags on {len(pages)} pages, dry_run={dry_run}")
        
        total = len(pages)
        processed = 0
        removed_count = 0
        no_tags_count = 0
        errors = 0
        details = []
        
        for page in pages:
            page_id = page.get("id")
            page_title = page.get("title", "Unknown")
            
            result = await self.reset_page_tags(
                page_id=page_id,
                page_title=page_title,
                categories=categories,
                dry_run=dry_run
            )
            
            details.append(result)
            processed += 1
            
            status = result.get("status")
            if status == "removed" or status == "dry_run":
                removed_count += 1
            elif status == "no_tags":
                no_tags_count += 1
            elif status == "error":
                errors += 1
        
        summary = {
            "total": total,
            "processed": processed,
            "removed": removed_count,
            "no_tags": no_tags_count,
            "errors": errors,
            "dry_run": dry_run,
            "details": details
        }
        
        logger.info(f"Reset complete: {removed_count} pages processed, {errors} errors")
        return summary
