import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Настройки приложения из переменных окружения."""

    bot_token: str = ""
    admin_ids: list[int] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

        raw_ids = os.getenv("ADMIN_IDS", "")
        if not raw_ids:
            raise ValueError("ADMIN_IDS не установлен")

        admin_ids = [int(uid.strip()) for uid in raw_ids.split(",") if uid.strip()]
        if not admin_ids:
            raise ValueError("ADMIN_IDS пуст — укажите хотя бы одного администратора")

        return cls(bot_token=bot_token, admin_ids=admin_ids)


settings = Settings.from_env()
