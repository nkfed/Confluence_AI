import os
from pathlib import Path

class PromptLoader:
    BASE_DIR = Path(__file__).resolve().parent.parent / "prompts"

    @staticmethod
    def load(agent: str, mode: str = "TEST", filename: str = "base.txt") -> str:
        """
        agent: 'summary', 'tagging', ...
        mode: TEST or PROD
        filename: base.txt, test.txt, prod.txt
        """

        # 1. Якщо є override для режиму — беремо його
        mode_file = PromptLoader.BASE_DIR / agent / f"{mode.lower()}.txt"
        if mode_file.exists():
            return mode_file.read_text(encoding="utf-8")

        # 2. Інакше беремо базовий промпт
        base_file = PromptLoader.BASE_DIR / agent / filename
        if base_file.exists():
            return base_file.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Prompt not found for agent={agent}, mode={mode}")
