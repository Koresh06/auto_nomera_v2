from aiogram import F
from aiogram.types import ContentType
from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory
from aiogram_dialog.widgets.kbd import (
    Group,
    Select,
    Back,
    Cancel,
    Next,
    Button,
    Start,
    SwitchTo,
    RequestContact,
    Column,
)

from src.domain.enums.ad import AdType
from src.presentation.telegram.features.error_handlers import on_input_error
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.features.user.shared.ad_getters import calendar_getter, getter_finish, getter_publication_service
from src.presentation.telegram.features.user.shared.ad_handlers import on_pick_slot, on_service_paid_selected
from src.presentation.telegram.utils.text_validators import capitalize_word, validate_phone_number

from .states import CreateAdSG
from .handlers import (
    on_back_to_calendar,
    on_city_input,
    on_confirm_ad,
    on_delete_photo,
    on_edit_ad,
    on_input_photo,
    on_negotiable_price,
    on_phone_input_success,
    on_phone_received_contact,
    on_plate_success,
    on_price_input_success,
    on_reuse_old_click,
)
from .getters import (
    getter_confirm,
    getter_default_ad,
    getter_duplicate_ad,
    getter_media_plate,
    getter_user_phone,
)
from .texts import PLANE_URGENT_TEXT, PLATE_BUY_TEXT, PLATE_SALE_TEXT

