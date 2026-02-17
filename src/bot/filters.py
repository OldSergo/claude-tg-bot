from aiogram.filters import Filter
from aiogram.types import Message

from src.config import settings


class AdminFilter(Filter):
    """Фильтр: пропускает сообщения только от администраторов из ADMIN_IDS."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        return message.from_user.id in settings.admin_ids
