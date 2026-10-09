import re

from src.presentation.telegram.utils.text_validators import (
    MAX_TEXT_FIELD_LEN,
    capitalize_word,
)


def validate_store(text: str) -> str:
    name = text.strip()

    url_pattern = r"(https?://|www\.|t\.me/|@\w+|tg://)"
    if re.search(url_pattern, name, re.IGNORECASE):
        raise ValueError("❌ Название не должно содержать ссылки или упоминания.")

    if re.search(r"@\w+", name):
        raise ValueError("❌ Название не должно содержать Telegram-теги.")

    if not re.match(r"^[\w\s\-\.а-яёА-ЯЁa-zA-Z0-9]+$", name):
        raise ValueError("❌ Название содержит недопустимые символы.")

    if len(name) < 3:
        raise ValueError("❌ Название должно быть не короче 3 символов.")

    # колонка ads.shop_name — VARCHAR(128); раньше проверка была на 255,
    # и название 129..255 символов роняло сохранение
    if len(name) > MAX_TEXT_FIELD_LEN:
        raise ValueError("❌ Слишком длинное название магазина.")

    return capitalize_word(name)
