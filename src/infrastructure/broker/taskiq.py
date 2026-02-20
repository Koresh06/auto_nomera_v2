from typing import Awaitable, Callable

from src.application.mediator import Mediator
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)

from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
)


# def register_taskiq_tasks(broker, *, mediator: Mediator):
    
#     @broker.task
#     async def publish_publication(publication_id: int) -> None:
#         await mediator.handle(PublishPublicationRequest(publication_id=publication_id))

#     @broker.task
#     async def unpin_message(channel_id: int, message_id: int) -> None:
#         await mediator.handle(UnpinMessageRequest(channel_id=channel_id, message_id=message_id))

#     return {
#         "publish_publication": publish_publication,
#         "unpin_message": unpin_message,
#     }

def register_taskiq_tasks(broker, *, get_mediator: Callable[[], Awaitable[Mediator]]):

    @broker.task(name="publish_publication")
    async def publish_publication(publication_id: int) -> None:
        mediator = await get_mediator()
        await mediator.handle(PublishPublicationRequest(publication_id=publication_id))

    @broker.task(name="unpin_message")
    async def unpin_message(channel_id: int, message_id: int) -> None:
        mediator = await get_mediator()
        await mediator.handle(UnpinMessageRequest(channel_id=channel_id, message_id=message_id))

    return {
        "publish_publication": publish_publication,
        "unpin_message": unpin_message,
    }