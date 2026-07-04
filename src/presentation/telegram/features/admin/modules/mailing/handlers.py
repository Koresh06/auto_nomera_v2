from dishka.integrations.aiogram_dialog import inject, FromDishka
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select

from src.domain.enums.miling import MailingType
from src.application.mediator import Mediator
from src.application.use_cases.miling.enqueue import EnqueueMailingRequest
from src.presentation.telegram.features.admin.modules.mailing.states import MailingSG


async def on_choose_type(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    mail_type = MailingType(button.widget_id)
    dialog_manager.dialog_data["mail_type"] = mail_type.value

    if mail_type == MailingType.TO_REGION:
        await dialog_manager.switch_to(MailingSG.choose_region)
    else:
        await dialog_manager.switch_to(MailingSG.compose)


async def on_choose_region(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    dialog_manager.dialog_data["region_id"] = int(item_id)
    await dialog_manager.next()


async def on_message_received(
    message: Message,
    widget,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.dialog_data["from_chat_id"] = message.chat.id
    dialog_manager.dialog_data["message_id"] = message.message_id

    await message.bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await dialog_manager.next()


@inject
async def on_mailing_confirm(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mediator: FromDishka[Mediator],
) -> None:
    data = dialog_manager.dialog_data

    await mediator.handle(
        EnqueueMailingRequest(
            mail_type=MailingType(data["mail_type"]),
            from_chat_id=data["from_chat_id"],
            message_id=data["message_id"],
            region_id=data.get("region_id"),
        )
    )

    await callback.answer(
        "🚀 Рассылка запущена! Отчёт придёт по завершении.", show_alert=True
    )
    await dialog_manager.done()
