from src.domain.exceptions.base import ApplicationException
from src.domain.enums.payment import PaymentMethod


class PaymentProviderNotFoundException(ApplicationException):
    def __init__(self, method: "PaymentMethod") -> None:
        super().__init__(f"Платёжный провайдер для метода {method} не зарегистрирован")
