import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value.strip())
        return value.strip()
    except (KeyError, ZoneInfoNotFoundError):
        raise ValueError(f"Неизвестный часовой пояс: {value}")
    

def validate_channel_id(value: str) -> int:
    try:
        channel_id = int(value.strip())
    except ValueError:
        raise ValueError("ID канала должен быть числом, например: -1001234567890")
    
    if channel_id > 0:
        raise ValueError("ID канала должен быть отрицательным числом, например: -1001234567890")
    
    return channel_id


def validate_channel_username(value: str) -> str:
    username = value.strip().lstrip("@")
    
    if not username:
        raise ValueError("Username не может быть пустым")
    
    if len(username) < 3:
        raise ValueError("Username слишком короткий, минимум 3 символа")
    
    if not username.replace("_", "").isalnum():
        raise ValueError("Username может содержать только буквы, цифры и подчёркивание")
    
    return username


@dataclass(frozen=True)
class UrlValidator:
    pattern: re.Pattern
    error_message: str

    def __call__(self, value: str) -> str:
        value = value.strip()

        if not self.pattern.match(value):
            raise ValueError(self.error_message)

        return value


validate_tg_url = UrlValidator(
    pattern=re.compile(r'^https://t\.me/[\w\-]+$'),
    error_message="❌ Неверный формат. Пример: https://t.me/mygroup",
)

validate_vk_url = UrlValidator(
    pattern=re.compile(r'^https://vk\.com/[\w\-]+$'),
    error_message="❌ Неверный формат. Пример: https://vk.com/mygroup",
)

validate_max_url = UrlValidator(
    pattern=re.compile(r'^https?://[\w\-.]+(?:\.[a-z]{2,})(?:/[^\s]*)?$', re.IGNORECASE),
    error_message="❌ Неверный формат. Пример: https://max.ru/channel",
)