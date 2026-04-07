from __future__ import annotations

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Group, Select

from src.domain.services.ad.plate_validator import validate_plate

from .states import CreateAdSG
from .handlers import (
    on_plate_success,
    on_city_success,
    on_price_success,
    on_contacts_success,
    on_pick_slot,
)
from .getters import calendar_getter


create_ad_dialog = Dialog(
    Window(
        Const(
            "Продать:\n\n"
            "✍🏻 <b>Введите номер по примеру, который хотите продать. Не вводите ничего лишнего кроме цифр и букв вашего номера.</b>\n\n"
            "📌 <b>Примеры ввода номера:</b>\n\n"
            "<code>x111xx01</code>\n"
            "<code>oo777701</code>\n"
            "<code>9999yy01</code>",
        ),
        Const(
            "Купить:\n\n"
            "✍🏻 <b>Введите номер по примеру, который хотите купить. Не вводите ничего лишнего кроме цифр, букв и «***» нужного вам номера.</b>\n\n"
            "📌 <b>Примеры ввода номера:</b>\n\n"
            "<code>А111АА01</code>\n"
            "<code>*111**01</code>\n"
            "<code>А***АА01</code>\n\n"
            "<code>oo777701</code>\n"
            "<code>**777701</code>\n"
            "<code>oo****01</code>\n\n"
            "<code>9999yy01</code>\n"
            "<code>9999**01</code>\n"
            "<code>****yy01</code>\n\n"
        ),
        TextInput(
            id="sale_plate",
            type_factory=lambda v: validate_plate(v, allow_mask=False),
            on_success=on_plate_success,
        ),
        TextInput(
            id="bye_plate",
            type_factory=lambda v: validate_plate(v, allow_mask=True),
            on_success=on_plate_success,
        ),
        state=CreateAdSG.plate,
    ),
    Window(
        Const("Введи город"),
        TextInput(id="city", on_success=on_city_success),
        state=CreateAdSG.city,
    ),
    Window(
        Const("Введи цену (например: 245 000 руб. / Договорная)"),
        TextInput(id="price", on_success=on_price_success),
        state=CreateAdSG.price,
    ),
    Window(
        Const("Введи контакты (например: @user, +7...)"),
        TextInput(id="contacts", on_success=on_contacts_success),
        state=CreateAdSG.contacts,
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
        getter=calendar_getter,
        state=CreateAdSG.calendar,
    ),
    Window(
        Format(
            "Готово!\nСлот: {dialog_data[picked]}\nConverted: {dialog_data[converted]}"
        ),
        state=CreateAdSG.done,
    ),
)
