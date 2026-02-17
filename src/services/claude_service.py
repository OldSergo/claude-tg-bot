import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Таймаут на выполнение команды Claude (секунды)
CLAUDE_TIMEOUT = 300


class ClaudeService:
    """Сервис для взаимодействия с Claude Code CLI.

    Поддерживает общий контекст разговора через session_id.
    """

    def __init__(self) -> None:
        self._session_id: str | None = None

    async def ask(self, question: str) -> str:
        """Отправляет вопрос в Claude Code CLI и возвращает текстовый ответ."""
        cmd = self._build_command(question)
        logger.info("Запуск Claude CLI: %s", " ".join(cmd))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=CLAUDE_TIMEOUT,
            )

            if process.returncode != 0:
                error_text = stderr.decode().strip()
                stdout_text = stdout.decode().strip()
                logger.error(
                    "Claude CLI ошибка (код %d)\nstderr: %s\nstdout: %s",
                    process.returncode, error_text, stdout_text,
                )
                return f"⚠️ Ошибка Claude CLI:\n{error_text or stdout_text}"

            return self._parse_response(stdout.decode())

        except asyncio.TimeoutError:
            logger.error("Claude CLI таймаут (%d сек)", CLAUDE_TIMEOUT)
            if process:
                process.kill()
            return "⚠️ Claude не ответил в течение отведённого времени. Попробуйте позже."

        except Exception as e:
            logger.exception("Непредвиденная ошибка при вызове Claude CLI")
            return f"⚠️ Ошибка: {e}"

    def reset_session(self) -> None:
        """Сбрасывает текущую сессию (контекст разговора)."""
        self._session_id = None
        logger.info("Сессия Claude сброшена")

    def _build_command(self, question: str) -> list[str]:
        """Формирует команду для запуска CLI."""
        cmd = ["claude", "-p", question, "--output-format", "json", "--dangerously-skip-permissions"]

        if self._session_id:
            cmd.extend(["--resume", self._session_id])

        return cmd

    def _parse_response(self, raw: str) -> str:
        """Парсит JSON-ответ Claude CLI, извлекает текст и session_id."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Если CLI вернул не JSON — возвращаем как есть
            logger.warning("Claude CLI вернул не-JSON ответ")
            return raw.strip()

        # Сохраняем session_id для продолжения разговора
        session_id = data.get("session_id")
        if session_id:
            self._session_id = session_id
            logger.info("Session ID обновлён: %s", session_id)

        # Извлекаем текстовый результат
        result = data.get("result", "")
        if isinstance(result, str):
            return result.strip()

        # Если result — это список блоков (stream-json формат)
        if isinstance(result, list):
            texts = []
            for block in result:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return "\n".join(texts).strip()

        return str(result).strip()
