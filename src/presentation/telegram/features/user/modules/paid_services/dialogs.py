from aiogram import F
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.text import Const, Format, List
from aiogram_dialog.widgets.kbd import (
    ScrollingGroup,
    Select,
    Start,
    Group,
    Next,
    Cancel,
    Back,
    Row,
    PrevPage,
    NextPage,
    Button,
)
from aiogram_dialog.widgets.style import Style

from src.domain.enums.publication_service import PublicationServiceType
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG
from src.presentation.telegram.widgets.smart_scroll_text import SmartScrollingText

from .states import BuyServiceSG, PaidServiceSG, PrePublicationSG
from .getters import (
    getter_buy_service_confirm,
    getter_connected_services_user,
    getter_current_services,
    getter_pre_publication_confirm,
    getter_user_ads_for_service,
)
from .handlers import (
    on_ad_selected_service,
    on_confirm_buy_pre_publication,
    on_confirm_buy_service,
)

paid_service_dialog = Dialog(
    Window(
        List(
            field=Format(
                "<b><u>{item[name]}</u></b>\n"
                "{item[description]}\n"
                "<b>Срок:</b> {item[duration_text]}\n"
                "<b>Цена:</b> <i>{item[price_text]}</i>\n"
            ),
            items="services",
            id="services_list",
        ),
        Start(
            Format("{pre_publication_name}"),
            id="buy_pre_publication",
            state=PrePublicationSG.confirm,
            style=Style(style=ButtonStyle.SUCCESS),
        ),
        Group(
            Start(
                Format("{priority_name}"),
                id="buy_priority",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.PRIORITY_PUBLISH.value},
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            Start(
                Format("{autopublish_name}"),
                id="buy_auto",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.AUTOPUBLISH.value},
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            Start(
                Format("{pin_name}"),
                id="buy_pin",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.PIN.value},
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            Start(
                Format("{highlight_name}"),
                id="buy_highlight",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.HIGHLIGHT.value},
                style=Style(style=ButtonStyle.SUCCESS),
            ),
            width=2,
        ),
        Next(Const("📂 Подключённые услуги")),
        Start(
            Const("⬅️ Назад"),
            id="general_menu",
            state=UserMenuSG.menu,
            mode=StartMode.RESET_STACK,
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceSG.start,
        getter=getter_current_services,
    ),
    Window(
        Const("📂 <b>Подключённые услуги</b>\n"),
        Const("Пока нет подключённых услуг.", when=~F["has_any"]),
        SmartScrollingText(
            text=Format("{cards_text}"),
            id="scroll_cards",
            items_per_page=8,
            when=F["has_any"],
        ),
        Row(
            PrevPage(scroll="scroll_cards", text=Const("⬅️")),
            Button(Format("📄 {page_current} / {pages_total}"), id="paginator"),
            NextPage(scroll="scroll_cards", text=Const("➡️")),
            when=F["has_any"],
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PaidServiceSG.connected,
        getter=getter_connected_services_user,
    ),
)


buy_service_dialog = Dialog(
    Window(
        Format("<b>{service_name}</b>\n"),
        Const("Выберите объявление:", when=F["has_ads"]),
        Const(
            "Нет подходящих объявлений. Данная услуга применяется только в момент публикации нового или повторной публикации старого объявления.",
            when=~F["has_ads"],
        ),
        ScrollingGroup(
            Select(
                Format("{item[title]}"),
                id="ad_select",
                items="ads",
                item_id_getter=lambda it: it["id"],
                on_click=on_ad_selected_service,
            ),
            id="ads_scroll",
            width=1,
            height=8,
            hide_on_single_page=True,
            when="has_ads",
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=BuyServiceSG.select_ad,
        getter=getter_user_ads_for_service,
    ),
    Window(
        Format(
            "📌 <b>Подтверждение покупки</b>\n\n"
            "Услуга: <b>{service_name}</b>\n"
            "Объявление: <b>{ad_title}</b>\n"
            "Цена: <b>{price_text}</b>\n"
        ),
        Button(
            Const("✅ Подключить"),
            id="confirm_buy",
            on_click=on_confirm_buy_service,
            style=Style(style=ButtonStyle.SUCCESS),
        ),
        Back(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=BuyServiceSG.confirm,
        getter=getter_buy_service_confirm,
    ),
)


pre_publication_dialog = Dialog(
    Window(
        Format(
            "<b><u>{service_name}</u></b>\n\n"
            "{description}\n\n"
            "<b>Срок:</b> {duration_text}\n\n"
            "<b>Цена:</b> <i>{price_text}</i>\n"
        ),
        Format(
            "⚠️ <b>У вас уже активна подписка</b> до <b>{current_expires_display}</b>.\n"
            "При повторной покупке срок продлится до <b>{new_expires_display}</b>.",
            when=F["already_active"],
        ),
        Button(
            Const("✅ Подключить подписку"),
            id="confirm_buy_pre_publication",
            on_click=on_confirm_buy_pre_publication,
            style=Style(style=ButtonStyle.SUCCESS),
        ),
        Cancel(
            Const("⬅️ Назад"),
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=PrePublicationSG.confirm,
        getter=getter_pre_publication_confirm,
    ),
)
