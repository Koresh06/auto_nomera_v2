from src.domain.exceptions.base import ApplicationException


class RegionNotFoundException(ApplicationException):
    message = "Регион не найден"

    def __init__(self, region_id: int | None = None):
        msg = f"Регион с id={region_id} не найден" if region_id else self.message
        super().__init__(msg)
