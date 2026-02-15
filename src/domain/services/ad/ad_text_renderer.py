from dataclasses import dataclass

from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_hashtags import generate_hashtags


@dataclass(frozen=True, slots=True)
class AdTextRenderer:
    bot_url: str  # "https://t.me/Snomerami_bot"

    def render(self, *, ad: Ad, region: Region) -> str:
        # нижний блок ссылок — из Region.links (мы ранее обсуждали)
        links_block = self._render_links(region)

        if ad.ad_type == AdType.STORE:
            return self._render_store(ad, region) + "\n" + links_block

        return self._render_standard(ad, region) + "\n" + links_block

    def _render_standard(self, ad: Ad, region: Region) -> str:
        c = ad.content
        assert c is not None

        header = "📌 ПРОДАМ НОМЕРА"  # позже можно маппить по ad_type
        if ad.ad_type == AdType.BUY:
            header = "📌 КУПЛЮ НОМЕРА"
        elif ad.ad_type == AdType.URGENT_BUYOUT:
            header = "📌 СРОЧНЫЙ ВЫКУП"

        lines = [
            header,
            "",
            f"🚘 Номер: {c.plate_number}",
            f"🌎 Город: {c.city}",
            f"💰 Цена: {c.price_text}",
            "",
            f"📲 Связь: {c.contacts}",
        ]

        if c.caption:
            lines.extend(["", c.caption])

        tags = generate_hashtags(c.plate_number)
        if tags:
            lines.extend(["", " ".join(tags)])

        return "\n".join(lines)

    def _render_store(self, ad: Ad, region: Region) -> str:
        s = ad.store_content
        assert s is not None

        lines = [
            "📌 ПРОДАМ НОМЕРА",
            "",
            f"🏦 Магазин: {s.shop_name}",
            f"🌎 Город: {s.city}",
            f"📲 Связь: {s.contacts}",
            "",
            "Список доступных номеров:",
            "",
        ]

        for item in s.items:
            lines.append(f"✖️ {item.plate} ➖ {item.price_text}")

        return "\n".join(lines)

    def _render_links(self, region: Region) -> str:
        # region.metadata может быть None
        bot_line = f"⚠️ РАЗМЕСТИТЬ ОБЪЯВЛЕНИЕ ({self.bot_url})"
        sep = "—————————————————"

        links = [bot_line, sep]

        if getattr(region, "metadata", None) is not None:
            rl = region.metadata
            if rl.tg_group_url:
                links.append(f"✅ Наш Чат ({rl.tg_group_url})")
            if rl.vk_group_url:
                links.append(f"✅ Наша группа VK ({rl.vk_group_url})")
            if rl.max_channel_url:
                links.append(f"✅ Наш канал MAX ({rl})")

        return "\n".join(links)
