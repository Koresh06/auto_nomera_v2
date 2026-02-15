from typing import Any, Dict, Type, TypeVar

from src.application.use_cases.base import UseCase, UseCaseRequest


Req = TypeVar("Req", bound=UseCaseRequest)
Res = TypeVar("Res")


class Mediator:
    def __init__(self) -> None:
        self._handlers: Dict[Type[UseCaseRequest], UseCase[Any, Any]] = {}

    def register(self, request_type: Type[Req], handler: UseCase[Req, Res]) -> None:
        self._handlers[request_type] = handler

    async def handle(self, request: Req) -> Res:
        for cls in type(request).mro():
            handler = self._handlers.get(cls)
            if handler is not None:
                return await handler(request)  # type: ignore[return-value]
        raise ValueError(f"No handler registered for {type(request)}")
