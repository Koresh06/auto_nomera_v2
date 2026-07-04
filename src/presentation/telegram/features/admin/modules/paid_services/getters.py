from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram_dialog import DialogManager

from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.mediator import Mediator
from src.application.use_cases.service_difinition.get_all import GetAllServicesRequest
from src.application.use_cases.service_difinition.get_by_id import (
    GetByIdServiceDefinitionRequest,
)


@inject
async def getter_service_list(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    services: list[ServiceDefinitionDTO] = await mediator.handle(
        GetAllServicesRequest()
    )
    return {
        "services": [
            (f"{'🟢' if s.is_active else '🔴'} {s.title} — {s.price_display}", s.id)
            for s in services
        ],
    }


@inject
async def getter_service_detail(
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
    **kwargs,
) -> dict:
    service_id: int = dialog_manager.dialog_data["service_id"]
    s: ServiceDefinitionDTO = await mediator.handle(
        GetByIdServiceDefinitionRequest(id=service_id)
    )

    return {
        "service": s,
        "status_label": s.status_label,
        "toggle_label": s.toggle_label,
        "price_display": s.price_display,
        "duration_display": s.duration_display,
        "description_display": s.description_display,
        "has_duration": s.has_duration,
    }
