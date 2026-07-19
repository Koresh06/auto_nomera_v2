"""
ETL: перенос данных из старой БД AutoNomeraBot в новую схему auto_nomera_v2.

Запуск:
    # сухой прогон — ничего не пишет, только отчёт
    docker compose run --rm bot python scripts/migrate_legacy.py --dry-run

    # реальный перенос
    docker compose run --rm bot python scripts/migrate_legacy.py

Источник задаётся через LEGACY_DSN:
    LEGACY_DSN=postgresql://my_user:pass@host:5432/auto_db

Скрипт идемпотентен только в смысле «прогнал → снёс новую БД → прогнал заново».
Повторный запуск поверх заполненной БД создаст дубли.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.domain.enums.ad import AdStatus, AdType
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.publication_service import (
    PublicationServiceStatus,
    PublicationServiceType,
)
from src.domain.enums.region import RegionStatus
from src.domain.enums.role import UserRole
from src.infrastructure.database.models import (
    AdModel,
    PaymentModel,
    PublicationModel,
    PublicationServiceModel,
    RegionModel,
    SlotConvertedModel,
    UserModel,
)


# --------------------------------------------------------------------------
# Справочники
# --------------------------------------------------------------------------

# Таймзона по id региона в СТАРОЙ базе
REGION_TZ: dict[int, str] = {
    1: "Europe/Moscow",  # 26 Ставропольский
    2: "Europe/Moscow",  # 23/93 Краснодарский
    3: "Europe/Moscow",  # 61 Ростовская
    4: "Europe/Moscow",  # 05 Дагестан
    5: "Europe/Saratov",  # 64 Саратовская
    6: "Asia/Yekaterinburg",  # 72 Тюменская
    7: "Europe/Moscow",  # 77 Москва и МО
    8: "Europe/Moscow",  # 16 Татарстан
    9: "Europe/Moscow",  # 78 СПб и ЛО
    10: "Asia/Yekaterinburg",  # 66/96 Свердловская
    11: "Asia/Novosibirsk",  # 54 Новосибирская
    12: "Europe/Moscow",  # 180 ДНР
    13: "Europe/Moscow",  # 21 Чувашия
    14: "Asia/Yekaterinburg",  # 59 Пермский
    15: "Europe/Moscow",  # 36 Воронежская
    16: "Europe/Moscow",  # 52 Нижегородская
    17: "Asia/Yekaterinburg",  # 74 Челябинская
    18: "Asia/Omsk",  # 55 Омская
    19: "Europe/Samara",  # 63 Самарская
    20: "Asia/Yekaterinburg",  # 02 Башкортостан
    21: "Europe/Samara",  # 18 Удмуртия
    22: "Asia/Krasnoyarsk",  # 24 Красноярский
    23: "Europe/Moscow",  # 33 Владимирская
    24: "Europe/Volgograd",  # 34 Волгоградская
    25: "Europe/Kaliningrad",  # 39 Калининградская
    26: "Europe/Moscow",  # 48 Липецкая
    27: "Europe/Moscow",  # 68 Тамбовская
    28: "Europe/Simferopol",  # 82 Крым
    29: "Europe/Astrakhan",  # 30 Астраханская
    30: "Europe/Moscow",  # 181 ЛНР
    31: "Asia/Krasnoyarsk",  # 17 Тыва
    32: "Asia/Krasnoyarsk",  # 19 Хакасия
    33: "Europe/Moscow",  # 58 Пензенская
    34: "Europe/Moscow",  # 62 Рязанская
    35: "Asia/Yekaterinburg",  # 86 ХМАО
    36: "Europe/Moscow",  # 07 КБР
    37: "Europe/Moscow",  # 32 Брянская
    38: "Europe/Moscow",  # 13 Мордовия
    39: "Asia/Yekaterinburg",  # 45 Курганская
    40: "Asia/Tomsk",  # 70 Томская
    41: "Europe/Moscow",  # 67 Смоленская
    42: "Asia/Irkutsk",  # 38 Иркутская
    43: "Asia/Novokuznetsk",  # 42 Кемеровская
    44: "Europe/Moscow",  # 71 Тульская
    45: "Europe/Moscow",  # 31 Белгородская
    46: "Europe/Moscow",  # 01 Адыгея
    47: "Europe/Simferopol",  # 92 Севастополь
}

DEFAULT_TZ = "Europe/Moscow"

AD_TYPE_MAP: dict[str, AdType] = {
    "SELL": AdType.SALE,
    "BUY": AdType.BUY,
    "URGENT": AdType.URGENT_BUYOUT,
    "STORE": AdType.STORE,
}

SERVICE_TYPE_MAP: dict[str, PublicationServiceType] = {
    "PIN": PublicationServiceType.PIN,
    "HIGHLIGHT": PublicationServiceType.HIGHLIGHT,
    "AUTOPOST": PublicationServiceType.AUTOPUBLISH,
    "PRIORITY": PublicationServiceType.PRIORITY_PUBLISH,
    "EARLY_ACCESS": PublicationServiceType.PRE_PUBLICATION,
}

REGION_SETTINGS = {
    "slot_times": ["10:00", "14:00", "18:00"],
    "days_range": 7,
    "system_paid_slots_count": 3,
    "publication_limit_enabled": True,
    "paid_slot_price": "200",
}


# --------------------------------------------------------------------------
# Хелперы
# --------------------------------------------------------------------------

PHONE_RE = re.compile(r"^[\d\s\-+()]{6,}$")


def clean_url(value: str | None) -> str | None:
    """'-' и пустые строки старой базы → None."""
    if value is None:
        return None
    v = value.strip()
    if not v or v == "-":
        return None
    return v


def parse_contacts(raw: str | None) -> tuple[str | None, str | None]:
    """Старое contacts (одна строка) → (username, phone)."""
    if not raw or not raw.strip():
        return None, None

    username: str | None = None
    phone: str | None = None

    for part in re.split(r"[,;/|]+", raw):
        p = part.strip()
        if not p:
            continue
        if p.startswith("@"):
            username = username or p[1:].strip()[:64]
        elif PHONE_RE.match(p):
            digits = re.sub(r"\D", "", p)
            if digits:
                phone = phone or digits[:16]
        else:
            username = username or p.lstrip("@").strip()[:64]

    return (username or None), (phone or None)


def parse_slot_time(raw: str | None) -> time | None:
    """'14:00' → time(14, 0)."""
    if not raw:
        return None
    try:
        hh, mm = raw.split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return None


def to_utc(slot_day: date, slot_time: time, tz_name: str) -> datetime:
    """Локальное время региона → UTC."""
    local = datetime.combine(slot_day, slot_time, tzinfo=ZoneInfo(tz_name))
    return local.astimezone(timezone.utc)


def money(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


# --------------------------------------------------------------------------
# Отчёт
# --------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.counts: dict[str, int] = defaultdict(int)
        self.warnings: list[str] = []

    def add(self, key: str, n: int = 1) -> None:
        self.counts[key] += n

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def render(self) -> str:
        lines = ["", "=" * 58, "ОТЧЁТ О ПЕРЕНОСЕ", "=" * 58]
        for key in sorted(self.counts):
            lines.append(f"  {key:<42} {self.counts[key]:>8}")
        if self.warnings:
            lines.append("")
            lines.append(f"ПРЕДУПРЕЖДЕНИЯ ({len(self.warnings)}):")
            for w in self.warnings[:40]:
                lines.append(f"  ! {w}")
            if len(self.warnings) > 40:
                lines.append(f"  ... и ещё {len(self.warnings) - 40}")
        lines.append("=" * 58)
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Мигратор
# --------------------------------------------------------------------------


class Migrator:
    def __init__(self, src: asyncpg.Connection, dst: AsyncSession, dry_run: bool):
        self.src = src
        self.dst = dst
        self.dry = dry_run
        self.report = Report()

        # старый id → новый id
        self.region_map: dict[int, int] = {}
        self.user_map: dict[int, int] = {}
        self.ad_map: dict[int, int] = {}  # old ads.id → new ads.id
        self.store_ad_map: dict[int, int] = {}  # old user_id → new ads.id (STORE)
        self.pub_by_old_ad: dict[int, int] = {}  # old ads.id → new publications.id
        self.region_tz: dict[int, str] = {}  # new region_id → tz

        # слоты старых объявлений: old ad_id → (date, time)
        self.slots: dict[int, tuple[date, time]] = {}

    async def run(self) -> None:
        await self.migrate_regions()
        await self.load_slots()
        await self.migrate_users()
        await self.migrate_stores()
        await self.migrate_ads()
        await self.migrate_publications()
        await self.migrate_services()
        await self.migrate_payments()
        await self.migrate_future_slots()

    # ---------------------------------------------------------------- regions

    async def migrate_regions(self) -> None:
        rows = await self.src.fetch("SELECT * FROM regions ORDER BY id")

        seen_channels: dict[int, int] = {}
        for r in rows:
            if r["channel_id"] in seen_channels:
                self.report.warn(
                    f"region {r['id']} '{r['name']}' делит channel_id "
                    f"{r['channel_id']} с регионом {seen_channels[r['channel_id']]}"
                )
            else:
                seen_channels[r["channel_id"]] = r["id"]

            tz = REGION_TZ.get(r["id"], DEFAULT_TZ)
            if r["id"] not in REGION_TZ:
                self.report.warn(
                    f"region {r['id']} '{r['name']}': tz не задана, {DEFAULT_TZ}"
                )

            model = RegionModel(
                title=r["name"][:64],
                timezone=tz,
                channel_id=r["channel_id"],
                channel_username=(r["channel_username"] or "")[:64],
                status=RegionStatus.ACTIVE,
                settings=dict(REGION_SETTINGS),
                metadata_={
                    "tg_group_url": clean_url(r["tg_group"]),
                    "vk_group_url": clean_url(r["vk_group"]),
                    "max_channel_url": clean_url(r["max_channel"]),
                },
                created_at=r["created_at"],
            )
            self.dst.add(model)
            await self.dst.flush()

            self.region_map[r["id"]] = model.id
            self.region_tz[model.id] = tz
            self.report.add("regions")

    # ------------------------------------------------------------------ slots

    async def load_slots(self) -> None:
        """Слоты старых объявлений — источник расписания."""
        rows = await self.src.fetch(
            'SELECT ad_id, _date, "time" FROM slot_settings '
            "WHERE ad_id IS NOT NULL ORDER BY id"
        )
        for r in rows:
            t = parse_slot_time(r["time"])
            if t is None:
                self.report.warn(
                    f"slot ad_id={r['ad_id']}: не разобрал время {r['time']!r}"
                )
                continue
            self.slots[r["ad_id"]] = (r["_date"], t)
        self.report.add("slots_loaded", len(self.slots))

    # ------------------------------------------------------------------ users

    async def migrate_users(self) -> None:
        rows = await self.src.fetch("SELECT * FROM users ORDER BY id")

        for r in rows:
            region_id = self.region_map.get(r["region_id"]) if r["region_id"] else None
            if region_id is None:
                self.report.warn(
                    f"user {r['id']} tg_id={r['tg_id']}: регион не найден, пропуск"
                )
                self.report.add("users_skipped")
                continue

            model = UserModel(
                tg_id=r["tg_id"],
                username=(r["username"] or None) and r["username"][:64],
                full_name=(r["full_name"] or None) and r["full_name"][:128],
                phone=(r["phone"] or None)
                and re.sub(r"\D", "", r["phone"])[:16]
                or None,
                role=UserRole.ADMIN if r["is_admin"] else UserRole.USER,
                balance=money(r["balance"]),
                is_blocked=r["is_blocked"],
                is_payment_blocked=r["is_payment_blocked"],
                pre_publication_expires_at=r["subscription_until"],
                region_id=region_id,
                created_at=r["created_at"],
            )
            self.dst.add(model)
            await self.dst.flush()

            self.user_map[r["id"]] = model.id
            self.report.add("users")
            if r["is_admin"]:
                self.report.add("users_admin")
            if r["subscription_until"]:
                self.report.add("users_with_subscription")

    # ----------------------------------------------------------------- stores

    async def migrate_stores(self) -> None:
        """stores + store_ad_items → один Ad(STORE) на владельца."""
        stores = await self.src.fetch("SELECT * FROM stores ORDER BY id")
        items = await self.src.fetch("SELECT * FROM store_ad_items ORDER BY id")

        items_by_user: dict[int, list[dict]] = defaultdict(list)
        for it in items:
            items_by_user[it["user_id"]].append(
                {"plate": it["plate_number"], "price": int(it["price"] or 0)}
            )

        # у кого есть STORE-публикации
        published = await self.src.fetch(
            "SELECT DISTINCT user_id FROM ads WHERE ad_type = 'STORE'"
        )
        published_users = {r["user_id"] for r in published}

        for s in stores:
            user_id = self.user_map.get(s["user_id"])
            if user_id is None:
                self.report.warn(
                    f"store {s['id']}: владелец {s['user_id']} не перенесён"
                )
                self.report.add("stores_skipped")
                continue

            # регион берём у владельца
            region_row = await self.src.fetchrow(
                "SELECT region_id FROM users WHERE id = $1", s["user_id"]
            )
            region_id = (
                self.region_map.get(region_row["region_id"]) if region_row else None
            )
            if region_id is None:
                self.report.warn(f"store {s['id']}: регион владельца не найден")
                self.report.add("stores_skipped")
                continue

            has_pubs = s["user_id"] in published_users
            phone = re.sub(r"\D", "", s["phone"] or "")[:16] or None

            model = AdModel(
                user_id=user_id,
                region_id=region_id,
                ad_type=AdType.STORE,
                status=AdStatus.PUBLISHED if has_pubs else AdStatus.READY,
                shop_name=s["name"][:128],
                city=(s["city"] or "")[:128],
                phone=phone,
                store_items=items_by_user.get(s["user_id"], []),
                created_at=s["created_at"],
            )
            self.dst.add(model)
            await self.dst.flush()

            self.store_ad_map[s["user_id"]] = model.id
            self.report.add("stores")
            if not has_pubs:
                self.report.add("stores_without_publications")

    # -------------------------------------------------------------------- ads

    async def migrate_ads(self) -> None:
        """Обычные объявления 1:1. Последнее по (user, plate, type) активно, прочие в архив."""
        rows = await self.src.fetch(
            "SELECT * FROM ads WHERE ad_type <> 'STORE' ORDER BY id"
        )

        # определяем «последнее» в каждой группе
        latest: dict[tuple, int] = {}
        for r in rows:
            key = (r["user_id"], r["plate_number"], r["ad_type"])
            prev = latest.get(key)
            if prev is None or r["created_at"] >= prev[1]:
                latest[key] = (r["id"], r["created_at"])
        latest_ids = {v[0] for v in latest.values()}

        for r in rows:
            user_id = self.user_map.get(r["user_id"])
            region_id = self.region_map.get(r["region_id"])
            if user_id is None or region_id is None:
                self.report.warn(f"ad {r['id']}: юзер или регион не перенесён")
                self.report.add("ads_skipped")
                continue

            username, phone = parse_contacts(r["contacts"])
            is_latest = r["id"] in latest_ids

            if not is_latest:
                status = AdStatus.ARCHIVED
            elif r["published_at"] is not None:
                status = AdStatus.PUBLISHED
            elif r["id"] in self.slots:
                status = AdStatus.SCHEDULED
            else:
                status = AdStatus.READY

            model = AdModel(
                user_id=user_id,
                region_id=region_id,
                ad_type=AD_TYPE_MAP[r["ad_type"]],
                status=status,
                plate_number=(r["plate_number"] or "")[:16] or None,
                city=(r["city"] or "")[:128] or None,
                price=int(r["price"] or 0),
                username=username,
                phone=phone,
                caption=r["caption"],
                image_file_id=r["image_file_id"],
                created_at=r["created_at"],
            )
            self.dst.add(model)
            await self.dst.flush()

            self.ad_map[r["id"]] = model.id
            self.report.add("ads")
            self.report.add(f"ads_status_{status.value}")

    # ----------------------------------------------------------- publications

    async def migrate_publications(self) -> None:
        """Каждая старая строка ads → одна публикация."""
        rows = await self.src.fetch("SELECT * FROM ads ORDER BY id")
        now = datetime.now(timezone.utc)

        for r in rows:
            if r["ad_type"] == "STORE":
                new_ad_id = self.store_ad_map.get(r["user_id"])
                if new_ad_id is None:
                    self.report.warn(
                        f"ad {r['id']} STORE: у юзера {r['user_id']} нет записи в stores"
                    )
                    self.report.add("publications_skipped")
                    continue
            else:
                new_ad_id = self.ad_map.get(r["id"])
                if new_ad_id is None:
                    self.report.add("publications_skipped")
                    continue

            region_id = self.region_map.get(r["region_id"])
            if region_id is None:
                self.report.add("publications_skipped")
                continue

            tz = self.region_tz.get(region_id, DEFAULT_TZ)
            slot = self.slots.get(r["id"])
            slot_day = slot[0] if slot else None
            slot_time = slot[1] if slot else None

            publish_at = None
            if slot:
                publish_at = to_utc(slot[0], slot[1], tz)

            if r["published_at"] is not None:
                status = PublicationStatus.PUBLISHED
                publish_at = publish_at or r["published_at"]
            elif publish_at is not None and publish_at > now:
                status = PublicationStatus.SCHEDULED
            else:
                status = PublicationStatus.CANCELED

            model = PublicationModel(
                ad_id=new_ad_id,
                region_id=region_id,
                status=status,
                slot_day=slot_day,
                slot_time=slot_time,
                publish_at_utc=publish_at,
                scheduler_job_id=None,
                channel_message_id=r["message_id"],
                published_at_utc=r["published_at"],
                is_child=False,
                created_at=r["created_at"],
            )
            self.dst.add(model)
            await self.dst.flush()

            self.pub_by_old_ad[r["id"]] = model.id
            self.report.add("publications")
            self.report.add(f"publications_status_{status.value}")

    # -------------------------------------------------------------- services

    async def migrate_services(self) -> None:
        """Активные user_paid_services → publication_services."""
        rows = await self.src.fetch(
            """
            SELECT ups.*, ps.service_type, ps.price
            FROM user_paid_services ups
            JOIN paid_services ps ON ps.id = ups.service_id
            ORDER BY ups.id
            """
        )
        now = datetime.now(timezone.utc)

        for r in rows:
            # истёкшие пропускаем
            if r["end_at"] is not None and r["end_at"] <= now:
                self.report.add("services_expired_skipped")
                continue

            svc_type = SERVICE_TYPE_MAP.get(r["service_type"])
            if svc_type is None:
                self.report.warn(
                    f"user_paid_service {r['id']}: неизвестный тип {r['service_type']}"
                )
                self.report.add("services_skipped")
                continue

            # подписка на юзера уже перенесена через pre_publication_expires_at
            if svc_type == PublicationServiceType.PRE_PUBLICATION or r["ad_id"] is None:
                self.report.add("services_user_level_skipped")
                continue

            pub_id = self.pub_by_old_ad.get(r["ad_id"])
            if pub_id is None:
                self.report.warn(
                    f"user_paid_service {r['id']}: публикация ad_id={r['ad_id']} не найдена"
                )
                self.report.add("services_skipped")
                continue

            model = PublicationServiceModel(
                publication_id=pub_id,
                type=svc_type,
                status=PublicationServiceStatus.ACTIVE,
                price_paid=int(r["price"] or 0),
                params={},
                created_at=r["start_at"],
            )
            self.dst.add(model)
            self.report.add("services")
            self.report.add(f"services_type_{svc_type.value}")

        await self.dst.flush()

    # -------------------------------------------------------------- payments

    async def migrate_payments(self) -> None:
        rows = await self.src.fetch("SELECT * FROM payments ORDER BY id")

        for r in rows:
            user_id = self.user_map.get(r["user_id"])
            if user_id is None:
                self.report.warn(f"payment {r['id']}: юзер {r['user_id']} не перенесён")
                self.report.add("payments_skipped")
                continue

            try:
                method = PaymentMethod[r["method"]]  # по ИМЕНИ, не по значению
            except KeyError:
                self.report.warn(f"payment {r['id']}: неизвестный метод {r['method']}")
                self.report.add("payments_skipped")
                continue

            try:
                status = PaymentStatus[r["status"]]  # по ИМЕНИ
            except KeyError:
                self.report.warn(f"payment {r['id']}: неизвестный статус {r['status']}")
                self.report.add("payments_skipped")
                continue

            model = PaymentModel(
                external_id=r["external_id"][:64],
                user_id=user_id,
                method=method,
                amount=money(r["amount"]),
                currency=(r["currency"] or "RUB")[:8],
                status=status,
                purpose=PaymentPurpose.BALANCE_TOPUP,
                purpose_id=None,
                description=(r["description"] or None) and r["description"][:256],
                meta=dict(r["meta"] or {}),
                expires_at=r["expires_at"],
                paid_at=r["paid_at"],
                created_at=r["created_at"],
            )
            self.dst.add(model)
            self.report.add("payments")
            self.report.add(f"payments_status_{status.value}")

        await self.dst.flush()

    # ---------------------------------------------------------- future slots

    async def migrate_future_slots(self) -> None:
        """Будущие занятые слоты → slot_converted (с дедупом)."""
        rows = await self.src.fetch(
            "SELECT s.*, a.user_id FROM slot_settings s "
            "LEFT JOIN ads a ON a.id = s.ad_id "
            "WHERE s._date >= CURRENT_DATE AND s.ad_id IS NOT NULL "
            "ORDER BY s.id"
        )

        seen: set[tuple[int, date, time]] = set()

        for r in rows:
            region_id = self.region_map.get(r["region_id"]) if r["region_id"] else None
            new_ad_id = self.ad_map.get(r["ad_id"]) or self.store_ad_map.get(
                r["user_id"]
            )
            user_id = self.user_map.get(r["user_id"]) if r["user_id"] else None

            if region_id is None or user_id is None:
                self.report.add("future_slots_skipped")
                continue

            t = parse_slot_time(r["time"])
            if t is None:
                self.report.add("future_slots_skipped")
                continue

            key = (region_id, r["_date"], t)
            if key in seen:
                self.report.add("future_slots_duplicates")
                continue
            seen.add(key)

            self.dst.add(
                SlotConvertedModel(
                    region_id=region_id,
                    slot_day=r["_date"],
                    slot_time=t,
                    ad_id=new_ad_id,
                    user_id=user_id,
                )
            )
            self.report.add("future_slots")

        await self.dst.flush()


# --------------------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------------------


async def main() -> int:
    parser = argparse.ArgumentParser(description="Перенос данных из старой БД")
    parser.add_argument(
        "--dry-run", action="store_true", help="не коммитить, только отчёт"
    )
    args = parser.parse_args()

    legacy_dsn = os.getenv("LEGACY_DSN")
    if not legacy_dsn:
        print("LEGACY_DSN не задан. Пример:", file=sys.stderr)
        print(
            "  LEGACY_DSN=postgresql://my_user:pass@1.2.3.4:5432/auto_db",
            file=sys.stderr,
        )
        return 1

    src = await asyncpg.connect(legacy_dsn)
    engine = create_async_engine(settings.db.postgres.url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print(f"{'СУХОЙ ПРОГОН' if args.dry_run else 'ПЕРЕНОС'} начат...")

    try:
        async with session_factory() as session:
            migrator = Migrator(src, session, args.dry_run)
            try:
                await migrator.run()
                if args.dry_run:
                    await session.rollback()
                    print("\n[dry-run] изменения откачены")
                else:
                    await session.commit()
                    print("\n[commit] изменения сохранены")
            except Exception:
                await session.rollback()
                print(migrator.report.render())
                raise
            print(migrator.report.render())
    finally:
        await src.close()
        await engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
