from src.application.mediator import Mediator
from src.application.use_cases.miling.execute import ExecuteMailingRequest
from src.application.use_cases.notification.notify_pre_publication_users import (
    NotifyPrePublicationUsersRequest,
)
from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.application.use_cases.payment.mark import MarkPaymentFailedRequest
from src.application.use_cases.publication.publish_publication import (
    PublishPublicationRequest,
)

from src.application.use_cases.publication_service.unpin_message import (
    UnpinMessageRequest,
)
from src.domain.enums.miling import MailingType


def register_taskiq_tasks(broker, *, container):

    @broker.task(name="publish_publication")
    async def publish_publication(publication_id: int) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                PublishPublicationRequest(publication_id=publication_id)
            )

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
            await mediator.handle(NotifyPrePublicationUsersRequest(ad_id=ad_id))

    @broker.task(name="confirm_payment")
    async def confirm_payment(external_id: str) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(ConfirmPaymentRequest(external_id=external_id))

    @broker.task(name="mark_payment_failed")
    async def mark_payment_failed(external_id: str) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(MarkPaymentFailedRequest(external_id=external_id))

    @broker.task(name="execute_mailing")
    async def execute_mailing(
        mail_type: str,
        from_chat_id: int,
        message_id: int,
        region_id: int | None = None,
    ) -> None:
        async with container() as request_container:
            mediator = await request_container.get(Mediator)
            await mediator.handle(
                ExecuteMailingRequest(
                    mail_type=MailingType(mail_type),
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    region_id=region_id,
                )
            )

    return {
        "publish_publication": publish_publication,
        "unpin_message": unpin_message,
        "notify_pre_publication_users": notify_pre_publication_users,
        "confirm_payment": confirm_payment,
        "mark_payment_failed": mark_payment_failed,
        "execute_mailing": execute_mailing,
    }
