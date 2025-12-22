import requests
from settings import settings


class ConfluenceClient:
    """
    Клієнт для взаємодії з Confluence Cloud API.
    Має методи для:
    - отримання контенту сторінок
    - оновлення сторінок
    - пошуку сторінок
    """

    def __init__(self):
        self.base_url = settings.CONFLUENCE_BASE_URL
        self.auth = (settings.CONFLUENCE_EMAIL, settings.CONFLUENCE_API_TOKEN)

    def get_page(self, page_id: str):
        """Отримати сторінку Confluence у форматі storage."""
        url = f"{self.base_url}/wiki/rest/api/content/{page_id}?expand=body.storage,version"
        response = requests.get(url, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def get_page_body(self, page_id: str):
        """Отримати HTML-вміст сторінки."""
        data = self.get_page(page_id)
        return data["body"]["storage"]["value"]

    def update_page(self, page_id: str, new_content: str):
        """
        Оновити сторінку Confluence.
        new_content — HTML (storage format)
        """
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

        response = requests.put(url, json=payload, auth=self.auth)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 10):
        """Пошук сторінок у Confluence."""
        url = f"{self.base_url}/wiki/rest/api/content/search"
        params = {"cql": query, "limit": limit}

        response = requests.get(url, params=params, auth=self.auth)
        response.raise_for_status()
        return response.json()