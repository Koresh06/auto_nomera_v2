from src.domain.exceptions.base import DomainException


class PaymentNotFoundException(DomainException):
    message = "Платеж не найден"

    def __init__(self, external_id: str | None = None):
        msg = f"Платеж с external_id={external_id} не найден" if external_id else self.message
        super().__init__(msg)