from src.domain.exceptions.base import ApplicationException


class PublicationNotFoundException(ApplicationException):
    message = "Публикация не найдена"

    def __init__(self, publication_id: int | None = None):
        msg = (
            f"Публикация с id={publication_id} не найдена"
            if publication_id
            else self.message
        )
        super().__init__(msg)
