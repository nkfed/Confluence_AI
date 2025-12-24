class ConfluenceService:
    """
    Сервіс для високорівневої роботи з Confluence.
    Використовує ConfluenceClient для виконання операцій.
    """
    def __init__(self, client):
        self.client = client

    def get_formatted_content(self, page_id):
        """Отримує та форматує контент сторінки для аналізу AI."""
        pass
