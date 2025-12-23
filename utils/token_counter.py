import math


def estimate_tokens_count(text: str) -> int:
    """
    Оціночний підрахунок кількості токенів для тексту.
    Це НЕ точний підрахунок (як у tiktoken), але достатньо добрий
    для приблизної оцінки вартості.

    Підхід:
    - ділимо текст на слова
    - в середньому 1 слово ≈ 1.3–1.5 токена
    - використовуємо коефіцієнт 1.4
    """
    if not text:
        return 0

    words = text.strip().split()
    approx_tokens = len(words) * 1.4

    return int(math.ceil(approx_tokens))