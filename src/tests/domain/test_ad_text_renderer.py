from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.enums.ad import AdStatus, AdType
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.contacts import Contacts
from src.domain.value_objects.price import Price
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.region_settings import RegionSettings
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.domain.value_objects.timezone_name import TimezoneName


def make_region(region_id: int = 1) -> Region:
    return Region(
        id=region_id,
        title="Ставрополь",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="Snomerami",
        metadata=RegionMetadata(
            tg_group_url="https://t.me/example",
            vk_group_url="https://vk.com/example",
            max_channel_url="https://max.ru/example",
        ),
        settings=RegionSettings(),
    )


def test_render_standard_sale():
    region = make_region()

    ad = Ad(
        id=10,
        user_id=100,
        region_id=1,
        ad_type=AdType.SALE,
        status=AdStatus.READY,
    )
    ad.fill_content(
        AdContent(
            plate_number="О126ЕВ136",
            city="Ставрополь",
            price=Price(0),
            contacts=Contacts(username="Ludvig_Petrosyan", phone="+79289113058"),
        )
    )

    text = AdTextRenderer(
        bot_url="https://t.me/Snomerami_bot",
        buyout_url="https://t.me/Snomerami_buyout",
    ).render(ad=ad, region=region)

    assert "📌 ПРОДАМ НОМЕРА" in text
    assert "🚘 <b>Номер:</b> О126ЕВ136" in text
    assert "🌎 <b>Город:</b> Ставрополь" in text
    assert "💰 <b>Цена:</b> Договорная" in text
    assert "@Ludvig_Petrosyan" in text
    assert "+79289113058" in text
    assert "РАЗМЕСТИТЬ ОБЪЯВЛЕНИЕ" in text
    assert "Наш Чат" in text  # metadata.tg_group_url подставился в ссылки


def test_render_store():
    region = make_region(region_id=2)

    ad = Ad(
        id=11,
        user_id=101,
        region_id=2,
        ad_type=AdType.STORE,
        status=AdStatus.READY,
    )
    ad.fill_store_content(
        StoreContent(
            shop_name="Автономера vip26",
            city="Георгиевск",
            contacts=Contacts(username="Ludvig_Petrosyan", phone="+79289113058"),
            items=(
                StoreItem(plate="Р 100 АТ 126", price=Price(130_000)),
                StoreItem(plate="Р 099 УО 126", price=Price(80_000)),
            ),
        )
    )

    text = AdTextRenderer(
        bot_url="https://t.me/Snomerami_bot",
        buyout_url="https://t.me/Snomerami_buyout",
    ).render(ad=ad, region=region)

    assert "🏦 <b>Магазин:</b> Автономера vip26" in text
    assert "Список доступных номеров:" in text
    assert "✖️ Р 100 АТ 126 ➖ 130 000 руб." in text
    assert "✖️ Р 099 УО 126 ➖ 80 000 руб." in text
