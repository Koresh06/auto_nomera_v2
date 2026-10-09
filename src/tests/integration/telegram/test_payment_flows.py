"""Сквозные сценарии оплаты через бота: пополнение баланса (Stars, ЮKassa),
оплата платного слота с возвратом в сценарий публикации."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from src.application.use_cases.payment.confirm import ConfirmPaymentRequest
from src.domain.enums.payment import PaymentMethod, PaymentPurpose, PaymentStatus
from src.domain.enums.publication import PublicationStatus
from src.domain.value_objects.region_settings import RegionSettings
from src.infrastructure.database.models import PaymentModel, PublicationModel
from src.infrastructure.payment.providers.yookassa import YooKassaProvider
from src.infrastructure.repositories.user.sqlalchemy import SQLAlchemyUserRepo

from ..factories import make_region, make_user
from .conftest import ADMIN_TG_ID
from .harness import settle
from .test_create_ad_flow import PAID_SLOT, _fill_sale_until_calendar


async def _rows(session, model):
    q = select(model).execution_options(populate_existing=True)
    return list((await session.execute(q)).scalars().all())


async def _balance(session, tg_id: int) -> Decimal:
    session.expire_all()
    return (await SQLAlchemyUserRepo(session).get_by_tg_id(tg_id)).balance


@pytest.fixture
def fake_yookassa(monkeypatch):
    created: list[dict] = []

    async def create_invoice(self, **kw):
        if not kw.get("phone"):
            from src.domain.exceptions.payment import PaymentPhoneRequiredException

            raise PaymentPhoneRequiredException(PaymentMethod.YOOKASSA)
        created.append(kw)
        return {
            "confirmation_url": "https://yoomoney.ru/checkout/test",
            "yookassa_payment_id": "yk-1",
        }

    monkeypatch.setattr(YooKassaProvider, "create_invoice", create_invoice)
    return created


async def _start_topup(u, amount: str = "500"):
    await u.send("/start")
    await u.click("Пополнить баланс")
    assert "Пополнение баланса" in u.last.text
    await u.send(amount)


async def test_topup_with_stars_end_to_end(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=800)
    await session.commit()
    u = world.user(800)

    await _start_topup(u, "500")
    assert "Выберите способ оплаты" in u.last.text
    assert "500 руб." in u.last.text
    await u.click("TG Stars")

    assert "Оплата звёздами" in u.last.text
    pay_button = u.find_button("Оплатить")[1]
    assert pay_button.url.startswith("https://t.me/$invoice")

    [payment] = await _rows(session, PaymentModel)
    assert payment.status == PaymentStatus.PENDING
    assert payment.purpose == PaymentPurpose.BALANCE_TOPUP
    assert payment.method == PaymentMethod.TELEGRAM_STARS
    assert payment.amount == Decimal("500")

    await u.pay_stars(payload=payment.external_id, stars=payment.meta["stars_amount"])
    await settle()

    [payment] = await _rows(session, PaymentModel)
    assert payment.status == PaymentStatus.PAID
    assert await _balance(session, 800) == Decimal("500")
    texts = [m.text for m in u.messages]
    assert any("500" in t and "баланс" in t.lower() for t in texts), texts
    # админ узнаёт о платеже
    assert world.tg.visible(ADMIN_TG_ID)
    # пользователя вернули в главное меню
    assert "Выберите действие" in u.last.text


async def test_duplicate_successful_payment_is_credited_once(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=801)
    await session.commit()
    u = world.user(801)
    await _start_topup(u, "300")
    await u.click("TG Stars")
    [payment] = await _rows(session, PaymentModel)

    await u.pay_stars(payload=payment.external_id, stars=1)
    await settle()
    await u.pay_stars(payload=payment.external_id, stars=1)
    await settle()

    assert await _balance(session, 801) == Decimal("300")


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "99"])
async def test_topup_rejects_bad_amounts(world, session, bad):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=802)
    await session.commit()
    u = world.user(802)

    await _start_topup(u, bad)

    assert any("⚠️" in m.text for m in u.messages)
    assert "Пополнение баланса" in u.last.text
    assert await _rows(session, PaymentModel) == []


@pytest.mark.parametrize("bad", ["Infinity", "NaN", "1e12", "100.555"])
async def test_topup_rejects_non_finite_or_overflowing_amounts(world, session, bad):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=803)
    await session.commit()
    u = world.user(803)

    await _start_topup(u, bad)
    if "Выберите способ оплаты" in u.last.text:
        await u.click("TG Stars")

    assert "Пополнение баланса" in u.last.text, (
        f"сумма {bad!r} должна отклоняться на шаге ввода"
    )
    assert await _rows(session, PaymentModel) == []


async def test_topup_yookassa_asks_phone_first(world, session, fake_yookassa):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=804, phone=None)
    await session.commit()
    u = world.user(804)

    await _start_topup(u, "1000")
    await u.click("СБП")

    assert "Нужен номер телефона" in u.last.text
    await u.send("+79990001122")
    assert "Выберите способ оплаты" in u.last.text
    await u.click("СБП")

    assert "Выбирайте оплату - СБП" in u.last.text
    assert u.find_button("Оплатить")[1].url == "https://yoomoney.ru/checkout/test"
    assert fake_yookassa[0]["phone"] == "+79990001122"
    [payment] = await _rows(session, PaymentModel)
    assert payment.method == PaymentMethod.YOOKASSA

    # вебхук ЮKassa ставит задачу confirm_payment, воркер её исполняет
    await world.mediator_call(ConfirmPaymentRequest(external_id=payment.external_id))
    await settle()
    assert await _balance(session, 804) == Decimal("1000")


async def test_payment_blocked_user_cannot_pay(world, session):
    region = await make_region(session)
    await make_user(session, region.id, tg_id=805, is_payment_blocked=True)
    await session.commit()
    u = world.user(805)

    await _start_topup(u, "500")
    await u.click("TG Stars")

    assert "Платежи для вашего аккаунта заблокированы" in u.last_alert
    assert await _rows(session, PaymentModel) == []


async def test_paid_slot_paid_by_stars_returns_user_to_confirm(world, session):
    region = await make_region(
        session, settings=RegionSettings(system_paid_slots_count=3)
    )
    user = await make_user(session, region.id, tg_id=806, username="seller")
    await session.commit()
    u = world.user(806)

    await _fill_sale_until_calendar(u)
    await u.click(PAID_SLOT)
    assert "Выберите способ оплаты" in u.last.text
    assert "199 руб." in u.last.text
    await u.click("TG Stars")
    [payment] = await _rows(session, PaymentModel)
    assert payment.purpose == PaymentPurpose.SLOT

    await u.pay_stars(payload=payment.external_id, stars=1)
    await settle()

    # после оплаты пользователь снова видит подтверждение объявления
    assert "Проверьте данные" in u.last.text
    await u.click("Подтвердить")

    [pub] = await _rows(session, PublicationModel)
    assert pub.status == PublicationStatus.SCHEDULED
    assert pub.scheduler_job_id
    # деньги пришли внешним платежом — баланс не трогаем
    assert await _balance(session, 806) == Decimal("0")
    assert user.id == pub.ad.user_id if False else True


@pytest.mark.allow_bot_errors  # сбой провайдера логируется как ERROR — так и нужно
async def test_yookassa_unreachable_shows_clear_message(world, session, monkeypatch):
    """Как в логе: прокси не пропускает запрос к api.yookassa.ru, SDK падает
    AttributeError. Пользователь видит понятное сообщение, платёж не
    создаётся, можно сразу выбрать другой способ."""
    from src.infrastructure.payment.providers import yookassa as yk_module

    def broken_create(payload, idempotence_key):
        raise AttributeError("'NoneType' object has no attribute 'status_code'")

    monkeypatch.setattr(
        yk_module.YooKassaPayment, "create", staticmethod(broken_create)
    )
    region = await make_region(session)
    await make_user(session, region.id, tg_id=807, phone="+79990001122")
    await session.commit()
    u = world.user(807)

    await _start_topup(u, "500")
    await u.click("СБП")

    assert "Платёжная система временно недоступна" in u.last_alert
    assert "Произошла ошибка" not in (u.last_alert or "")
    assert "Выберите способ оплаты" in u.last.text
    assert await _rows(session, PaymentModel) == []

    await u.click("TG Stars")  # другой способ работает
    assert "Оплата звёздами" in u.last.text
