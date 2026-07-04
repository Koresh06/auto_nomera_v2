from src.domain.exceptions.base import DomainException


class PaymentNotFoundByExternalException(DomainException):
    message = "Платеж не найден"

    def __init__(self, external_id: str | None = None):
        msg = (
            f"Платеж с external_id={external_id} не найден"
            if external_id
            else self.message
        )
        super().__init__(msg)


class PaymentNotFoundByIdException(DomainException):
    message = "Платеж не найден"

    def __init__(self, id: int | None = None):
        msg = f"Платеж с id={id} не найден" if id else self.message
        super().__init__(msg)


class PaymnetNotFountPurposeException(DomainException):
    message = "Платеж не найден"

    def __init__(self, purpose: str | None = None):
        msg = f"Платеж с purpose={purpose} не найден" if purpose else self.message
        super().__init__(msg)
