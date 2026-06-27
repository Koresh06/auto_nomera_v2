from aiogram import F
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

from src.domain.enums.publication_service import PublicationServiceType
from src.presentation.telegram.features.user.modules.menu.states import UserMenuSG

from .states import BuyServiceSG, PaidServiceSG, PrePublicationSG
from .smart_scroll_text import SmartScrollingText
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
                "<b>{item[name]}</b>\n"
                "{item[description]}\n"
                "Срок: {item[duration_text]}\n"
                "Цена: <i>{item[price_text]}</i>\n"
            ),
            items="services",
            id="services_list",
        ),
        Start(
            Const("💎 Объявления до публикации"),
            id="buy_pre_publication",
            state=PrePublicationSG.confirm,
        ),
        Group(
            Start(
                Const("🥇 Вне очереди"),
                id="buy_priority",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.PRIORITY_PUBLISH.value},
            ),
            Start(
                Const("🔂 Автопубликация"),
                id="buy_auto",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.AUTOPUBLISH.value},
            ),
            Start(
                Const("📌 Закрепление"),
                id="buy_pin",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.PIN.value},
            ),
            Start(
                Const("🟥 Выделение"),
                id="buy_highlight",
                state=BuyServiceSG.select_ad,
                data={"service_type": PublicationServiceType.HIGHLIGHT.value},
            ),
            width=2,
        ),
        Next(Const("📂 Подключённые услуги")),
        # Cancel(Const("⬅️ Назад")),
        Start(
            Const("⬅️ Назад"),
            id="back_to_menu",
            state=UserMenuSG.menu,
            mode=StartMode.RESET_STACK,
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
            items_per_page=3,
            when=F["has_any"],
        ),
        Row(
            PrevPage(scroll="scroll_cards", text=Const("⬅️")),
            Button(Format("📄 {page_current} / {pages_total}"), id="paginator"),
            NextPage(scroll="scroll_cards", text=Const("➡️")),
            when=F["has_any"],
        ),
        Back(Const("⬅️ Назад")),
        state=PaidServiceSG.connected,
        getter=getter_connected_services_user,
    ),
)


buy_service_dialog = Dialog(
    Window(
        Format("<b>{service_name}</b>\n\nВыберите объявление:"),
        Const(
            "У вас пока нет объявлений с неподключенной услугой.", when=~F["has_ads"]
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
        Cancel(Const("⬅️ Назад")),
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
        ),
        Back(Const("⬅️ Назад")),
        state=BuyServiceSG.confirm,
        getter=getter_buy_service_confirm,
    ),
)


pre_publication_dialog = Dialog(
    Window(
        Format(
            "<b>{service_name}</b>\n\n"
            "🕒 <b>Срок действия:</b> {duration_text} дн.\n"
            "💰 <b>Стоимость:</b> {price_text}\n\n"
            "⚠️ После подключения подписки Вы получаете полный доступ к объявлениям из раздела "
            '"Срочный выкуп", а также к объявлениям подписчиков до публикации в канале выбранного ранее Вами региона.\n'
            "⚠️ После подключения подписки, в главном меню появится новая кнопка "
            '"<b>💎 Каталог объявлений до публикации</b>".'
        ),
        Format(
            "\n\n⚠️ <b>У вас уже активна подписка</b> до <b>{current_expires_display}</b>.\n"
            "При повторной покупке срок продлится до <b>{new_expires_display}</b>.",
            when=F["already_active"],
        ),
        Button(
            Const("✅ Подключить подписку"),
            id="confirm_buy_pre_publication",
            on_click=on_confirm_buy_pre_publication,
        ),
        Cancel(Const("⬅️ Назад")),
        state=PrePublicationSG.confirm,
        getter=getter_pre_publication_confirm,
    ),
)
