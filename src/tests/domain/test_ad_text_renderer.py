from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.enums.ad import AdType
from src.domain.services.ad.ad_text_renderer import AdTextRenderer
from src.domain.value_objects.ad_content import AdContent
from src.domain.value_objects.region_metadata import RegionMetadata
from src.domain.value_objects.store_content import StoreContent, StoreItem
from src.domain.value_objects.timezone_name import TimezoneName


def test_render_standard_sale():
    region = Region(
        id=1,
        title="Ставрополь",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="Snomerami",
        metadata=RegionMetadata(
            {
                "tg_group_url": "https://t.me/...",
                "vk_group_url": "https://vk.com/...",
                "max_channel_url": "https://max.ru/...",
            }
        )
    )
    # если links у тебя уже есть, можно подставить — иначе тест без links
    # region.links = RegionLinks(tg_group_url="https://t.me/...", vk_group_url="https://vk.com/...")

    ad = Ad(
        id=10,
        user_id=100,
        region_id=1,
        ad_type=AdType.SALE,
    )
    ad.fill_content(
        AdContent(
            plate_number="О126ЕВ136",
            city="Ставрополь",
            price_text="Договорная",
            contacts="@Ludvig_Petrosyan, +79289113058",
        )
    )

    text = AdTextRenderer(bot_url="https://t.me/Snomerami_bot").render(ad=ad, region=region)

    assert "📌 ПРОДАМ НОМЕРА" in text
    assert "🚘 Номер: О126ЕВ136" in text
    assert "🌎 Город: Ставрополь" in text
    assert "💰 Цена: Договорная" in text
    assert "📲 Связь: @Ludvig_Petrosyan, +79289113058" in text
    assert "⚠️ РАЗМЕСТИТЬ ОБЪЯВЛЕНИЕ" in text


def test_render_store():
    region = Region(
        id=2,
        title="Ставрополь",
        timezone=TimezoneName("Europe/Moscow"),
        channel_id=-100123,
        channel_username="Snomerami",
        metadata=RegionMetadata(
            {
                "tg_group_url": "https://t.me/...",
                "vk_group_url": "https://vk.com/...",
                "max_channel_url": "https://max.ru/...",
            }
        )
    )

    ad = Ad(
        id=11,
        user_id=101,
        region_id=2,
        ad_type=AdType.STORE,
    )
    ad.fill_store_content(
        StoreContent(
            shop_name="Автономера vip26",
            city="Георгиевск",
            contacts="@Bigman026, 89887473674",
            items=(
                StoreItem(plate="Р 100 АТ 126", price_text="130 000 руб."),
                StoreItem(plate="Р 099 УО 126", price_text="80 000 руб."),
            ),
        )
    )

    text = AdTextRenderer(bot_url="https://t.me/Snomerami_bot").render(ad=ad, region=region)

    assert "🏦 Магазин: Автономера vip26" in text
    assert "Список доступных номеров:" in text
    assert "✖️ Р 100 АТ 126 ➖ 130 000 руб." in text
    assert "✖️ Р 099 УО 126 ➖ 80 000 руб." in text
