from src.domain.exceptions.base import ApplicationException

class UserNotFoundException(ApplicationException):
    message = "Пользователь не найден"

    def __init__(self, id: int | None = None):
        msg = f"Пользователь с id={id} не найден" if id else self.message
        super().__init__(msg)


class UserAlreadyExistsException(ApplicationException):
    message = "Пользователь уже существует"


class PaymentBlockedException(ApplicationException):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"Payments blocked for user {user_id}")
        self.user_id = user_id