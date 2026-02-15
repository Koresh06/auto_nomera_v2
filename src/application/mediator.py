from typing import Any, Dict, Type, TypeVar

from src.application.use_cases.base import UseCase, UseCaseRequest


Req = TypeVar("Req", bound=UseCaseRequest)
Res = TypeVar("Res")


class Mediator:
    def __init__(self) -> None:
        self._handlers: Dict[
            Type[UseCaseRequest],
            UseCase[Any, Any],
        ] = {}

    def register(
        self,
        request_type: Type[Req],
        handler: UseCase[Req, Res],
    ) -> None:
        """Регистрирует UseCase по типу запроса."""
        self._handlers[request_type] = handler

    async def handle(self, request: Req) -> Res:
        handler = self._handlers.get(type(request))

        if handler is None:
            raise ValueError(f"No handler registered for {type(request)}")

        return await handler(request)