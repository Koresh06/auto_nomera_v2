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
            file_id=context.ad.content.image_file_id
        )
        context.ad.content = context.ad.content.with_image(new_file_id)
        service.mark_used()
