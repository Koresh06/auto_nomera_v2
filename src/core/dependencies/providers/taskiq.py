from dishka import Provider, Scope, provide
from taskiq_redis import RedisAsyncResultBackend, RedisScheduleSource, RedisStreamBroker

from src.application.ports.publication.publication_repo import PublicationRepository
from src.core.config import AppSettings

from src.application.ports.tasks.task_queue import TaskQueue
from src.application.ports.publication.scheduler import Scheduler
from src.infrastructure.scheduler.taskiq_queue_scheduler import TaskQueueScheduler
from src.infrastructure.tasks.taskiq_queue import TaskiqTaskQueue


class TaskiqProvider(Provider):
    @provide(scope=Scope.APP)
    def taskiq_broker(self, settings: AppSettings) -> RedisStreamBroker:
        result_backend = RedisAsyncResultBackend(redis_url=settings.db.redis.taskiq_url)
        return RedisStreamBroker(url=settings.db.redis.taskiq_url).with_result_backend(result_backend)
    
    @provide(scope=Scope.APP)
    def schedule_source(self, settings: AppSettings) -> RedisScheduleSource:
        return RedisScheduleSource(settings.db.redis.taskiq_url)
    
    @provide(scope=Scope.REQUEST)
    def task_queue(self, taskiq_broker: RedisStreamBroker, schedule_source: RedisScheduleSource) -> TaskQueue:
        return TaskiqTaskQueue(taskiq_broker, schedule_source)

    @provide(scope=Scope.REQUEST)
    def scheduler(
        self,
        task_queue: TaskQueue,
        publication_repo: PublicationRepository,
    ) -> Scheduler:
        return TaskQueueScheduler(
            queue=task_queue,
            publication_repo=publication_repo,
        )

    # @provide(scope=Scope.REQUEST)
    # def scheduler(self) -> Scheduler:       
    #     return DevScheduler() 