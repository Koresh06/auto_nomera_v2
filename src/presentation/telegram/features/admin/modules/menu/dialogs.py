from aiogram import F
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Const

from src.presentation.telegram.features.admin.modules.admin_management.states import AdminManagementSG
from src.presentation.telegram.features.admin.modules.balance.states import (
    UserBalanceAdminSG,
)
from src.presentation.telegram.features.admin.modules.blocking.states import UserBlockSG
from src.presentation.telegram.features.admin.modules.mailing.states import MailingSG
from src.presentation.telegram.features.admin.modules.paid_services.states import (
    PaidServiceAdminSG,
)
from src.presentation.telegram.features.admin.modules.region.main.states import (
    MainRegionSG,
)
from src.presentation.telegram.features.admin.modules.stats.globals.states import GlobalStatsSG
from src.presentation.telegram.features.admin.modules.stats.publications.states import PublishStatsSG
from src.presentation.telegram.features.admin.modules.stats.replenishment.states import StatsReplenishmentSG

from .getters import getter_admin_menu
from .states import AdminMenuSG

admin_menu_dialog = Dialog(
    Window(
        Const("🚘 <b>Админ-панель</b>\n\nВыберите раздел:"),
        Start(
            Const("🗺 Регионы"),
            id="region_menu",
            state=MainRegionSG.start,
            when=F["is_super_admin"],
        ),
        Start(
            Const("💎 Платные услуги"),
            id="paid_services",
            state=PaidServiceAdminSG.list,
            when=F["is_super_admin"],
        ),
        Start(
            Const("💳 Баланс пользователей"),
            id="user_balance",
            state=UserBalanceAdminSG.start,
            when=F["is_super_admin"],
        ),
        Start(
            Const("🚫 Блокировка пользователя"),
            id="user_block",
            state=UserBlockSG.start,
            when=F["is_super_admin"],
        ),
        Start(
            Const("🛡 Управление админами"),
            id="admin_management",
            state=AdminManagementSG.menu,
            when=F["is_super_admin"],
        ),
        Start(
            Const("📢 Рассылки"),
            id="mailing",
            state=MailingSG.choose_type,
        ),
        # Start(
        #     Const("⚙️ Настройки"),
        #     id="admin_settings",
        #     state=AdminSettingsSG.menu,
        # ),
        Start(
            Const("💰 Статистика пополнений"),
            id="replenishment_stats",
            state=StatsReplenishmentSG.general,
        ),
        Start(
            Const("🔢 Статистика публикаций"),
            id="ads_stats",
            state=PublishStatsSG.start,
        ),
        Start(
            Const("📈 Общая статистика"),
            id="global_stats",
            state=GlobalStatsSG.start,
        ),
        state=AdminMenuSG.menu,
        getter=getter_admin_menu,
    )
)
