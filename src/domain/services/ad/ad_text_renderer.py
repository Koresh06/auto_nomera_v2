from dataclasses import dataclass

from src.domain.entities.ad import Ad
from src.domain.entities.region import Region
from src.domain.enums.ad import AdType
from src.domain.services.ad.plate_hashtags import generate_hashtags


@dataclass(frozen=True, slots=True)
class AdTextRenderer:
    bot_url: str
    buyout_url: str

    def render(self, *, ad: Ad, region: Region) -> str:
        if ad.ad_type == AdType.STORE:
            body = self._render_store(ad)
        else:
            body = self._render_standard(ad)

        hashtags = self._render_hashtags(ad)
        links = self._render_links(region)

        parts = [body]
        parts.append(links)
        if hashtags:
            parts.append(hashtags)

        return "\n\n".join(parts)

    def _render_standard(self, ad: Ad) -> str:
        c = ad.content
        assert c is not None

        header = ad.ad_type.display

        lines = [
            f"<b>{header}</b>",
            "",
            f"🚘 <b>Номер:</b> {c.plate_number}",
            f"🌎 <b>Город:</b> {c.city}",
            f"💰 <b>Цена:</b> {c.price.display}",
            "",
            f"📲 <b>Связь:</b> {c.contacts.display}",
        ]

        if c.caption:
            lines.extend(["", c.caption])

        return "\n".join(lines)

    def _render_store(self, ad: Ad) -> str:
        s = ad.store_content
        assert s is not None

        lines = [
            "<b>📌 МАГАЗИН НОМЕРОВ</b>",
            "",
            f"🏦 <b>Магазин:</b> {s.shop_name}",
            f"🌎 <b>Город:</b> {s.city}",
            f"📲 <b>Связь:</b> {s.contacts.display}",
            "",
            "<b>Список доступных номеров:</b>",
            "",
        ]

        for item in s.items:
            lines.append(f"✖️ {item.plate} ➖ {item.price.display}")

        return "\n".join(lines)

    def _render_hashtags(self, ad: Ad) -> str:
        plates: list[str] = []

        if ad.ad_type == AdType.STORE and ad.store_content:
            plates = [item.plate for item in ad.store_content.items]
        elif ad.content and ad.content.plate_number:
            plates = [ad.content.plate_number]

        all_tags: list[str] = []
        for plate in plates:
            for tag in generate_hashtags(plate):
                if tag not in all_tags:
                    all_tags.append(tag)

        return " ".join(all_tags) if all_tags else ""

    def _render_links(self, region: Region) -> str:
        lines = [
            f"<b><a href='{self.bot_url}'>⚠️ РАЗМЕСТИТЬ ОБЪЯВЛЕНИЕ</a></b>",
            "—————————————————",
            f"<b><a href='{self.buyout_url}'>💸 ВЫКУП ВАШИХ НОМЕРОВ</a></b>",
            "—————————————————",
        ]

        if region.metadata is not None:
            m = region.metadata
            lines.append(
                f"✅ <b><a href='https://t.me/{region.channel_username}'>Наш канал</a></b>"
            )
            if m.tg_group_url:
                lines.append(f"✅ <b><a href='{m.tg_group_url}'>Наш Чат</a></b>")
            if m.vk_group_url:
                lines.append(f"✅ <b><a href='{m.vk_group_url}'>Наша группа VK</a></b>")
            if m.max_channel_url:
                lines.append(f"✅ <b><a href='{m.max_channel_url}'>Мы в MAX</a></b>")

        return "\n".join(lines)
