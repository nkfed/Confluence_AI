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

    def get_page_body(self, page_id: str) -> str:
        """Отримати HTML-вміст сторінки."""
        data = self.get_page(page_id)
        return data.get("body", {}).get("storage", {}).get("value", "")

    @log_retry(attempts=3, backoff=1.0)
    @log_timing
    def update_page(self, page_id: str, new_content: str) -> Dict[str, Any]:
        """Оновити сторінку Confluence."""
        logger.info(f"Updating page {page_id} in Confluence")
        page = self.get_page(page_id)
        current_version = page["version"]["number"]

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
    def append_to_page(self, page_id: str, html_block: str) -> Dict[str, Any]:
        """Додати HTML-блок у кінець сторінки."""

        # HTML validation
        try:
            BeautifulSoup(html_block, "html.parser")
        except Exception:
            logger.error(f"Invalid HTML block for page {page_id}")
            raise ValueError("Invalid HTML content")

        logger.info(f"Appending HTML block to page {page_id}")
        page = self.get_page(page_id)
        current_body = page["body"]["storage"]["value"]
        new_body = current_body + "\n" + html_block

        return self.update_page(page_id, new_body)

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

    async def update_labels(self, page_id: str, tags: dict, dry_run: bool = False):
        try:
            logger.info(f"[Confluence] update_labels() called for page {page_id}, dry_run={dry_run}")
            # 1. Whitelist check
            allowed = [x.strip() for x in settings.ALLOWED_TAGGING_PAGES.split(",")]
            if page_id not in allowed:
                logger.warning(f"[Confluence] Page {page_id} not in whitelist, skipping update")
                return

            # 2. Отримати існуючі теги
            existing = await self.get_labels(page_id)

            # 3. Зібрати нові теги у плоский список
            new_tags = []
            for category, values in tags.items():
                new_tags.extend(values)

            # 4. Визначити теги, які треба додати
            to_add = [t for t in new_tags if t not in existing]

            # 5. Визначити теги, які треба видалити (опційно)
            to_remove = [t for t in existing if t not in new_tags]

            # 6. Dry-run логіка
            if dry_run:
                logger.info(f"[Confluence] Dry-run: would add {to_add}, remove {to_remove}")
                return

            # 7. Реалізувати додавання тегів
            if to_add:
                payload = [{"prefix": "global", "name": t} for t in to_add]
                url = f"{self.base_url}/wiki/rest/api/content/{page_id}/label"
                await self._post(url, json=payload)
                logger.info(f"[Confluence] Added labels: {to_add}")

            # 8. Реалізувати видалення тегів
            for t in to_remove:
                url = f"{self.base_url}/wiki/rest/api/content/{page_id}/label/{t}"
                await self._delete(url)
            if to_remove:
                logger.info(f"[Confluence] Removed labels: {to_remove}")

        except Exception as e:
            logger.error(f"[Confluence] Failed to update labels for page {page_id}: {e}")
            raise

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