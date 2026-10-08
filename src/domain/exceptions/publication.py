class PublicationDomainError(Exception):
    pass


class InvalidPublicationState(PublicationDomainError):
    """Неверное состояние публикации."""

    pass


class ServiceAlreadyAdded(PublicationDomainError):
    """Сервис уже добавлен."""

    pass


class ServiceNotAllowed(PublicationDomainError):
    """Сервис не разрешен."""

    pass


class SchedulerCancellationFailed(PublicationDomainError):
    """Не удалось гарантированно отменить запланированную задачу — старая
    задача может ещё выстрелить, продолжать (например, ставить новую задачу
    поверх) небезопасно."""

    pass
