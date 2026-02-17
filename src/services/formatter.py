import re
import html
import logging

logger = logging.getLogger(__name__)

# Лимит Telegram на длину одного сообщения
MAX_MESSAGE_LENGTH = 4096


class MessageFormatter:
    """Конвертирует Markdown-ответ Claude в Telegram HTML и разбивает на части."""

    def format_for_telegram(self, text: str) -> list[str]:
        """Форматирует текст для отправки в Telegram.

        Возвращает список сообщений, каждое ≤ 4096 символов.
        """
        if not text:
            return ["(пустой ответ)"]

        html_text = self._markdown_to_html(text)
        return self._split_message(html_text)

    def _markdown_to_html(self, text: str) -> str:
        """Конвертирует Markdown в Telegram HTML."""
        # 1. Извлекаем блоки кода — их содержимое не трогаем
        code_blocks: list[str] = []
        placeholder = "\x00CB"

        def save_code_block(match: re.Match) -> str:
            lang = match.group(1) or ""
            code = html.escape(match.group(2).strip())
            if lang:
                block = f'<pre><code class="language-{html.escape(lang)}">{code}</code></pre>'
            else:
                block = f"<pre>{code}</pre>"
            idx = len(code_blocks)
            code_blocks.append(block)
            return f"{placeholder}{idx}\x00"

        result = re.sub(r"```(\w*)\n(.*?)```", save_code_block, text, flags=re.DOTALL)

        # 2. Извлекаем инлайн-код
        inline_codes: list[str] = []
        ic_placeholder = "\x00IC"

        def save_inline_code(match: re.Match) -> str:
            code = html.escape(match.group(1))
            idx = len(inline_codes)
            inline_codes.append(f"<code>{code}</code>")
            return f"{ic_placeholder}{idx}\x00"

        result = re.sub(r"`([^`\n]+)`", save_inline_code, result)

        # 3. Обрабатываем таблицы (до экранирования HTML)
        result = self._convert_tables(result)

        # 4. Экранируем HTML-символы
        result = html.escape(result)

        # 5. Горизонтальные линии: --- или *** или ___
        result = re.sub(r"^[-*_]{3,}\s*$", "———————————", result, flags=re.MULTILINE)

        # 6. Жирный: **text** или __text__
        result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result, flags=re.DOTALL)
        result = re.sub(r"__(.+?)__", r"<b>\1</b>", result, flags=re.DOTALL)

        # 7. Курсив: *text* или _text_
        result = re.sub(r"\*(.+?)\*", r"<i>\1</i>", result, flags=re.DOTALL)
        result = re.sub(r"(?<!\w)_([^_]+?)_(?!\w)", r"<i>\1</i>", result)

        # 8. Зачёркнутый: ~~text~~
        result = re.sub(r"~~(.+?)~~", r"<s>\1</s>", result, flags=re.DOTALL)

        # 9. Заголовки → жирный текст
        result = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", result, flags=re.MULTILINE)

        # 10. Ссылки: [text](url)
        result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', result)

        # 11. Маркированные списки
        result = re.sub(r"^[\-\*]\s+", "• ", result, flags=re.MULTILINE)

        # 12. Восстанавливаем инлайн-код
        for idx, code in enumerate(inline_codes):
            result = result.replace(html.escape(f"{ic_placeholder}{idx}\x00"), code)

        # 13. Восстанавливаем блоки кода
        for idx, block in enumerate(code_blocks):
            result = result.replace(html.escape(f"{placeholder}{idx}\x00"), block)

        return result.strip()

    def _convert_tables(self, text: str) -> str:
        """Конвертирует Markdown-таблицы в читаемый текстовый формат."""
        lines = text.split("\n")
        result_lines: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Проверяем, является ли строка началом таблицы
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|?[\s\-:|]+\|", lines[i + 1].strip()):
                # Собираем все строки таблицы
                table_lines: list[str] = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1

                # Парсим таблицу
                parsed = self._parse_table(table_lines)
                result_lines.extend(parsed)
            else:
                result_lines.append(lines[i])
                i += 1

        return "\n".join(result_lines)

    def _parse_table(self, table_lines: list[str]) -> list[str]:
        """Парсит Markdown-таблицу и возвращает текстовый формат."""
        rows: list[list[str]] = []

        for line in table_lines:
            # Пропускаем разделительную строку (|---|---|)
            if re.match(r"^\|?[\s\-:|]+\|?$", line):
                continue

            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)

        if not rows:
            return table_lines

        # Форматируем: заголовок жирным, данные — через двоеточие
        result: list[str] = []
        headers = rows[0] if rows else []

        for row_idx, row in enumerate(rows):
            if row_idx == 0 and len(rows) > 1:
                # Заголовок таблицы — жирный
                result.append("  ".join(f"**{cell}**" for cell in row))
            else:
                # Данные — через " | "
                if headers and len(row) == len(headers) and len(rows) > 1:
                    parts = []
                    for h, v in zip(headers, row):
                        parts.append(f"**{h}**: {v}")
                    result.append(" │ ".join(parts))
                else:
                    result.append(" │ ".join(row))

        return result

    def _split_message(self, text: str) -> list[str]:
        """Разбивает сообщение на части ≤ MAX_MESSAGE_LENGTH символов."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        parts: list[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= MAX_MESSAGE_LENGTH:
                parts.append(remaining)
                break

            chunk = remaining[:MAX_MESSAGE_LENGTH]
            split_pos = self._find_split_position(chunk)

            parts.append(remaining[:split_pos].rstrip())
            remaining = remaining[split_pos:].lstrip("\n")

        return parts if parts else ["(пустой ответ)"]

    def _find_split_position(self, chunk: str) -> int:
        """Находит оптимальное место для разрыва сообщения."""
        for sep in ["</pre>", "\n\n", "\n", " "]:
            pos = chunk.rfind(sep)
            if pos > MAX_MESSAGE_LENGTH // 4:
                return pos + len(sep)

        return MAX_MESSAGE_LENGTH
