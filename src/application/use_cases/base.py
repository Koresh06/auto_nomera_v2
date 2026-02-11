from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar


class UseCaseRequest(ABC): ...


CT = TypeVar("CT", bound=UseCaseRequest)
CR = TypeVar("CR", bound=Any)


class UseCase(ABC, Generic[CT, CR]):
    
    @abstractmethod
    async def __call__(self, command: CT) -> CR: ...