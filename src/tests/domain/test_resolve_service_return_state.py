"""
Regression test for AUD-15: on_service_paid_selected used to read ad_type
from dialog_manager.dialog_data, which the post-payment teleport
(AiogramDialogTeleporter.start) restarts with an empty dialog_data. A second
paid-service purchase in the same flow (e.g. insufficient balance twice in a
row) would then see ad_type=None and misroute a STORE ad's owner into the
regular ad-creation dialog instead of the store dialog. The fix reads
ad_type from the freshly-loaded Ad entity instead of dialog_data.
resolve_service_return_state() is the extracted decision logic.
"""

from src.domain.enums.ad import AdType
from src.presentation.telegram.features.user.shared.ad_handlers import (
    resolve_service_return_state,
)


def test_store_ad_returns_to_store_dialog():
    assert (
        resolve_service_return_state(AdType.STORE)
        == "StoreViewPublishSG:publication_service"
    )


def test_sale_ad_returns_to_create_ad_dialog():
    assert resolve_service_return_state(AdType.SALE) == "CreateAdSG:publication_service"


def test_buy_ad_returns_to_create_ad_dialog():
    assert resolve_service_return_state(AdType.BUY) == "CreateAdSG:publication_service"


def test_urgent_buyout_ad_returns_to_create_ad_dialog():
    assert (
        resolve_service_return_state(AdType.URGENT_BUYOUT)
        == "CreateAdSG:publication_service"
    )
