from src.domain.exceptions.base import ApplicationException

class UserNotFoundException(ApplicationException):
    message = "Пользователь не найден"

    def __init__(self, tg_id: int | None = None):
        msg = f"Пользователь с tg_id={tg_id} не найден" if tg_id else self.message
        super().__init__(msg)


class UserAlreadyExistsException(ApplicationException):
    message = "Пользователь уже существует"