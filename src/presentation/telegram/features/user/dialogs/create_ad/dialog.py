from __future__ import annotations

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
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
        Const("Введи номер (пример: Х111УХ26 или Х111УХ126)"),
        TextInput(
            id="plate",
            type_factory=lambda v: validate_plate(v, allow_mask=False),
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
        Format("Готово!\nСлот: {dialog_data[picked]}\nConverted: {dialog_data[converted]}"),
        state=CreateAdSG.done,
    ),
)
