import re


def validate_store(text: str) -> str:
    name = text.strip()
    
    url_pattern = r'(https?://|www\.|t\.me/|@\w+|tg://)'
    if re.search(url_pattern, name, re.IGNORECASE):
        raise ValueError("❌ Название не должно содержать ссылки или упоминания.")
    
    if re.search(r'@\w+', name):
        raise ValueError("❌ Название не должно содержать Telegram-теги.")
    
    if not re.match(r'^[\w\s\-\.а-яёА-ЯЁa-zA-Z0-9]+$', name):
        raise ValueError("❌ Название содержит недопустимые символы.")
    
    if len(name) < 3:
        raise ValueError("❌ Название должно быть не короче 3 символов.")
    
    if len(name) > 255:
        raise ValueError("❌ Слишком длинное название магазина.")
    
    return name.capitalize()