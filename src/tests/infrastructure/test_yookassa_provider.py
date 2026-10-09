"""YooKassaProvider: что именно уходит в API ЮKassa и как обрабатываются
ошибки. SDK подменён — сеть не используется."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.exceptions.payment import PaymentProviderUnavailableException
from src.core.config.payment import YooKassaSettings
from src.domain.entities.payment import Payment
from src.domain.enums.payment import PaymentMethod, PaymentPurpose
from src.domain.exceptions.payment import PaymentPhoneRequiredException
from src.infrastructure.payment.providers import yookassa as module
from src.infrastructure.payment.providers.yookassa import YooKassaProvider


@pytest.fixture
def provider():
    return YooKassaProvider(
        account_id=1,
        secret_key="s",
        settings=YooKassaSettings(return_url="https://site/payment/return"),
    )


@pytest.fixture
def sdk(monkeypatch):
    calls: dict = {"create": [], "find": []}
    behaviour: dict = {"create": None, "find": None}

    def create(payload, idempotence_key):
        calls["create"].append((payload, idempotence_key))
        if isinstance(behaviour["create"], Exception):
            raise behaviour["create"]
        return SimpleNamespace(
            id="yk-1",
            confirmation=SimpleNamespace(confirmation_url="https://yoomoney/pay"),
        )

    def find_one(payment_id):
        calls["find"].append(payment_id)
        if isinstance(behaviour["find"], Exception):
            raise behaviour["find"]
        return SimpleNamespace(id=payment_id, status="succeeded", paid=True)

    monkeypatch.setattr(module.YooKassaPayment, "create", staticmethod(create))
    monkeypatch.setattr(module.YooKassaPayment, "find_one", staticmethod(find_one))
    return calls, behaviour


async def test_create_invoice_payload(provider, sdk):
    calls, _ = sdk

    meta = await provider.create_invoice(
        user_id=5,
        amount=Decimal("199"),
        currency="RUB",
        description="Закрепление",
        external_id="ext-1",
        phone="+7 (999) 123-45-67",
        chat_id=777,
    )

    assert meta == {
        "yookassa_payment_id": "yk-1",
        "confirmation_url": "https://yoomoney/pay",
    }
    [(payload, key)] = calls["create"]
    assert key  # ключ идемпотентности передаётся
    assert payload["amount"] == {"value": "199.00", "currency": "RUB"}
    assert payload["capture"] is True
    assert payload["confirmation"]["return_url"] == (
        "https://site/payment/return?external_id=ext-1"
    )
    assert payload["metadata"] == {"user_id": 5, "chat_id": 777, "external_id": "ext-1"}
    assert payload["receipt"]["customer"]["phone"] == "79991234567"
    [item] = payload["receipt"]["items"]
    assert item["amount"]["value"] == "199.00" and item["description"] == "Закрепление"


async def test_create_invoice_requires_phone_for_receipt(provider, sdk):
    calls, _ = sdk
    with pytest.raises(PaymentPhoneRequiredException):
        await provider.create_invoice(
            user_id=5,
            amount=Decimal("100"),
            currency="RUB",
            description="d",
            external_id="e",
            phone="",
        )
    assert calls["create"] == []


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("API down"),
        # ровно то, что SDK ЮKassa бросает при отказе прокси (ответа нет)
        AttributeError("'NoneType' object has no attribute 'status_code'"),
    ],
)
async def test_create_invoice_api_failure_means_provider_unavailable(
    provider, sdk, error
):
    _, behaviour = sdk
    behaviour["create"] = error
    with pytest.raises(PaymentProviderUnavailableException):
        await provider.create_invoice(
            user_id=5,
            amount=Decimal("100"),
            currency="RUB",
            description="d",
            external_id="e",
            phone="79990000000",
        )


async def test_create_invoice_timeout_means_provider_unavailable(provider, monkeypatch):
    async def timeout(*a, **kw):
        raise asyncio.TimeoutError

    monkeypatch.setattr(module.asyncio, "wait_for", timeout)
    with pytest.raises(PaymentProviderUnavailableException):
        await provider.create_invoice(
            user_id=5,
            amount=Decimal("100"),
            currency="RUB",
            description="d",
            external_id="e",
            phone="79990000000",
        )


async def test_stars_network_error_means_provider_unavailable():
    from aiogram.exceptions import TelegramNetworkError
    from aiogram.methods import CreateInvoiceLink

    from src.infrastructure.payment.providers.telegram_stars import (
        TelegramStarsProvider,
    )

    class Bot:
        async def create_invoice_link(self, **kw):
            raise TelegramNetworkError(
                method=CreateInvoiceLink(
                    title="t", description="d", payload="p", currency="XTR", prices=[]
                ),
                message="connection reset",
            )

    stars = TelegramStarsProvider(bot=Bot(), xtr_to_rub_rate=Decimal("1.5"))
    with pytest.raises(PaymentProviderUnavailableException):
        await stars.create_invoice(
            user_id=1,
            amount=Decimal("300"),
            currency="RUB",
            description="d",
            external_id="e",
        )


async def test_verify_payment_asks_api_and_returns_its_answer(provider, sdk):
    calls, _ = sdk
    verified = await provider.verify_payment(yookassa_payment_id="yk-9")
    assert calls["find"] == ["yk-9"]
    assert (verified.status, verified.paid) == ("succeeded", True)


async def test_verify_payment_returns_none_on_errors(provider, sdk):
    _, behaviour = sdk
    behaviour["find"] = ConnectionError("network")
    assert await provider.verify_payment(yookassa_payment_id="x") is None


async def test_verify_payment_returns_none_on_timeout(provider, monkeypatch):
    async def timeout(*a, **kw):
        raise asyncio.TimeoutError

    monkeypatch.setattr(module.asyncio, "wait_for", timeout)
    assert await provider.verify_payment(yookassa_payment_id="x") is None


async def test_instructions_and_webhook_helpers(provider):
    payment = Payment(
        external_id="e",
        user_id=1,
        method=PaymentMethod.YOOKASSA,
        amount=Decimal("1"),
        purpose=PaymentPurpose.BALANCE_TOPUP,
        meta={"confirmation_url": "https://pay"},
    )
    assert await provider.get_payment_instructions(payment) == {
        "type": "deeplink",
        "url": "https://pay",
    }
    assert (
        await provider.handle_webhook({"object": {"metadata": {"external_id": "z"}}})
        == "z"
    )
    assert await provider.handle_webhook({}) is None
