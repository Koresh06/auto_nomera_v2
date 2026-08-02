import sentry_sdk

from src.core.config import settings


def setup_sentry(*, integrations: list | None = None) -> None:
    if not settings.app.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.app.sentry_dsn,
        traces_sample_rate=0.1,
        environment=getattr(settings.app, "env", None),
        integrations=integrations or [],
    )
