import logging
from dataclasses import dataclass

from src.application.use_cases.base import UseCase, UseCaseRequest
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
    PublishPublicationUseCase,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchResult:
    success: int
    failed: list[int]


@dataclass(frozen=True, eq=False)
class PublishOverdueBatchRequest(UseCaseRequest):
    publication_ids: list[int]


@dataclass(kw_only=True)
class PublishOverdueBatchUseCase(UseCase[PublishOverdueBatchRequest, BatchResult]):
    publish_publication: PublishPublicationUseCase

    async def __call__(self, command: PublishOverdueBatchRequest) -> BatchResult:
        success = 0
        failed: list[int] = []
        for pub_id in command.publication_ids:
            try:
                await self.publish_publication(
                    PublishPublicationRequest(publication_id=pub_id)
                )
                success += 1
            except Exception:
                logger.exception(f"[PublishOverdueBatch] failed pub_id={pub_id}")
                failed.append(pub_id)
        return BatchResult(success=success, failed=failed)
