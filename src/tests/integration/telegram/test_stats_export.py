"""Выгрузка статистики: конструктор в боте, настоящий файл, права."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO

import pytest
from aiogram.methods import SendDocument
from openpyxl import load_workbook

from src.application.use_cases.stats.globals import GetGlobalStatsRequest
from src.application.use_cases.user.admin_adjust_balance import (
    AdminAdjustBalanceCommand,
)
from src.domain.enums.payment import PaymentPurpose
from src.domain.enums.period import StatsPeriod
from src.domain.enums.publication import PublicationStatus
from src.domain.enums.role import UserRole
from src.presentation.telegram.features.admin.modules.stats.export import handlers
from src.presentation.telegram.features.admin.modules.stats.export.selection import (
    SECTIONS_WIDGET,
)

from ..factories import make_ad, make_payment, make_publication, make_region, make_user
from .conftest import ADMIN_TG_ID
from .harness import forge_click

NOW = datetime.now(timezone.utc)
PHONE = "+79991234567"


async def _seed(session):
    r1 = await make_region(session, title="Москва", channel_id=-1)
    r2 = await make_region(session, title="СПб", channel_id=-2)
    await make_user(session, r1.id, tg_id=ADMIN_TG_ID)
    u1 = await make_user(
        session,
        r1.id,
        tg_id=777,
        username="ivan",
        full_name="=Иван",
        phone=PHONE,
        balance=Decimal("100"),
    )
    u2 = await make_user(session, r2.id, tg_id=778)
    await make_payment(session, u1, external_id="m1", amount=Decimal("500"))
    await make_payment(
        session,
        u2,
        external_id="s1",
        amount=Decimal("200"),
        purpose=PaymentPurpose.SLOT,
    )
    ad = await make_ad(session, u1)
    await make_publication(session, ad, status=PublicationStatus.PUBLISHED)
    await session.commit()
    return r1, r2, u1, u2


async def _open(user):
    await user.send("/admin")
    await user.click("Выгрузка статистики")
    assert "Выгрузка статистики" in user.last.text


def _files(world):
    return world.tg.calls_of(SendDocument)


def _book(world, index=-1):
    return load_workbook(BytesIO(_files(world)[index].document.data))


async def _toggle_section(admin, title):
    await admin.click("Разделы")
    await admin.click(title)
    await admin.click("Готово")


def _column(sheet, title):
    headers = [c.value for c in sheet[1]]
    return [row[headers.index(title)].value for row in sheet.iter_rows(min_row=2)]


def _summary(book):
    return {row[1].value: row[2].value for row in book["Сводка"].iter_rows(min_row=2)}


async def test_default_report_has_summary_and_regions(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    assert "Сводка, По регионам" in admin.last.text
    assert "Месяц" in admin.last.text

    await admin.click("Скачать Excel")

    [sent] = _files(world)
    assert sent.chat_id == ADMIN_TG_ID
    assert sent.document.filename.endswith(".xlsx")
    book = _book(world)
    assert book.sheetnames == ["Параметры", "Сводка", "По регионам"]
    values = _summary(book)
    assert values["Выручка всего, руб."] == 200  # пополнение не выручка
    assert values["Поступило всего, руб."] == 700
    assert set(_column(book["По регионам"], "Регион")) == {"Москва", "СПб"}


async def test_dialog_reappears_under_the_file(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Скачать Excel")
    assert "Выгрузка статистики" in admin.last.text
    await admin.click("Скачать Excel")
    assert len(_files(world)) == 2


async def test_super_admin_gets_personal_data(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await _toggle_section(admin, "Пользователи")
    await admin.click("Скачать Excel")

    book = _book(world)
    assert "Телефон" in [c.value for c in book["Пользователи"][1]]
    assert PHONE in _column(book["Пользователи"], "Телефон")


async def test_appointed_admin_file_has_no_personal_data(world, session):
    """Назначенный через бота админ не должен вынести базу телефонов."""
    r1, _, _, _ = await _seed(session)
    await make_user(session, r1.id, tg_id=900, role=UserRole.ADMIN)
    await session.commit()
    admin = world.user(900)
    await _open(admin)
    assert "не попадут" in admin.last.text

    await admin.click("Разделы")
    for title in ("Пользователи", "Платежи", "Объявления"):
        await admin.click(title)
    await admin.click("Готово")
    await admin.click("Скачать Excel")

    book = _book(world)
    raw = BytesIO(_files(world)[-1].document.data).getvalue()
    assert PHONE.encode() not in raw
    for sheet in book.worksheets:
        for row in sheet.iter_rows(values_only=True):
            assert PHONE not in row and "ivan" not in row
    headers = {c.value for ws in book.worksheets[1:] for c in ws[1]}
    assert not headers & {"Телефон", "Username", "Имя", "Telegram ID", "Баланс"}
    assert "Пользователи" in book.sheetnames  # статистика при этом доступна


async def test_non_admin_cannot_reach_the_dialog(world, session):
    await _seed(session)
    outsider = world.user(777)
    await outsider.send("/admin")
    assert not any("Админ-панель" in m.text for m in outsider.messages)


async def test_revoked_admin_cannot_download_from_open_dialog(world, session):
    r1, _, _, _ = await _seed(session)
    user = await make_user(session, r1.id, tg_id=900, role=UserRole.ADMIN)
    await session.commit()
    admin = world.user(900)
    await _open(admin)

    user.revoke_admin()
    from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

    await SQLAlchemyUserRepo(session).save(user)
    await session.commit()

    await admin.click("Скачать Excel")

    assert _files(world) == []
    assert "Доступ к админ-панели закрыт" in admin.last_alert


async def test_user_text_in_file_stays_text(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await _toggle_section(admin, "Пользователи")
    await admin.click("Скачать Excel")

    assert "=Иван" in _column(_book(world)["Пользователи"], "Имя")


async def test_regions_filter_applies_to_preview_and_file(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Регионы")
    await admin.click("СПб")
    await admin.click("Готово")
    assert "Регионы: <b>СПб</b>" in admin.last.text

    await admin.click("Посмотреть итоги")
    assert "Выручка: 200.00" in admin.last.text
    assert "Поступило: 200.00" in admin.last.text

    await admin.click("Скачать Excel")
    book = _book(world)
    assert _column(book["По регионам"], "Регион") == ["СПб"]
    assert book["Параметры"]["B2"].value == "СПб"


async def test_all_regions_button_clears_selection(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Регионы")
    await admin.click("СПб")
    await admin.click("Все регионы")
    assert "Регионы: <b>все</b>" in admin.last.text


async def test_preview_shows_row_counts(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await _toggle_section(admin, "Платежи")
    await admin.click("Посмотреть итоги")
    assert "Платежи: <b>2</b>" in admin.last.text


async def test_no_sections_is_refused(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Разделы")
    await admin.click("Сводка")
    await admin.click("По регионам")
    await admin.click("Готово")
    assert "не выбраны" in admin.last.text

    await admin.click("Скачать Excel")
    assert "хотя бы один раздел" in admin.last_alert
    await admin.click("Посмотреть итоги")
    assert "хотя бы один раздел" in admin.last_alert
    assert _files(world) == []


async def test_forged_section_is_ignored(world, session):
    """Значение чекбокса приходит из callback_data: чужое не должно ронять."""
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Разделы")
    await forge_click(admin, f"{SECTIONS_WIDGET}:hacked")
    await admin.click("Готово")
    await admin.click("Скачать Excel")
    assert _book(world).sheetnames == ["Параметры", "Сводка", "По регионам"]


async def test_custom_dates(world, session):
    _, _, user, _ = await _seed(session)
    old = NOW - timedelta(days=400)
    await make_payment(
        session, user, external_id="old", amount=Decimal("9000"), paid_at=old
    )
    await session.commit()
    admin = world.admin()
    await _open(admin)
    await admin.click("Период")
    await admin.click("Свои даты")

    await admin.send("31.12.2020 - 01.01.2020")
    assert any("позже конца" in m.text for m in admin.messages)
    await admin.send("не дата")
    assert any("Пример" in m.text for m in admin.messages)

    raw = f"{old - timedelta(days=1):%d.%m.%Y} - {old + timedelta(days=1):%d.%m.%Y}"
    await admin.send(raw)
    assert raw.replace(" - ", " — ") in admin.last.text

    await admin.click("Скачать Excel")
    assert _summary(_book(world))["Поступило всего, руб."] == 9000


async def test_preset_period_is_highlighted_and_applied(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Период")
    await admin.click("Всё")
    assert "Всё время" in admin.last.text
    await admin.click("Период")
    assert admin.find_button("🟢 Всё")


async def test_custom_period_highlights_only_custom_button(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Период")
    await admin.click("Свои даты")
    await admin.send("01.10.2026")
    await admin.click("Период")
    assert admin.find_button("🟢 📆 Свои даты")
    assert not any(t.startswith("🟢 Месяц") for t in admin.last.button_texts)


async def test_second_tap_during_export_does_not_build_twice(world, session):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    handlers._exports_in_progress.add(ADMIN_TG_ID)
    try:
        await admin.click("Скачать Excel")
    finally:
        handlers._exports_in_progress.discard(ADMIN_TG_ID)

    assert "уже готовится" in admin.last_alert
    assert _files(world) == []


async def test_failed_export_does_not_lock_the_admin_out(world, session, monkeypatch):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    monkeypatch.setattr(handlers, "MAX_FILE_BYTES", 1)

    await admin.click("Скачать Excel")

    assert _files(world) == []
    assert any("больше 50 МБ" in m.text for m in admin.messages)
    assert ADMIN_TG_ID not in handlers._exports_in_progress


async def test_global_stats_screen_agrees_with_the_file(world, session):
    """Экран «Общая статистика» и Excel считают деньги одинаково."""
    _, _, user, _ = await _seed(session)
    await world.mediator_call(
        AdminAdjustBalanceCommand(user_id=user.id, amount=Decimal("50"))
    )

    stats = await world.mediator_call(GetGlobalStatsRequest(period=StatsPeriod.MONTH))

    assert stats.total_amount == Decimal("200")
    assert stats.total_purchases == 1
    admin = world.admin()
    await admin.send("/admin")
    await admin.click("Общая статистика")
    assert "Покупок: <b>1</b>" in admin.last.text


@pytest.mark.parametrize("label", ["Сегодня", "Неделя", "Месяц", "Всё"])
async def test_every_preset_builds_a_file(world, session, label):
    await _seed(session)
    admin = world.admin()
    await _open(admin)
    await admin.click("Период")
    await admin.click(label)
    await _toggle_section(admin, "Публикации")
    await admin.click("Скачать Excel")
    assert "Публикации" in _book(world).sheetnames
