class UserDomainError(Exception):
    pass


class InvalidTelegramId(UserDomainError):
    """Не корректный Telegram ID."""

    pass


class EmptyUsername(UserDomainError):
    """Пустое имя пользователя."""

    pass
