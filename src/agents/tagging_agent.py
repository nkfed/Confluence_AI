import re
import json
from typing import Optional
from src.agents.base_agent import BaseAgent
from src.utils.prompt_loader import PromptLoader
from src.clients.openai_client import OpenAIClient
from src.core.ai.router import AIProviderRouter
from src.core.ai.logging_utils import log_ai_call
from src.core.logging.logger import get_logger
from src.utils.tag_structure import limit_tags_per_category
from src.config.tagging_settings import MAX_TAGS_PER_CATEGORY

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
    def __init__(
        self,
        openai_client: OpenAIClient = None,
        ai_router: Optional[AIProviderRouter] = None,
        ai_provider: Optional[str] = None
    ):
        super().__init__(agent_name="TAGGING_AGENT")
        
        # Support both old (openai_client) and new (ai_router) initialization
        if ai_router is not None:
            self._ai_router = ai_router
            self._ai_provider = ai_provider
            self.ai = None  # Mark as using router
            logger.info(f"TaggingAgent using AI Router with provider: {ai_provider or 'default'}")
        else:
            # Backward compatibility: use direct OpenAI client
            self.ai = openai_client or OpenAIClient()
            self._ai_router = None
            self._ai_provider = None
            logger.info("TaggingAgent using direct OpenAI client (legacy mode)")

    async def suggest_tags(self, text: str) -> dict:
        prompt = f"""
Ти — класифікаційний агент для Confluence.

Твоє завдання — проаналізувати текст і повернути ТІЛЬКИ JSON з тегами.
Не додавай пояснень, markdown або тексту поза JSON.

Використовуй ТІЛЬКИ теги зі списків нижче.
Не вигадуй нових тегів.
Якщо тег не підходить — не включай його.

------------------------------------------
ДОСТУПНІ ТЕГИ (канонічні):

doc-теги:
- doc-tech
- doc-business
- doc-process
- doc-onboarding
- doc-architecture
- doc-requirements
- doc-design
- doc-knowledge-base
- doc-ai-tools
- doc-prompt-template

domain-теги:
- domain-ehealth-core
- domain-dzr
- domain-rehab-1-0
- domain-rehab-2-0
- domain-helpdesk-site
- domain-ai-integration

kb-теги:
- kb-overview
- kb-template
- kb-example
- kb-index
- kb-canonical
- kb-uml
- kb-components
- kb-entities-hierarchy
- kb-error-handling

tool-теги:
- tool-confluence
- tool-vscode
- tool-pycharm
- tool-github-copilot
- tool-nextjs
- tool-vercel
- tool-rovo-agent
------------------------------------------

Правила:
1. Повертаєш максимум {MAX_TAGS_PER_CATEGORY} теги в кожній категорії.
2. Повертаєш тег ТІЛЬКИ якщо він явно присутній у тексті або однозначно випливає з контексту.
3. Якщо немає релевантних тегів — поверни порожній список.
4. Не вигадуй нових тегів.
5. Не додавай тексту поза JSON.

Формат відповіді строго такий:

{{
  "doc": [],
  "domain": [],
  "kb": [],
  "tool": []
}}

Текст для аналізу:
{text}
"""

        logger.debug(f"Tagging prompt length: {len(prompt)}")

        # Use router if available with unified logging
        if self._ai_router is not None:
            provider = self._ai_router.get(self._ai_provider)
            ai_response = await log_ai_call(
                provider_name=provider.name,
                model=provider.model_default,
                operation="tagging",
                coro=lambda: provider.generate(prompt)
            )
            raw = ai_response.text
            logger.debug(f"[TaggingAgent] AI response received (provider={ai_response.provider}, tokens={ai_response.total_tokens})")
        else:
            # Legacy: direct OpenAI call
            raw = await self.ai.generate(prompt)
            logger.debug(f"[TaggingAgent] OpenAI response received (legacy mode)")
        
        logger.debug(f"[TaggingAgent] Raw model response: {raw}")

        tags = self._parse_response(raw)
        
        # ✅ Post-processing: enforce MAX_TAGS_PER_CATEGORY limit
        limited_tags = limit_tags_per_category(tags)
        
        if tags != limited_tags:
            logger.warning(
                f"[TaggingAgent] AI returned more than {MAX_TAGS_PER_CATEGORY} tags per category. "
                f"Applied post-processing limit."
            )
        
        return limited_tags

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
