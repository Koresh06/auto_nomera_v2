from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.kbd import Cancel

from src.presentation.telegram.features.user.modules.profile.getters import profile_getter

from .states import ProfileSG


profile_dialog = Dialog(
    Window(
        Format(
            "📌 <b>Ваш профиль</b> 📌\n\n"
            "💎 <b>Имя:</b> {user.full_name}\n"
           "🌎 <b>Регион:</b> <a href='https://t.me/{region.channel_username}'>{region.title}</a>\n"
            "📣 <b>Количество объявлений:</b> {count_ads}\n"
            "💰 <b>Ваш баланс:</b> {user.balance_display}\n"
        ),
        Cancel(Const("🏠 Главное меню")),
        getter=profile_getter,
        state=ProfileSG.start,
    )
)