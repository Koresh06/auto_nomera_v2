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