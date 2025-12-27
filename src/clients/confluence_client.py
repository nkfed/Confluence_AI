import requests
from typing import Dict, Any
from bs4 import BeautifulSoup
from settings import settings
from src.core.logging.logger import get_logger
from src.core.logging.timing import log_timing
from src.core.logging.retry import log_retry

logger = get_logger(__name__)


class ConfluenceClient:
    """
    Клієнт для взаємодії з Confluence Cloud API.
    """

    def __init__(self):
        self.base_url = settings.CONFLUENCE_BASE_URL
        self.auth = (settings.CONFLUENCE_EMAIL, settings.CONFLUENCE_API_TOKEN)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    @log_retry(attempts=3, backoff=1.0)
    @log_timing
    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Отримати сторінку Confluence у форматі storage."""
        logger.info(f"Fetching page {page_id} from Confluence")
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,version"

        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully fetched page {page_id}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching page {page_id}: {e}")
            raise RuntimeError(f"Confluence API error (get_page): {e}")

    async def get_page_body(self, page_id: str) -> str:
        """
        Отримати HTML-вміст сторінки.
        
        Args:
            page_id: ID сторінки
            
        Returns:
            HTML вміст сторінки
        """
        data = await self.get_page(page_id)
        return data.get("body", {}).get("storage", {}).get("value", "")

    @log_retry(attempts=3, backoff=1.0)
    @log_timing
    async def update_page(self, page_id: str, new_content: str) -> Dict[str, Any]:
        """
        Оновити сторінку Confluence.
        
        Args:
            page_id: ID сторінки
            new_content: Новий HTML вміст
            
        Returns:
            Dict з результатом оновлення
        """
        logger.info(f"Updating page {page_id} in Confluence")
        
        # Fetch current page (MUST await async method)
        page = await self.get_page(page_id)
        current_version = page["version"]["number"]
        
        logger.debug(f"Current version: {current_version}, title: {page['title']}")

        url = f"{self.base_url}/wiki/rest/api/content/{page_id}"

        payload = {
            "id": page_id,
            "type": "page",
            "title": page["title"],
            "version": {"number": current_version + 1},
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }

        try:
            response = requests.put(url, json=payload, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully updated page {page_id}")
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Confluence API error (update_page): {e}")

    @log_timing
    async def append_to_page(self, page_id: str, html_block: str) -> Dict[str, Any]:
        """
        Додати HTML блок в кінець існуючої сторінки.
        
        Args:
            page_id: ID сторінки Confluence
            html_block: HTML блок для додавання
            
        Returns:
            Dict з результатом оновлення
        """
        # HTML validation
        try:
            BeautifulSoup(html_block, "html.parser")
        except Exception:
            logger.error(f"Invalid HTML block for page {page_id}")
            raise ValueError("Invalid HTML content")

        logger.info(f"Appending HTML block to page {page_id}")
        
        # Fetch page (MUST await async method)
        page = await self.get_page(page_id)
        
        # Log page structure for debugging
        import json
        logger.debug(f"Fetched page structure keys: {list(page.keys())}")
        if "body" in page:
            logger.debug(f"Page body keys: {list(page['body'].keys())}")
        
        # Extract current body
        current_body = page["body"]["storage"]["value"]
        logger.debug(f"Current body length: {len(current_body)} chars")
        
        # Append new content
        new_body = current_body + "\n" + html_block
        logger.info(f"New body length: {len(new_body)} chars (added {len(html_block)} chars)")

        return await self.update_page(page_id, new_body)

    async def _get(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            response = requests.get(url, params=params, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"GET {url} failed: {e}")
            raise RuntimeError(f"Confluence API GET error: {e}")

    async def _post(self, url: str, json: Any) -> Dict[str, Any]:
        try:
            response = requests.post(url, json=json, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"POST {url} failed: {e}")
            raise RuntimeError(f"Confluence API POST error: {e}")

    async def _delete(self, url: str):
        try:
            response = requests.delete(url, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"DELETE {url} failed: {e}")
            raise RuntimeError(f"Confluence API DELETE error: {e}")

    async def get_labels(self, page_id: str):
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}/label"
        resp = await self._get(url)
        return [label["name"] for label in resp.get("results", [])]

    async def update_labels(
        self, 
        page_id: str, 
        labels_to_add: list = None, 
        labels_to_remove: list = None
    ):
        """
        Update labels for a Confluence page.
        
        Args:
            page_id: The Confluence page ID
            labels_to_add: List of label names to add
            labels_to_remove: List of label names to remove
            
        Returns:
            Dict with update results
        """
        labels_to_add = labels_to_add or []
        labels_to_remove = labels_to_remove or []
        
        logger.info(f"[Confluence] update_labels() called for page {page_id}")
        logger.debug(f"[Confluence] labels_to_add={labels_to_add}, labels_to_remove={labels_to_remove}")
        
        # 1. Get current labels
        current_labels = await self.get_labels(page_id)
        logger.debug(f"[Confluence] Current labels: {current_labels}")
        
        # 2. Compute final labels
        # Remove labels that should be removed
        final_labels = [label for label in current_labels if label not in labels_to_remove]
        
        # Add new labels (avoiding duplicates)
        for label in labels_to_add:
            if label not in final_labels:
                final_labels.append(label)
        
        logger.info(f"[Confluence] Final labels: {final_labels}")
        
        # 3. Add new labels via API
        if labels_to_add:
            try:
                payload = [{"prefix": "global", "name": label} for label in labels_to_add]
                url = f"{self.base_url}/wiki/rest/api/content/{page_id}/label"
                await self._post(url, json=payload)
                logger.info(f"[Confluence] Successfully added labels: {labels_to_add}")
            except Exception as e:
                logger.error(f"[Confluence] Failed to add labels: {e}")
                raise
        
        # 4. Remove labels via API
        if labels_to_remove:
            try:
                for label in labels_to_remove:
                    url = f"{self.base_url}/wiki/rest/api/content/{page_id}/label/{label}"
                    await self._delete(url)
                logger.info(f"[Confluence] Successfully removed labels: {labels_to_remove}")
            except Exception as e:
                logger.error(f"[Confluence] Failed to remove labels: {e}")
                raise
        
        return {
            "page_id": page_id,
            "labels_added": labels_to_add,
            "labels_removed": labels_to_remove,
            "final_labels": final_labels
        }

    async def get_child_pages(self, parent_id: str) -> list[str]:
        """Отримати список ID дочірніх сторінок."""
        url = f"{self.base_url}/wiki/rest/api/content/{parent_id}/child/page"
        resp = await self._get(url)
        return [page["id"] for page in resp.get("results", [])]

    async def get_all_pages_in_space(self, space_key: str) -> list[str]:
        """Отримати список ID усіх сторінок у просторі."""
        url = f"{self.base_url}/wiki/rest/api/content"
        pages = []
        limit = 50
        start = 0

        while True:
            params = {
                "spaceKey": space_key,
                "type": "page",
                "limit": limit,
                "start": start
            }
            resp = await self._get(url, params=params)
            results = resp.get("results", [])
            if not results:
                break

            pages.extend([page["id"] for page in results])
            start += limit

            # Якщо результатів менше ліміту — ми на останній сторінці
            if len(results) < limit:
                break

        return pages

    def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Пошук сторінок у Confluence."""
        url = f"{self.base_url}/wiki/rest/api/content/search"
        params = {"cql": query, "limit": limit}

        try:
            response = requests.get(url, params=params, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Confluence API error (search): {e}")