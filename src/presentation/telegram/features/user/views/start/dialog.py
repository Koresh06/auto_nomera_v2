from aiogram import F
from aiogram.enums.button_style import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.style import Style
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
from src.presentation.telegram.features.user.views.ad.create_ad.states import CreateAdSG
from src.presentation.telegram.features.user.views.start.getters import (
    getter_start_menu,
    list_regions_getter,
)
from src.presentation.telegram.features.user.views.start.handlers import (
    on_register_user,
)
from src.presentation.telegram.features.user.views.start.states import StartSG


start_dialog = Dialog(
    Window(
        Const("Выберите действие:"),
        # Start(
        #     Const("💎 Каталог объявлений до публикации"),
        #     id="early_ads_catalog",
        #     state=CatalogUrgentRedemptionSG.start,
        #     when="has_early_access",
        # ),
        Row(
            Start(
                Const("📤 ПРОДАТЬ"),
                id="sale",
                state=CreateAdSG.plate,
                data={"ad_type": AdType.SALE},
            ),
            Start(
                Const("⚠️ Срочный выкуп"),
                id="urgent_buyout",
                state=CreateAdSG.plate,
                data={"ad_type": AdType.URGENT_BUYOUT},
            ),
        ),
        Row(
            Start(
                Const("📥 КУПИТЬ"),
                id="buy",
                state=CreateAdSG.plate,
                data={"ad_type": AdType.BUY},
            ),
            # Start(
            #     Const("🏦 Мой магазин"),
            #     id="my_store",
            #     state=ViewStoreSG.start,
            #     when="has_store",
            # ),
            # Start(
            #     Const("🏦 Создать магазин"),
            #     id="create_store",
            #     state=StoreSG.confirm_create,
            #     when=~F["has_store"],
            # ),
        ),
        # Column(
        #     Start(
        #         Const("📝 Редактировать мои объявления"),
        #         id="edit_ad",
        #         state=UpdateAdSG.start,
        #     ),
        #     Start(
        #         Const("🚀 Платные Топ услуги (NEW)"),
        #         id="paid_services",
        #         state=PaidServiceSG.start,
        #     ),
        # ),
        # Row(
        #     Start(
        #         Const("💻 Мой профиль"),
        #         id="profile",
        #         state=UserProfileSG.start,
        #     ),
        #     Start(
        #         Const("💰 Пополнить баланс"),
        #         id="top_up",
        #         state=TopupSG.enter_amount,
        #     ),
        # ),
        Column(
            Next(Format("♻️ Смена региона ({user.region_id})")),
            Url(
                Const("👨‍💻 Поддержка 24/7"),
                url=Const("https://t.me/mlnora"),
            ),
        ),
        state=StartSG.menu,
        getter=getter_start_menu,
    ),
    Window(
        Const("На текущий момент доступных регионов нет!", when=~F["regions"]),
        Const("Выберите регион:", when="regions"),
        Group(
            Select(
                Format("{item.title} - @{item.channel_username}"),
                id="region_id",
                item_id_getter=lambda item: item.id,
                items="regions",
                on_click=on_register_user,
            ),
            width=1,
            when="regions",
        ),
        Back(
            Const("⬅️ Назад"),
            when="is_region",
            style=Style(style=ButtonStyle.PRIMARY),
        ),
        state=StartSG.chooise_region,
        getter=list_regions_getter,
    ),
)
