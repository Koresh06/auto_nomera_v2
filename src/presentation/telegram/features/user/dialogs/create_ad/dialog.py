from aiogram import F
from aiogram.types import ContentType
from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput, MessageInput
from aiogram_dialog.widgets.kbd import (
    Group,
    Select,
    Back,
    Cancel,
    Next,
    Button,
    SwitchTo,
    RequestContact,
)
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory

from .states import CreateAdSG
from .handlers import (
    on_back_to_calendar,
    on_confirm,
    on_delete_photo,
    on_input_error,
    on_input_photo,
    on_negotiable_price,
    on_phone_input_success,
    on_phone_received_contact,
    on_plate_success,
    on_pick_slot,
)
from .getters import (
    calendar_getter,
    getter_confirm,
    getter_default_ad,
    getter_media_plate,
    getter_user_phone,
)
from .validators import capitalize_word, validate_phone_number, validate_price
from .texts import PLATE_BUY_TEXT, PLATE_SALE_TEXT


create_ad_dialog = Dialog(
    Window(
        Const(PLATE_SALE_TEXT, when=F["is_sale"] | F["is_urgent"]),
        Const(PLATE_BUY_TEXT, when=F["is_buy"]),
        TextInput(
            id="plate",
            type_factory=str,
            on_success=on_plate_success,
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=CreateAdSG.plate,
        getter=getter_default_ad,
    ),
    # Window(
    #     Const(
    #         "🔁 <b>Вы уже публиковали этот номер ранее.</b>\n\n"
    #         "Вот найденное объявление:\n"
    #     ),
    #     DynamicMedia(selector="media", when="media"),
    #     Format("{ad_text}"),
    #     Column(
    #         Button(
    #             Const("♻️ Опубликовать снова"),
    #             id="reuse_old",
    #             on_click=on_reuse_old_click,
    #         ),
    #         Next(Const("🆕 Создать новое объявление")),
    #     ),
    #     Back(Const("⬅️ Назад")),
    #     state=SellNumberSG.duplicate_preview,
    #     getter=getter_duplicate_ad,
    # ),
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
        ),
        state=CreateAdSG.image,
        getter=getter_media_plate,
    ),
    Window(
        Const("🌎 <b>Укажите город (без сокращений):</b>"),
        TextInput(
            id="city",
            type_factory=capitalize_word,
            on_success=Next(),
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
            "➡️ <code>1000000</code>"
        ),
        Button(
            Const("🤝 Договорная"),
            id="negotiable_price",
            on_click=on_negotiable_price,
        ),
        TextInput(
            id="price",
            type_factory=validate_price,
            on_success=Next(),
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
        ),
        getter=calendar_getter,
        state=CreateAdSG.calendar,
    ),
    Window(
        Const(
            '⚠️ <b>Обязательно нажмите кнопку "Подтвердить" в конце этого сообщения, иначе ваше объявление не опубликуется!</b>\n\n'
            "✅ <b>Предварительный просмотр объявления:</b>\n"
        ),
        Format(
            "📋 <b>Проверьте данные:</b>\n\n"
            "🚘 Номер: {plate}\n"
            "🌎 Город: {city}\n"
            "💰 Цена: {price}\n"
            "📲 Телефон: {phone}\n\n"
            "🕐 Слот: {slot_day} в {slot_time}\n"
        ),
        DynamicMedia(selector="media", when="media"),
        Button(
            Const("✅ Подтвердить"),
            id="confirm",
            on_click=on_confirm,
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
        Const("Успешно!!!"),
        state=CreateAdSG.done,
    )
)
