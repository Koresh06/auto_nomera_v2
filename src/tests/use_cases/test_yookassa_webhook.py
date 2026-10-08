"""
Regression tests for AUD-01: the YooKassa webhook endpoint used to trust the
POST body directly (event/status/metadata), with no signature or server-side
verification. Since external_id leaks to the user via the return_url, anyone
could self-confirm an unpaid payment by POSTing a forged "payment.succeeded"
body. The fix calls YooKassaProvider.verify_payment() (an authenticated
Payment.find_one against YooKassa's API) and only trusts *that* response.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.application.services.payment.provider_registry import PaymentProviderRegistry
from src.core.config.payment import YooKassaSettings
from src.domain.enums.payment import PaymentMethod
from src.infrastructure.payment.providers.yookassa import YooKassaProvider
from src.presentation.web.routers.yookassa import process_yookassa_webhook


class FakeTaskQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple]] = []

    async def enqueue(self, *, task_name: str, args: tuple) -> str | None:
        self.enqueued.append((task_name, args))
        return "job-id"

    async def schedule(self, *, task_name, args, run_at_utc):
        return "job-id"

    async def cancel(self, *, job_id: str) -> None:
        pass


class StubbedYooKassaProvider(YooKassaProvider):
    """Real YooKassaProvider, but verify_payment() is stubbed to avoid any
    network call — it returns a pre-baked response as if YooKassa's API had
    been asked directly, which is exactly what the fix is supposed to rely on
    instead of the untrusted POST body."""

    def __init__(self, verified_response) -> None:
        super().__init__(account_id=1, secret_key="test", settings=YooKassaSettings())
        self._verified_response = verified_response

    async def verify_payment(self, *, yookassa_payment_id: str):
        return self._verified_response


def make_registry(provider: YooKassaProvider) -> PaymentProviderRegistry:
    registry = PaymentProviderRegistry()
    registry.register(PaymentMethod.YOOKASSA, provider)
    return registry


async def test_forged_webhook_is_ignored_when_yookassa_says_not_paid():
    """The attack from AUD-01: a user POSTs {"event": "payment.succeeded"} for
    their own unpaid external_id. The forged payload claims success, but the
    verified lookup (what YooKassa actually says) reports "pending"/not paid —
    nothing must be enqueued."""
    verified = SimpleNamespace(
        status="pending", paid=False, metadata={"external_id": "ext-victim"}
    )
    provider = StubbedYooKassaProvider(verified)
    queue = FakeTaskQueue()

    forged_payload = {
        "event": "payment.succeeded",
        "object": {
            "id": "yk-payment-id",
            "status": "succeeded",  # lies — attacker-controlled
            "metadata": {"external_id": "ext-victim"},
        },
    }

    result = await process_yookassa_webhook(
        forged_payload, task_queue=queue, provider_registry=make_registry(provider)
    )

    assert result == {"status": "ok"}
    assert queue.enqueued == []  # nothing confirmed despite the forged claim


async def test_genuine_succeeded_payment_enqueues_confirm():
    verified = SimpleNamespace(
        status="succeeded", paid=True, metadata={"external_id": "ext-real"}
    )
    provider = StubbedYooKassaProvider(verified)
    queue = FakeTaskQueue()

    payload = {
        "event": "payment.succeeded",
        "object": {"id": "yk-payment-id", "metadata": {"external_id": "ext-real"}},
    }

    await process_yookassa_webhook(
        payload, task_queue=queue, provider_registry=make_registry(provider)
    )

    assert queue.enqueued == [("confirm_payment", ("ext-real",))]


async def test_genuine_canceled_payment_enqueues_mark_failed():
    verified = SimpleNamespace(
        status="canceled", paid=False, metadata={"external_id": "ext-real"}
    )
    provider = StubbedYooKassaProvider(verified)
    queue = FakeTaskQueue()

    payload = {
        "event": "payment.canceled",
        "object": {"id": "yk-payment-id", "metadata": {"external_id": "ext-real"}},
    }

    await process_yookassa_webhook(
        payload, task_queue=queue, provider_registry=make_registry(provider)
    )

    assert queue.enqueued == [("mark_payment_failed", ("ext-real",))]


async def test_verification_failure_returns_502_and_enqueues_nothing():
    """verify_payment() returning None (network error talking to YooKassa)
    must not be treated as success — we ask for a retry instead."""
    provider = StubbedYooKassaProvider(None)
    queue = FakeTaskQueue()

    payload = {
        "event": "payment.succeeded",
        "object": {"id": "yk-payment-id", "metadata": {"external_id": "ext-real"}},
    }

    with pytest.raises(HTTPException) as exc_info:
        await process_yookassa_webhook(
            payload, task_queue=queue, provider_registry=make_registry(provider)
        )

    assert exc_info.value.status_code == 502
    assert queue.enqueued == []


async def test_missing_payment_id_is_rejected():
    provider = StubbedYooKassaProvider(None)
    queue = FakeTaskQueue()

    with pytest.raises(HTTPException) as exc_info:
        await process_yookassa_webhook(
            {"event": "payment.succeeded", "object": {}},
            task_queue=queue,
            provider_registry=make_registry(provider),
        )

    assert exc_info.value.status_code == 400
    assert queue.enqueued == []


async def test_verified_response_without_external_id_is_rejected():
    verified = SimpleNamespace(status="succeeded", paid=True, metadata={})
    provider = StubbedYooKassaProvider(verified)
    queue = FakeTaskQueue()

    payload = {"event": "payment.succeeded", "object": {"id": "yk-payment-id"}}

    with pytest.raises(HTTPException) as exc_info:
        await process_yookassa_webhook(
            payload, task_queue=queue, provider_registry=make_registry(provider)
        )

    assert exc_info.value.status_code == 400
    assert queue.enqueued == []
