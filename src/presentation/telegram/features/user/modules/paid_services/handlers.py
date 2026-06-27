from decimal import Decimal
from typing import Any

from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button

from src.application.use_cases.publication_service.get_by_id import (
    GetByIdServiceDefinitionRequest,
)
from src.domain.enums.payment import PaymentPurpose
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import PublicationServiceType
from src.domain.exceptions.user import InsufficientBalance
from src.application.dtos.publication import PublicationDTO
from src.application.dtos.service_definition import ServiceDefinitionDTO
from src.application.dtos.user import UserDTO
from src.application.mediator import Mediator
from src.application.use_cases.publication.get_by_id import GetPublicationByIdRequest
from src.application.use_cases.publication_service.apply_service import (
    ApplyServiceToPublishedRequest,
)
from src.application.use_cases.publication_service.buy_pre_publication_service import (
    BuyPrePublicationServiceRequest,
)
from src.application.use_cases.publication_service.buy_publication_service import (
    BuyPublicationServiceRequest,
)
from src.application.use_cases.publication_service.priority_publish_publication import (
    PriorityPublishPublicationRequest,
)
from src.presentation.telegram.features.user.modules.payment.helpers import (
    PaymentStartParams,
    start_payment,
)


async def on_ad_selected_service(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["selected_pub_id"] = int(item_id)
    await dialog_manager.next()


@inject
async def on_confirm_buy_service(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    user_id: int = dialog_manager.dialog_data["user_id"]
    service_type_raw = dialog_manager.start_data["service_type"]
    service_type: PublicationServiceType = PublicationServiceType(service_type_raw)
    pub_id: int = dialog_manager.dialog_data["selected_pub_id"]
    definition_id: int = dialog_manager.dialog_data["definition_id"]
    definition: ServiceDefinitionDTO = await mediator.handle(
        GetByIdServiceDefinitionRequest(definition_id)
    )

    if dialog_manager.dialog_data.get("confirm_warning"):
        dialog_manager.dialog_data.pop("confirm_warning")
        try:
            await mediator.handle(
                BuyPublicationServiceRequest(
                    user_id=user_id,
                    publication_id=pub_id,
                    service_type=service_type,
                )
            )
            pub: PublicationDTO = await mediator.handle(
                GetPublicationByIdRequest(publication_id=pub_id)
            )
            if service_type == PublicationServiceType.PRIORITY_PUBLISH:
                await mediator.handle(
                    PriorityPublishPublicationRequest(publication_id=pub_id)
                )
            elif pub.status == PublicationStatus.PUBLISHED:
                await mediator.handle(
                    ApplyServiceToPublishedRequest(
                        publication_id=pub_id,
                        service_type=service_type,
                    )
                )
            await callback.answer("✅ Услуга подключена!", show_alert=True)
            await dialog_manager.done()
        except InsufficientBalance:
            await start_payment(
                dialog_manager,
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                params=PaymentStartParams(
                    purpose=PaymentPurpose.PUBLICATION_SERVICE,
                    amount=Decimal(definition.price),
                    description=definition.title,
                    purpose_id=pub_id,
                    return_state="PaidServiceSG:start",
                    return_data={},
                    meta={"service_type": service_type_raw},
                ),
            )
    else:
        dialog_manager.dialog_data["confirm_warning"] = True
        await callback.answer(
            "Нажмите ещё раз для подтверждения покупки.",
            show_alert=True,
        )


@inject
async def on_confirm_buy_pre_publication(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    user_id: int = dialog_manager.dialog_data["user_id"]
    definition_id: int = dialog_manager.dialog_data["definition_id"]
    was_active = dialog_manager.dialog_data.get("already_active_flag", False)

    definition: ServiceDefinitionDTO = await mediator.handle(
        GetByIdServiceDefinitionRequest(definition_id)
    )

    if dialog_manager.dialog_data.get("confirm_warning"):
        dialog_manager.dialog_data.pop("confirm_warning")
        try:
            await mediator.handle(BuyPrePublicationServiceRequest(user_id=user_id))
            action_text = "продлена" if was_active else "подключена"
            await callback.answer(
                f"✅ Подписка {action_text} на {definition.duration_days} дн.!",
                show_alert=True,
            )
            await dialog_manager.done()
        except InsufficientBalance:
            await start_payment(
                dialog_manager,
                user_id=callback.from_user.id,
                chat_id=callback.message.chat.id,
                params=PaymentStartParams(
                    purpose=PaymentPurpose.PRE_PUBLICATION,
                    amount=Decimal(definition.price),
                    description=definition.title,
                    return_state="PaidServiceSG:start",
                    return_data={},
                    meta={"days": definition.duration_days or 30},
                ),
            )
    else:
        dialog_manager.dialog_data["confirm_warning"] = True
        await callback.answer(
            "Нажмите ещё раз для подтверждения покупки подписки.",
            show_alert=True,
        )
