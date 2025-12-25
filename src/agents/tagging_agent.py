from src.agents.base_agent import BaseAgent
from src.utils.prompt_loader import PromptLoader
from src.clients.openai_client import OpenAIClient
from src.core.logging.logger import get_logger

logger = get_logger(__name__)

class TaggingAgent(BaseAgent):
    def __init__(self, openai_client: OpenAIClient = None):
        super().__init__()
        self.ai = openai_client or OpenAIClient()

    async def suggest_tags(self, text: str) -> dict:
        policy = PromptLoader.load("tagging", filename="policy.txt")
        template = PromptLoader.load("tagging", mode=self.mode)

        prompt = template.format(TEXT=text, POLICY=policy)

        logger.debug(f"Tagging prompt length: {len(prompt)}")

        response = await self.ai.generate(prompt)
        return self._parse_response(response)

    async def process_page(self, page_id: str):
        """
        TaggingAgent не використовує process_page напряму.
        Метод реалізовано для сумісності з BaseAgent.
        """
        raise NotImplementedError("TaggingAgent does not support process_page()")

    def _parse_response(self, response: str) -> dict:
        import json
        try:
            return json.loads(response)
        except Exception:
            logger.error("Failed to parse tagging response")
            return {"doc": [], "domain": [], "kb": [], "tool": []}
