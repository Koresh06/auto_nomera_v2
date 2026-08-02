import sentry_sdk
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult
from typing import Any


class SentryMiddleware(TaskiqMiddleware):
    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:
        sentry_sdk.set_context(
            "taskiq",
            {
                "task_name": message.task_name,
                "task_id": message.task_id,
                "args": message.args,
                "kwargs": message.kwargs,
            },
        )
        sentry_sdk.capture_exception(exception)
