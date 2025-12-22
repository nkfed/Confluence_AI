class SummaryService:
    """
    Сервіс для генерації summary.
    Взаємодіє з AI-агентами та оновлює сторінки через ConfluenceService.
    """
    def __init__(self, confluence_service, ai_agent):
        self.confluence_service = confluence_service
        self.ai_agent = ai_agent

    def process_page_summary(self, page_id):
        """
        Основний флоу:
        1. Читання сторінки
        2. Генерація summary через AI
        3. Оновлення сторінки в Confluence
        """
        pass
