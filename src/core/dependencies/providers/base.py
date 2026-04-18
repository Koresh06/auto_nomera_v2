from dishka import Provider, provide, Scope

# from redis.asyncio import Redis

from src.core.config import AppSettings

# from src.infrastructure.database.sqlalchemy.connection import async_session_maker
# from src.infrastructure.database.redis.connection import get_redis_client


class BaseAppProvider(Provider):
    # HTTP CLIENT
    # @provide(scope=Scope.APP)
    # def get_http_client(self) -> BaseHttpClient:
    #     return HttpClient()

    # DATABASE
    # @provide(scope=Scope.REQUEST)
    # async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
    #     async with async_session_maker() as session:
    #         yield session

    # TRANSACTION MANAGER
    # @provide(scope=Scope.REQUEST)
    # def get_transaction_manager(self, session: AsyncSession) -> TransactionManager:
    #     return SQLAlchemyTransactionManager(session=session)

    # CONFIG
    @provide(scope=Scope.APP)
    def settings(self) -> AppSettings:
        return AppSettings()

    # REDIS
    # @provide(scope=Scope.APP)
    # def get_redis_client(self) -> Redis:
    #     return get_redis_client()

    # MESSAGE BROKER
    # @provide(scope=Scope.APP)
    # def get_message_broker(self, redis: Redis) -> BaseMessageBroker:
    #     return RedisMessageBroker(redis=redis)
    #     # return KafkaMessageBroker(producer=AIOKafkaProducer(
    #     #     bootstrap_servers=settings.kafka_url
    #     # ))
