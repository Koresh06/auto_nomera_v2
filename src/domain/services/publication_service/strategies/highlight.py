from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.services.publication_service.context import ServiceContext


class HighlightStrategy:
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None:
        new_file_id = await context.image_processor.add_red_frame(
            file_id=context.ad.content.image_file_id,
            chat_id=context.tg_id,
        )
        await context.telegram.edit_media(
            channel_id=context.region.channel_id,
            message_id=publication.channel_message_id,
            file_id=new_file_id,
            caption=context.caption,
        )
        service.mark_used()
