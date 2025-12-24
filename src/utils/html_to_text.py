import re
from html import unescape


def html_to_text(html: str) -> str:
    """
    Конвертує HTML-контент Confluence у чистий текст.
    Підтримує таблиці, списки, заголовки та базові блоки.
    """

    if not html:
        return ""

    text = html

    # -----------------------------
    # 1. Блоки → нові рядки
    # -----------------------------
    block_tags = [
        r"</p>", r"</div>", r"</h\d>", r"<br\s*/?>",
        r"</section>", r"</article>"
    ]
    for tag in block_tags:
        text = re.sub(tag, "\n", text)

    # -----------------------------
    # 2. Списки
    # -----------------------------
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"</ul>|</ol>", "\n", text)

    # -----------------------------
    # 3. Таблиці
    # -----------------------------
    # Рядок таблиці → новий рядок
    text = re.sub(r"</tr>", "\n", text)

    # Комірки таблиці → роздільник
    text = re.sub(r"<t[dh][^>]*>", "", text)      # <td>, <th>
    text = re.sub(r"</t[dh]>", " | ", text)

    # Початок таблиці → новий рядок
    text = re.sub(r"<table[^>]*>", "\n", text)
    text = re.sub(r"</table>", "\n", text)

    # -----------------------------
    # 4. Видаляємо всі HTML-теги
    # -----------------------------
    text = re.sub(r"<[^>]+>", "", text)

    # -----------------------------
    # 5. Декодуємо HTML-ентіті
    # -----------------------------
    text = unescape(text)

    # -----------------------------
    # 6. Прибираємо зайві пробіли
    # -----------------------------
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]  # видаляємо порожні рядки

    text = "\n".join(lines)

    # -----------------------------
    # 7. Прибираємо дублікати нових рядків
    # -----------------------------
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()