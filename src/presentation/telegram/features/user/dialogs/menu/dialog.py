from aiogram import F
from aiogram_dialog import Dialog, Window, StartMode
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import (
    Select,
    Row,
    Start,
    Group,
    Column,
    Url,
    Next,
    Back,
)

from src.domain.enums.ad import AdType
from src.presentation.telegram.features.user.dialogs.create_ad.states import CreateAdSG

from .states import UserMenuSG
from .getters import getter_user_menu


user_menu_dialog = Dialog(
    Window(
        Const("Выберите действие:"),
        Start(
            Const("💎 Каталог объявлений до публикации"),
            id="early_ads_catalog",
            state=UserMenuSG.menu,
            when="is_early_access",
        ),
        Row(
            Start(
                Const("📤 ПРОДАТЬ"),
                id="sell",
                state=CreateAdSG.plate,
                data={"ad_type": AdType.SALE},
            ),
            Start(
                Const("⚠️ Срочный выкуп"),
                id="quick_buy",
                state=UserMenuSG.urgent,
                data={"ad_type": AdType.URGENT_BUYOUT},
            ),
        ),
        Row(
            Start(
                Const("📥 КУПИТЬ"),
                id="buy",
                state=UserMenuSG.buy,
                data={"ad_type": AdType.BUY},
            ),
            Start(
                Const("🏦 Мой магазин"),
                id="my_store",
                state=UserMenuSG.my_store,
                when="is_store",
            ),
            Start(
                Const("🏦 Создать магазин"),
                id="create_store",
                state=UserMenuSG.create_store,
                when=~F["is_store"],
            ),
        ),
        Column(
            Start(
                Const("📝 Редактировать мои объявления"),
                id="edit_ad",
                state=UserMenuSG.edit_ad,
            ),
            Start(
                Const("🚀 Платные Топ услуги (NEW)"),
                id="paid_services",
                state=UserMenuSG.paid_services,
            ),
        ),
        Row(
            Start(
                Const("💻 Мой профиль"),
                id="profile",
                state=UserMenuSG.profile,
            ),
            Start(
                Const("💰 Пополнить баланс"),
                id="top_up",
                state=UserMenuSG.top_up,
            ),
        ),
        Column(
            Next(Format("♻️ Смена региона ({region_name})")),
            Url(
                Const("👨‍💻 Поддержка 24/7"),
                url=Const("https://t.me/mlnora"),
            ),
        ),
        state=UserMenuSG.menu,
        getter=getter_user_menu,
    ),
    # Window(
    #     Const("На текущий момент доступных регионов нет!", when=~F["regions"]),
    #     Const("Выберите регион:", when="regions"),
    #     Group(
    #         Select(
    #             Format("{item.name} - @{item.channel_username}"),
    #             id="s_regions",
    #             item_id_getter=lambda item: item.id,
    #             items="regions",
    #             on_click=on_region_selected,
    #         ),
    #         width=1,
    #         when="regions",
    #     ),
    #     Back(Const("⬅️ Назад"), when="is_region"),
    #     state=UserStartSG.region,
    #     getter=getter_regions,
    # ),
)