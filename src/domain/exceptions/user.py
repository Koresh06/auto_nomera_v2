from src.domain.exceptions.base import DomainException


class UserDomainException(DomainException):
    """Базовая доменная ошибка пользователя"""

    message = "Ошибка пользователя"


class UserBlockedException(UserDomainException):
    """Пользователь заблокирован — нарушение бизнес-правила"""

    message = "Пользователь заблокирован"

    def __init__(self, tg_id: int | None = None):
        msg = f"Пользователь tg_id={tg_id} заблокирован" if tg_id else self.message
        super().__init__(msg)


class UserInvalidRegionException(UserDomainException):
    """Пользователь пытается выбрать недопустимый регион"""

    message = "Недопустимый регион для пользователя"


class UserLimitAdException(UserDomainException):
    """Пользователь превысил лимит объявлений"""

    message = "Превышен лимит объявлений"

    def __init__(self, limit: int | None = None):
        msg = f"Превышен лимит объявлений: максимум {limit}" if limit else self.message
        super().__init__(msg)


class InvalidTelegramId(UserDomainException):
    """tg_id не прошёл валидацию"""

    message = "Некорректный Telegram ID"

    def __init__(self, tg_id: int | None = None):
        msg = (
            f"Некорректный tg_id={tg_id}, должен быть положительным"
            if tg_id
            else self.message
        )
        super().__init__(msg)


class EmptyUsername(UserDomainException):
    """Имя пользователя пустое"""

    message = "Имя пользователя не может быть пустым"


class InsufficientBalance(DomainException):
    """Недостаточно средств"""

    message = "Недостаточно средств"
