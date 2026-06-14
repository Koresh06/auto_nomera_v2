from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.services.publication_service.context import ServiceContext


class PinStrategy:
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None:
        if publication.channel_message_id is None:
            service.mark_used()
            return
        unpin_at = context.time_resolver.resolve_unpin_time(
            publication.published_at_utc,
            service.params,
        )
        await context.telegram.pin_message(
            channel_id=context.region.channel_id,
            message_id=publication.channel_message_id,
        )
        await context.scheduler.schedule_unpin(
            channel_id=context.region.channel_id,
            message_id=publication.channel_message_id,
            run_at_utc=unpin_at,
        )
        service.mark_used()
