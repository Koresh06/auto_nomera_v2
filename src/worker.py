from dishka import make_async_container

from src.core.dependencies.providers import make_base_providers
from src.core.dependencies.providers.taskiq import TaskiqProvider
from src.infrastructure.broker.instance import broker
from src.infrastructure.broker.taskiq import register_taskiq_tasks


container = make_async_container(
    *make_base_providers(),
    TaskiqProvider(),
)

register_taskiq_tasks(broker, container=container)
# print(f"Registered tasks: {list(broker.get_all_tasks().keys())}")

# taskiq worker src.worker:broker