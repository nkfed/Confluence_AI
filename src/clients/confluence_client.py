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

    async def update_labels(self, page_id: str, tags: dict):
        raise NotImplementedError

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