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
        # Сначала извлекаем блоки кода, чтобы не обрабатывать их содержимое
        code_blocks: list[str] = []
        placeholder_prefix = "\x00CODEBLOCK"

        def replace_code_block(match: re.Match) -> str:
            lang = match.group(1) or ""
            code = match.group(2)
            escaped_code = html.escape(code.strip())
            if lang:
                block = f'<pre><code class="language-{html.escape(lang)}">{escaped_code}</code></pre>'
            else:
                block = f"<pre>{escaped_code}</pre>"
            idx = len(code_blocks)
            code_blocks.append(block)
            return f"{placeholder_prefix}{idx}\x00"

        # Заменяем блоки кода на плейсхолдеры
        result = re.sub(
            r"```(\w*)\n(.*?)```",
            replace_code_block,
            text,
            flags=re.DOTALL,
        )

        # Экранируем HTML-символы (вне блоков кода)
        result = html.escape(result)

        # Инлайн-код: `code`
        result = re.sub(r"`([^`]+)`", r"<code>\1</code>", result)

        # Жирный: **text** или __text__
        result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
        result = re.sub(r"__(.+?)__", r"<b>\1</b>", result)

        # Курсив: *text* или _text_
        result = re.sub(r"\*(.+?)\*", r"<i>\1</i>", result)
        result = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<i>\1</i>", result)

        # Зачёркнутый: ~~text~~
        result = re.sub(r"~~(.+?)~~", r"<s>\1</s>", result)

        # Заголовки: # Header → жирный текст
        result = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", result, flags=re.MULTILINE)

        # Ссылки: [text](url)
        result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', result)

        # Маркированные списки: - item или * item
        result = re.sub(r"^[\-\*]\s+", "• ", result, flags=re.MULTILINE)

        # Нумерованные списки оставляем как есть (Telegram отображает нормально)

        # Восстанавливаем блоки кода
        for idx, block in enumerate(code_blocks):
            result = result.replace(
                html.escape(f"{placeholder_prefix}{idx}\x00"),
                block,
            )

        return result.strip()

    def _split_message(self, text: str) -> list[str]:
        """Разбивает сообщение на части ≤ MAX_MESSAGE_LENGTH символов.

        Старается не разрывать блоки кода и параграфы.
        """
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        parts: list[str] = []
        remaining = text

        while remaining:
            if len(remaining) <= MAX_MESSAGE_LENGTH:
                parts.append(remaining)
                break

            # Ищем подходящее место для разрыва
            chunk = remaining[:MAX_MESSAGE_LENGTH]
            split_pos = self._find_split_position(chunk)

            parts.append(remaining[:split_pos].rstrip())
            remaining = remaining[split_pos:].lstrip()

        return parts if parts else ["(пустой ответ)"]

    def _find_split_position(self, chunk: str) -> int:
        """Находит оптимальное место для разрыва сообщения."""
        # Приоритет: конец блока кода → двойной перенос → одинарный перенос → пробел
        for sep in ["</pre>", "\n\n", "\n", " "]:
            # Ищем последнее вхождение разделителя
            pos = chunk.rfind(sep)
            if pos > MAX_MESSAGE_LENGTH // 4:  # Не разрываем слишком рано
                return pos + len(sep)

        # Если ничего не нашли — режем по лимиту
        return MAX_MESSAGE_LENGTH
