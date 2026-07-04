class AppBaseException(Exception):
    message: str = "Произошла ошибка"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)

    def __str__(self) -> str:
        return self.args[0]


class DomainException(AppBaseException):
    message = "Доменная ошибка"


class ApplicationException(AppBaseException):
    message = "Ошибка приложения"
