from src.application.mediator import Mediator
from src.application.use_cases.notification.notify_pre_publication_users import NotifyPrePublicationUsersRequest
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)

from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
)


def register_taskiq_tasks(broker, *, container):

    @broker.task(name="publish_publication")
    async def publish_publication(publication_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(PublishPublicationRequest(publication_id=publication_id))

    @broker.task(name="unpin_message")
    async def unpin_message(channel_id: int, message_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                UnpinMessageRequest(channel_id=channel_id, message_id=message_id)
            )

    @broker.task(name="notify_pre_publication_users")
    async def notify_pre_publication_users(ad_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                NotifyPrePublicationUsersRequest(ad_id=ad_id)
            )

    return {
        "publish_publication": publish_publication,
        "unpin_message": unpin_message,
        "notify_pre_publication_users": notify_pre_publication_users,
    }
