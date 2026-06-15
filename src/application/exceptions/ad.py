from src.domain.exceptions.base import ApplicationException


class AdNotFoundException(ApplicationException):
    message = "Объявление не найдено"

    def __init__(self, ad_id: int | None = None):
        msg = f"Объявление с id={ad_id} не найдено" if ad_id else self.message
        super().__init__(msg)


class AdAlreadyProcessedException(ApplicationException):
    message = "Объявление уже обработано"

    def __init__(self, ad_id: int | None = None):
        msg = f"Объявление с id={ad_id} уже обработано" if ad_id else self.message
        super().__init__(msg)