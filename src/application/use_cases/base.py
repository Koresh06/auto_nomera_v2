from abc import ABC, abstractmethod
from typing import Generic, TypeVar


class UseCaseRequest(ABC):
    pass

ReqT = TypeVar("ReqT", bound=UseCaseRequest)
ResT = TypeVar("ResT")

class UseCase(ABC, Generic[ReqT, ResT]):
    @abstractmethod
    async def __call__(self, command: ReqT) -> ResT:
        raise NotImplementedError
