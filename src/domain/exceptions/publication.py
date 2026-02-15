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
