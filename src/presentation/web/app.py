from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from dishka.integrations.fastapi import FastapiProvider
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from taskiq_redis import RedisStreamBroker

from src.core.observability.sentry import setup_sentry
from src.core.dependencies.providers import make_base_providers
from src.infrastructure.broker.taskiq import register_taskiq_tasks
from src.presentation.web.routers.yookassa import router as yookassa_router
from src.presentation.web.routers.result import router as result_router


container = make_async_container(*make_base_providers(), FastapiProvider())


@asynccontextmanager
async def lifespan(app: FastAPI):
    broker: RedisStreamBroker = await container.get(RedisStreamBroker)
    register_taskiq_tasks(broker, container=container)
    yield


def create_app() -> FastAPI:
    setup_sentry(integrations=[FastApiIntegration()])
    app = FastAPI(lifespan=lifespan)

    @app.get("/sentry-test")
    async def sentry_test():
        raise RuntimeError("Sentry test from web")

    app.include_router(yookassa_router)
    app.include_router(result_router)
    setup_dishka(container=container, app=app)
    return app


# uvicorn src.presentation.web.app:create_app --host 0.0.0.0 --port 8080 --factory
