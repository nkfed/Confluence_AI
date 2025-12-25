import re
import json
from src.agents.base_agent import BaseAgent
from src.utils.prompt_loader import PromptLoader
from src.clients.openai_client import OpenAIClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)


def extract_json(s: str):
    # Витягуємо перший JSON-блок у відповіді
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


class TaggingAgent(BaseAgent):
    def __init__(self, openai_client: OpenAIClient = None):
        super().__init__()
        self.ai = openai_client or OpenAIClient()

    async def suggest_tags(self, text: str) -> dict:
        prompt = f"""
Ти — класифікаційний агент. Проаналізуй текст і поверни ТІЛЬКИ JSON.
Без пояснень. Без markdown. Без тексту до або після JSON.

Формат відповіді строго такий:

{{
  "doc": ["..."],
  "domain": ["..."],
  "kb": ["..."],
  "tool": ["..."]
}}

Текст для аналізу:
{text}
"""

        logger.debug(f"Tagging prompt length: {len(prompt)}")

        raw = await self.ai.generate(prompt)
        logger.debug(f"[TaggingAgent] Raw model response: {raw}")

        return self._parse_response(raw)

    async def process_page(self, page_id: str):
        """
        TaggingAgent не використовує process_page напряму.
        Метод реалізовано для сумісності з BaseAgent.
        """
        raise NotImplementedError("TaggingAgent does not support process_page()")

    def _parse_response(self, response: str) -> dict:
        parsed = extract_json(response)

        if not parsed:
            logger.error("[TaggingAgent] Failed to parse tagging response")
            return {"doc": [], "domain": [], "kb": [], "tool": []}

        return parsed
