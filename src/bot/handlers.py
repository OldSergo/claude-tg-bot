import logging

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.enums import ChatAction, ParseMode

from src.bot.filters import AdminFilter
from src.services.claude_service import ClaudeService
from src.services.formatter import MessageFormatter

logger = logging.getLogger(__name__)

router = Router()

# Общие сервисы (инициализируются один раз)
claude_service = ClaudeService()
formatter = MessageFormatter()


def _extract_question(message: Message, bot_username: str) -> str | None:
    """Извлекает текст вопроса, убирая упоминание бота."""
    if not message.text:
        return None

    text = message.text
    # Убираем @username бота из текста
    mention = f"@{bot_username}"
    text = text.replace(mention, "").strip()

    return text if text else None


def _is_bot_mentioned(message: Message, bot_username: str) -> bool:
    """Проверяет, что бот упомянут через @username в сообщении."""
    if not message.entities:
        return False

    for entity in message.entities:
        if entity.type == "mention":
            mention_text = message.text[entity.offset : entity.offset + entity.length]
            if mention_text.lower() == f"@{bot_username.lower()}":
                return True

    return False


@router.message(AdminFilter())
async def handle_mention(message: Message, bot: Bot) -> None:
    """Обработчик сообщений с упоминанием бота от администратора."""
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    if not bot_username:
        return

    # Проверяем, что бот упомянут
    if not _is_bot_mentioned(message, bot_username):
        return

    # Извлекаем вопрос
    question = _extract_question(message, bot_username)
    if not question:
        await message.reply("Напишите вопрос после упоминания бота.")
        return

    user = message.from_user
    logger.info(
        "Вопрос от %s (ID: %d): %s",
        user.full_name if user else "Unknown",
        user.id if user else 0,
        question[:100],
    )

    # Отправляем "typing" статус
    await message.answer_chat_action(ChatAction.TYPING)

    # Получаем ответ от Claude
    answer = await claude_service.ask(question)

    # Форматируем и отправляем
    parts = formatter.format_for_telegram(answer)

    for i, part in enumerate(parts):
        try:
            if i == 0:
                await message.reply(part, parse_mode=ParseMode.HTML)
            else:
                await message.answer(part, parse_mode=ParseMode.HTML)
        except Exception:
            # Если HTML-парсинг упал — отправляем без форматирования
            logger.warning("Ошибка HTML-парсинга, отправляю без форматирования")
            if i == 0:
                await message.reply(part, parse_mode=None)
            else:
                await message.answer(part, parse_mode=None)