create_ad_dialog = Dialog(
    Window(
        Const(PLATE_SALE_TEXT, when=F["is_sale"]),
        Const(PLATE_BUY_TEXT, when=F["is_buy"]),
        Const(PLANE_URGENT_TEXT, when=F["is_urgent"]),
        TextInput(
            id="plate",
            type_factory=str,
            on_success=on_plate_success,
            on_error=on_input_error,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.plate,
        getter=getter_default_ad,
    ),
    Window(
        Const(
            "🔁 <b>Вы уже публиковали этот номер ранее.</b>\n\n"
            "Вот найденное объявление:\n"
        ),
        DynamicMedia(selector="media", when="media"),
        Format(
            "🚘 <b>Номер</b>: {plate}\n"
            "🌎 <b>Город</b>: {city}\n"
            "💰 <b>Цена</b>: {price}\n"
            "📲 <b>Связь</b>: {contacts}"
        ),
        Column(
            Button(
                Const("♻️ Опубликовать снова"),
                id="reuse_old",
                on_click=on_reuse_old_click,
            ),
            Next(Const("🆕 Создать новое объявление")),
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.duplicate_preview,
        getter=getter_duplicate_ad,
    ),
    Window(
        Const(
            '📸 <b>Пришлите фото вашего номера (если есть) или нажмите кнопку "Пропустить".</b>',
            when=~F["media"],
        ),
        Const("📸 <b>Ваше фото</b>", when="media"),
        DynamicMedia(selector="media", when="media"),
        MessageInput(
            content_types=[ContentType.PHOTO],
            func=on_input_photo,
        ),
        Button(
            Const("❌ Удалить фото"),
            id="delete_photo",
            on_click=on_delete_photo,
            when="photo",
        ),
        Next(Const("➡️ Далее"), when="media"),
        Next(Const("Пропустить"), id="skip_media", when=~F["media"]),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_plate",
            state=CreateAdSG.plate,
            style=Style(style=ButtonStyle.PRIMARY),
            when=~F["dialog_data"]["is_reuse_ad"],
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
            when=F["dialog_data"]["is_reuse_ad"],
        ),
        state=CreateAdSG.image,
        getter=getter_media_plate,
    ),
    Window(
        Const("🌎 <b>Укажите город (без сокращений):</b>"),
        TextInput(
            id="city",
            type_factory=capitalize_word,
            on_success=on_city_input,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.city,
    ),
    Window(
        Const(
            "📞 <b>Укажите Ваш номер телефона (с 8 или +7, без пробелов и лишних символов):</b>"
        ),
        RequestContact(Const("📞 Отправить номер")),
        MessageInput(
            func=on_phone_received_contact,
            content_types=[ContentType.CONTACT],
        ),
        TextInput(
            id="phone",
            type_factory=validate_phone_number,
            on_success=on_phone_input_success,
            on_error=on_input_error,
        ),
        Next(Format("{phone}"), when="phone"),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        markup_factory=ReplyKeyboardFactory(
            one_time_keyboard=True,
            resize_keyboard=True,
        ),
        state=CreateAdSG.phone,
        getter=getter_user_phone,
    ),
    Window(
        Const(
            "💰 <b>Укажите стоимость номера, за которую хотите продать, или нажмите на кнопку «Договорная».</b>\n\n"
            "📌 <b>Примеры:</b>\n\n"
            "➡️ <code>1000</code>\n"
            "➡️ <code>100000</code>\n"
            "➡️ <code>1000000</code>",
            when=F["dialog_data"]["ad_type"].in_({AdType.SALE, AdType.BUY}),
        ),
        Const(
            "⚠️ <b>Объявления, в которых не указана сумма, не принимаются.</b>\n\n"
            "💰 <b>Укажите примерную сумму, которую Вы рассчитываете получить за свой номер.</b>\n\n"
            "📌 <b>Примеры:</b>\n\n"
            "➡️ <code>1000</code>\n"
            "➡️ <code>100000</code>\n"
            "➡️ <code>1000000</code>",
            when=F["dialog_data"]["ad_type"] == AdType.URGENT_BUYOUT,
        ),
        Button(
            Const("🤝 Договорная"),
            id="negotiable_price",
            on_click=on_negotiable_price,
            when=F["dialog_data"]["ad_type"].in_({AdType.SALE, AdType.BUY}),
        ),
        TextInput(
            id="price",
            type_factory=str,
            on_success=on_price_input_success,
            on_error=on_input_error,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.price,
    ),
    Window(
        Const("Выбери слот публикации (DEV календарь)"),
        Group(
            Select(
                Format("{item.text}"),
                id="slot",
                item_id_getter=lambda s: s.id,
                items="slots",
                on_click=on_pick_slot,
            ),
            width=3,
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
            when=~F["dialog_data"]["is_reuse_ad"],
        ),
        SwitchTo(
            Const("⬅️ Назад"),
            id="back_slot",
            style=Style(style=ButtonStyle.PRIMARY),
            state=CreateAdSG.duplicate_preview,
            when=F["dialog_data"]["is_reuse_ad"],
        ),
        getter=calendar_getter,
        state=CreateAdSG.calendar,
    ),
    Window(
        Multi(
            Const(
                '⚠️ <b>Обязательно нажмите кнопку "Подтвердить" в конце этого сообщения, иначе ваше объявление не опубликуется!</b>\n\n'
                "✅ <b>Предварительный просмотр объявления:</b>\n",
            ),
            Format(
                "📋 <b>Проверьте данные:</b>\n\n"
                "🚘 <b>Номер</b>: {plate}\n"
                "🌎 <b>Город</b>: {city}\n"
                "💰 <b>Цена</b>: {price}\n"
                "📲 <b>Связь</b>: {contacts}\n\n"
                "🕐 <b>Слот</b>: {slot_day} в {slot_time}"
            ),
            when=F["dialog_data"]["ad_type"].in_({AdType.SALE, AdType.BUY}),
        ),
        Multi(
            Const(
                "✅ <b>Предварительный просмотр заявки на срочный выкуп:</b>\n",
            ),
            Format(
                "🚀 <b>СРОЧНЫЙ ВЫКУП</b>\n\n"
                "🌎 <b>Город</b>: {city}\n"
                "🚘 <b>Номер</b>: {plate}\n"
                "💰 <b>Сумма</b>: {price}\n"
                "📲 <b>Связь</b>: {contacts}"
            ),
            when=F["dialog_data"]["ad_type"] == AdType.URGENT_BUYOUT,
        ),
        DynamicMedia(selector="media", when="media"),
        Button(
            Const("✅ Подтвердить"),
            id="confirm",
            on_click=on_confirm_ad,
        ),
        Back(
            Const("⬅️ Назад"),
            on_click=on_back_to_calendar,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.confirm,
        getter=getter_confirm,
    ),
    Window(
        Const(
            "💎 <b>Сделайте своё объявление заметнее! Выберите услуги, чтобы выделить его перед публикацией:</b>"
        ),
        Group(
            Select(
                Format("{item[0]}"),
                id="selected_services",
                item_id_getter=lambda x: str(x[1]),
                items="available_services",
                on_click=on_service_paid_selected,
            ),
            width=1,
        ),
        Next(Const("⏭ Пропустить")),
        state=CreateAdSG.publication_service,
        getter=getter_publication_service,
    ),
    Window(
        Const("🤝 <b>Спасибо что выбрали Нас.</b>\n\n"),
        Format(
            "✅ Ваше объявление о продаже будет опубликовано {slot_day} в {slot_time} в нашем телеграм канале: <a href='https://t.me/{channel_username}'>{region_title}</a>\n",
            when=~F["is_auto_pub"],
        ),
        Format(
            "✅ Ваше объявление о продаже опубликовано в нашем телеграм канале: <a href='{channel_username}'>{region_title}</a>\n",
            when="is_auto_pub",
        ),
        Const("‼️ Подписывайтесь на канал, чтобы не потерять объявление!\n\n"),
        Const(
            "Для быстрой продажи рекомендуем воспользоваться платными услугами, выбрав раздел «🚀 Платные Топ услуги (NEW)» в общем меню, чтобы выделить Ваше объявление среди других.\n\n"
        ),
        Format("🔝 Подключённые услуги:\n{selected_services}."),
        DynamicMedia(selector="media", when="media"),
        Back(
            Const("Назад к Услугам!"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        Column(
            Button(
                Const("📝 Редактировать объявление"),
                id="edit_ad",
                on_click=on_edit_ad,
            ),
            Start(
                Const("🏠 Главное меню"),
                id="main_menu",
                state=UserMenuSG.menu,
            ),
        ),
        state=CreateAdSG.finish,
        getter=getter_finish,
        # on_process_result=on_process_result,
    ),
    Window(
        Const(
            "✅ <b>Спасибо за Вашу заявку.</b>"
            "<b>Если ваше объявление соответствует критериям срочного выкупа,</b> "
            "<b>то в ближайшее время с Вами свяжутся покупатели.</b>"
        ),
        Start(
            Const("🏠 Главное меню"),
            id="main_menu",
            state=UserMenuSG.menu,
        ),
        state=CreateAdSG.urgent_done,
    ),
)
