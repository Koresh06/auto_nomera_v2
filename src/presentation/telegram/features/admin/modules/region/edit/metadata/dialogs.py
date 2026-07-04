from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Cancel, Column, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.style import Style

from src.presentation.telegram.features.admin.modules.region.edit.states import (
    EditRegionMetadataSG,
)
from src.presentation.telegram.features.error_handlers import on_input_error
from .handlers import on_metadata_url_success
from .getters import getter_metadata_menu
from .validators import validate_url

edit_region_metadata_dialog = Dialog(
    Window(
        Multi(
            Const("🔗 <b>Соцсети и каналы</b>\n"),
            Format("Telegram: {tg_group_url}"),
            Format("VK: {vk_group_url}"),
            Format("Макс: {max_channel_url}"),
            sep="\n",
        ),
        Column(
            SwitchTo(
                Const("📱 Telegram-группа"),
                id="edit_tg",
                state=EditRegionMetadataSG.tg_group_url,
            ),
            SwitchTo(
                Const("🔵 VK-группа"),
                id="edit_vk",
                state=EditRegionMetadataSG.vk_group_url,
            ),
            SwitchTo(
                Const("📺 Макс-канал"),
                id="edit_max",
                state=EditRegionMetadataSG.max_channel_url,
            ),
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionMetadataSG.menu,
        getter=getter_metadata_menu,
        disable_web_page_preview=True,
    ),
    Window(
        Format(
            "📱 <b>Telegram-группа</b>\n\n"
            "Текущее: {tg_group_url}\n"
            "Введите ссылку (или <code>-</code> для очистки):"
        ),
        TextInput(
            id="tg_input",
            type_factory=validate_url,
            on_success=on_metadata_url_success,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionMetadataSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionMetadataSG.tg_group_url,
        getter=getter_metadata_menu,
        disable_web_page_preview=True,
    ),
    Window(
        Format(
            "🔵 <b>VK-группа</b>\n\n"
            "Текущее: {vk_group_url}\n"
            "Введите ссылку (или <code>-</code> для очистки):"
        ),
        TextInput(
            id="vk_input",
            type_factory=validate_url,
            on_success=on_metadata_url_success,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionMetadataSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionMetadataSG.vk_group_url,
        getter=getter_metadata_menu,
        disable_web_page_preview=True,
    ),
    Window(
        Format(
            "📺 <b>Макс-канал</b>\n\n"
            "Текущее: {max_channel_url}\n"
            "Введите ссылку (или <code>-</code> для очистки):"
        ),
        TextInput(
            id="max_input",
            type_factory=validate_url,
            on_success=on_metadata_url_success,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=EditRegionMetadataSG.menu,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=EditRegionMetadataSG.max_channel_url,
        getter=getter_metadata_menu,
        disable_web_page_preview=True,
    ),
)
