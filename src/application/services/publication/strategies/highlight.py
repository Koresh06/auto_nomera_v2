from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.domain.enums.publication import PublicationStatus
from src.application.services.publication.context import ServiceContext


class HighlightStrategy:
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None:
        if context.ad.content is None:
            service.mark_used()
            return

        new_file_id = await context.image_processor.add_red_frame(
            file_id=context.ad.content.image_file_id,
            chat_id=context.tg_id,
        )

        if publication.status == PublicationStatus.PUBLISHED:
            # уже опубликовано — редактируем сообщение в канале
            await context.telegram.edit_media(
                channel_id=context.region.channel_id,
                message_id=publication.channel_message_id,
                file_id=new_file_id,
                caption=context.caption,
            )
        else:
            # ещё не опубликовано — меняем file_id для последующей публикации
            context.highlight_file_id = new_file_id  # ← передаём через контекст

        service.mark_used()