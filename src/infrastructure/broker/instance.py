from src.core.config import settings
from taskiq import SimpleRetryMiddleware
from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend

from src.infrastructure.broker.middleware.sentry import SentryMiddleware


result_backend = RedisAsyncResultBackend(redis_url=settings.db.redis.taskiq_url)
broker = (
    RedisStreamBroker(
        url=settings.db.redis.taskiq_url,
        idle_timeout=1800000,  # 30 минут
    )
    .with_result_backend(result_backend)
    .with_middlewares(
        SentryMiddleware(),
        # AUD-12: раньше при любой разовой транзиентной ошибке (сетевой
        # сбой Telegram API, временная недоступность БД) задача падала один
        # раз и больше не повторялась — публикация оставалась незапланированной
        # навсегда, пока админ не находил её вручную. default_retry_label=False:
        # ретраи включены только там, где явно указан label retry_on_error=True
        # на конкретной задаче (см. broker/taskiq.py), а не для всех задач по
        # умолчанию — у рассылок (execute_mailing_batch) и части других задач
        # свой встроенный учёт частичных сбоев, слепой повтор всей задачи там
        # мог бы продублировать уже отправленные сообщения.
        SimpleRetryMiddleware(default_retry_count=3, default_retry_label=False),
    )
)
