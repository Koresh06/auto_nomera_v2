from src.domain.exceptions.base import ApplicationException


class ServiceDefinitionException(ApplicationException):
    message = "Ошибка справочника услуг"

    def __init__(self, service_type: str | None = None):
        msg = f"Услуга {service_type} не найдена" if service_type else self.message
        super().__init__(msg)


class ServiceNotAvailableException(ApplicationException):
    message = "Услуга недоступна"
