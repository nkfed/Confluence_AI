from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Базовий абстрактний клас для AI-агентів."""

    def __init__(self):
        """Базовий конструктор без параметрів."""
        pass

    @abstractmethod
    def process_page(self, page_id: str):
        """Базовий метод, який мають реалізувати всі агенти."""
        pass