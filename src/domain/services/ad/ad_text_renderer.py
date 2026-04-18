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
            return self._render_store(ad) + "\n" + links_block

        return self._render_standard(ad) + "\n" + links_block

    def _render_standard(self, ad: Ad) -> str:
        c = ad.content
        assert c is not None

        header = "📌 ПРОДАМ НОМЕРА"
        if ad.ad_type == AdType.BUY:
            header = "📌 КУПЛЮ НОМЕРА"
        elif ad.ad_type == AdType.URGENT_BUYOUT:
            header = "📌 СРОЧНЫЙ ВЫКУП"

        lines = [
            header,
            "",
            f"🚘 Номер: {c.plate_number}",
            f"🌎 Город: {c.city}",
            f"💰 Цена: {c.price.display}",
            "",
            f"📲 Связь: {c.contacts.display}",
        ]

        if c.caption:
            lines.extend(["", c.caption])

        tags = generate_hashtags(c.plate_number)
        if tags:
            lines.extend(["", " ".join(tags)])

        return "\n".join(lines)

    def _render_store(self, ad: Ad) -> str:
        s = ad.store_content
        assert s is not None

        lines = [
            "📌 ПРОДАМ НОМЕРА",
            "",
            f"🏦 Магазин: {s.shop_name}",
            f"🌎 Город: {s.city}",
            f"📲 Связь: {s.contacts.display}",
            "",
            "Список доступных номеров:",
            "",
        ]

        for item in s.items:
            lines.append(f"✖️ {item.plate} ➖ {item.price.display}")

        return "\n".join(lines)

    def _render_links(self, region: Region) -> str:
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
                links.append(f"✅ Наш канал MAX ({rl.max_channel_url})")

        return "\n".join(links)
