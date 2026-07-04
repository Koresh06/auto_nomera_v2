from aiogram import Router
from aiogram_dialog import Dialog

from src.presentation.telegram.features.error_handlers import router as error_router
from src.presentation.telegram.features.user.routers import router as user_router
from src.presentation.telegram.features.admin.routers import router as admin_router
from src.presentation.telegram.features.admin.modules.urgent_buyout.router import (
    router as admin_urgent_buyout_router,
)
from src.presentation.telegram.features.user.modules.catalog_deferred_publication.routers import (
    router as user_urgent_buyout_router,
)
from src.presentation.telegram.features.user.modules.payment.routers import (
    router as payment_router,
)

from src.presentation.telegram.features.user.modules.menu.dialog import user_menu_dialog
from src.presentation.telegram.features.user.modules.ad.create_ad.dialog import (
    create_ad_dialog,
)
from src.presentation.telegram.features.user.modules.ad.edit.dialog import (
    edit_ad_dialog,
)
from src.presentation.telegram.features.user.modules.catalog_deferred_publication.dialogs import (
    catalog_deferred_publication_dialog,
)
from src.presentation.telegram.features.user.modules.profile.dialogs import (
    profile_dialog,
)
from src.presentation.telegram.features.user.modules.paid_services.dialogs import (
    paid_service_dialog,
    buy_service_dialog,
    pre_publication_dialog,
)
from src.presentation.telegram.features.user.modules.balance.dialogs import topup_dialog
from src.presentation.telegram.features.user.modules.payment.dialogs import (
    payment_dialog,
)
from src.presentation.telegram.features.user.modules.store.main.dialogs import (
    store_main_dialog,
)
from src.presentation.telegram.features.user.modules.store.create.dialogs import (
    create_store_dialog,
)
from src.presentation.telegram.features.user.modules.store.add_item.dialogs import (
    store_add_items_dialog,
)
from src.presentation.telegram.features.user.modules.store.view_publish.dialogs import (
    store_view_publish_dialog,
)
from src.presentation.telegram.features.user.modules.store.edit_store.dialogs import (
    store_edit_dialog,
)
from src.presentation.telegram.features.user.modules.store.edit_items.dialogs import (
    store_edit_items_dialog,
)
from src.presentation.telegram.features.admin.modules.menu.dialogs import (
    admin_menu_dialog,
)
from src.presentation.telegram.features.admin.modules.region.main.dialog import (
    main_region_dialog,
)
from src.presentation.telegram.features.admin.modules.region.create.dialog import (
    create_region_dialog,
)
from src.presentation.telegram.features.admin.modules.region.edit.settings.dialogs import (
    edit_region_settings_dialog,
)
from src.presentation.telegram.features.admin.modules.region.edit.metadata.dialogs import (
    edit_region_metadata_dialog,
)
from src.presentation.telegram.features.admin.modules.paid_services.dialogs import (
    paid_service_admin_dialog,
)
from src.presentation.telegram.features.admin.modules.balance.dialogs import (
    admin_balance_dialog,
)
from src.presentation.telegram.features.admin.modules.blocking.dialogs import (
    blocked_user_dialog,
)
from src.presentation.telegram.features.admin.modules.admin_management.dialogs import (
    admin_management_dialog,
)
from src.presentation.telegram.features.admin.modules.mailing.dialogs import (
    mailing_dialog,
)
from src.presentation.telegram.features.admin.modules.stats.replenishment.dialogs import (
    stats_replenishment_dialog,
)
from src.presentation.telegram.features.admin.modules.stats.publications.dialogs import (
    publish_stats_dialog,
)
from src.presentation.telegram.features.admin.modules.stats.globals.dialogs import (
    global_stats_dialog,
)


def get_all_routers() -> list[Router]:
    return [
        error_router,
        user_router,
        admin_router,
        admin_urgent_buyout_router,
        user_urgent_buyout_router,
        payment_router,
    ]


def get_all_dialogs() -> list[Dialog]:
    return [
        user_menu_dialog,
        create_ad_dialog,
        edit_ad_dialog,
        catalog_deferred_publication_dialog,
        profile_dialog,
        paid_service_dialog,
        buy_service_dialog,
        pre_publication_dialog,
        topup_dialog,
        payment_dialog,
        store_main_dialog,
        create_store_dialog,
        store_add_items_dialog,
        store_view_publish_dialog,
        store_edit_dialog,
        store_edit_items_dialog,
        admin_menu_dialog,
        main_region_dialog,
        create_region_dialog,
        edit_region_settings_dialog,
        edit_region_metadata_dialog,
        paid_service_admin_dialog,
        admin_balance_dialog,
        blocked_user_dialog,
        admin_management_dialog,
        mailing_dialog,
        stats_replenishment_dialog,
        publish_stats_dialog,
        global_stats_dialog,
    ]
