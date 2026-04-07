CUSTOM_URL_PREFIX = "my://"


def build_virtual_plate_url(
    *, plate_number: str, channel_username: str, chat_id: int
) -> str:
    # формат как у тебя: my://plate|channel|chat_id
    return f"{CUSTOM_URL_PREFIX}{plate_number}|{channel_username}|{chat_id}"
