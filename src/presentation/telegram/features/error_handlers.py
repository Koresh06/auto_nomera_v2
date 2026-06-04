from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput


async def on_input_error(
    message: Message,
    widget: ManagedTextInput[str],
    dialog_manager: DialogManager,
    error: ValueError,
) -> None:
    await message.answer(f"❌ {error}")