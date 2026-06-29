from src.domain.exceptions.base import ApplicationException


class StoreAlreadyExistsException(ApplicationException):
    message = "Магазин уже существует"

    def __init__(self, ad_id: int | None = None):
        msg = f"Магазин с id={ad_id} уже существует у этого пользователя" if ad_id else self.message
        super().__init__(msg)


class StoreItemsAlreadyExistException(ApplicationException):
    message = "Номера уже есть в магазине"

    def __init__(self, plates: list[str] | None = None):
        msg = (
            "Следующие номера уже есть в вашем магазине:\n"
            + "\n".join(f"• {p}" for p in plates)
            if plates else self.message
        )
        super().__init__(msg)