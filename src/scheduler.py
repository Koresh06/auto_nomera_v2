from taskiq import TaskiqScheduler
from taskiq_redis import RedisScheduleSource
from src.core.config import settings
from src.worker import broker


schedule_source = RedisScheduleSource(settings.db.redis.taskiq_url)
scheduler = TaskiqScheduler(broker=broker, sources=[schedule_source])

# taskiq scheduler src.scheduler:scheduler
