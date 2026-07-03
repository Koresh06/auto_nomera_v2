from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import (
    Button,
    Select,
    ScrollingGroup,
    SwitchTo,
    Cancel,
    Back,
)
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput

from src.presentation.telegram.features.error_handlers import on_input_error

from .states import (
    AdminManagementSG,
)
from .getters import (
    getter_admins_list,
    getter_admin_detail,
    getter_add_confirm,
)
from .handlers import (
    on_admin_selected,
    on_revoke_admin,
    on_add_tg_id_input,
    on_promote_admin,
)

admin_management_dialog = Dialog(
    Window(
        Const("👑 <b>Управление администраторами</b>\n"),
        Const("На данный момент администраторов нет.", when=~F["has_admins"]),
        Const("Выберите администратора из списка:", when="has_admins"),
        ScrollingGroup(
            Select(
                Format("🛡 {item.full_name} — {item.tg_id}"),
                id="admin_select",
                items="admins",
                item_id_getter=lambda item: item.tg_id,
                on_click=on_admin_selected,
            ),
            id="admins_scroll",
            width=1,
            height=10,
            hide_on_single_page=True,
            when="has_admins",
        ),
        SwitchTo(
            Const("❇️ Добавить администратора"),
            id="to_add",
            state=AdminManagementSG.add_input,
        ),
        Cancel(Const("⬅️ Назад")),
        state=AdminManagementSG.menu,
        getter=getter_admins_list,
    ),
    Window(
        Format(
            "👤 <b>Профиль администратора</b>\n\n"
            "🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
            "🔗 <b>Username:</b> {username}\n"
            "📛 <b>Имя:</b> {full_name}\n"
            "📞 <b>Телефон:</b> {phone}"
        ),
        Button(
            Const("❌ Снять права администратора"),
            id="revoke_admin",
            on_click=on_revoke_admin,
        ),
        Back(Const("⬅️ Назад")),
        state=AdminManagementSG.admin_detail,
        getter=getter_admin_detail,
    ),
    Window(
        Const(
            "🔎 <b>Введите Telegram ID пользователя</b>\n\n"
            "📌 Пример: <code>123456789</code>\n\n"
            "Пользователь должен хотя бы раз зайти в бота."
        ),
        TextInput(
            id="add_tg_input",
            on_success=on_add_tg_id_input,
            on_error=on_input_error,
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_menu",
            state=AdminManagementSG.menu,
        ),
        state=AdminManagementSG.add_input,
    ),
    Window(
        Format(
            "👤 <b>Найден пользователь</b>\n\n"
            "🆔 <b>ID:</b> <code>{user.tg_id}</code>\n"
            "🔗 <b>Username:</b> {username}\n"
            "🛡 <b>Текущий статус:</b> {role_label}"
        ),
        Button(
            Const("✅ Назначить администратором"),
            id="promote_admin",
            on_click=on_promote_admin,
            when=~F["is_admin"] & ~F["is_super"],
        ),
        Const("\n⚠️ Уже администратор", when="is_admin"),
        Const("\n👑 Супер-админ из конфига", when="is_super"),
        Back(Const("⬅️ Назад")),
        state=AdminManagementSG.add_confirm,
        getter=getter_add_confirm,
    ),
)
