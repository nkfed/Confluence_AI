import requests
from typing import Dict, Any
from settings import settings


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

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Отримати сторінку Confluence у форматі storage."""
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,version"

        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Confluence API error (get_page): {e}")

    def get_page_body(self, page_id: str) -> str:
        """Отримати HTML-вміст сторінки."""
        data = self.get_page(page_id)
        return data.get("body", {}).get("storage", {}).get("value", "")

    def update_page(self, page_id: str, new_content: str) -> Dict[str, Any]:
        """Оновити сторінку Confluence."""
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
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Confluence API error (update_page): {e}")

    def append_to_page(self, page_id: str, html_block: str) -> Dict[str, Any]:
        """Додати HTML-блок у кінець сторінки."""
        page = self.get_page(page_id)
        current_body = page["body"]["storage"]["value"]
        new_body = current_body + "\n" + html_block

        return self.update_page(page_id, new_body)

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