from datetime import datetime
from src.application.ports.publication.scheduler import Scheduler


class DevScheduler(Scheduler):
    async def schedule_publication(self, *, publication_id: int, run_at_utc: datetime) -> None:
        print(f"[SCHEDULER] schedule_publication id={publication_id} run_at_utc={run_at_utc.isoformat()}")

    async def cancel_publication(self, *, publication_id: int) -> None:
        print(f"[SCHEDULER] cancel_publication id={publication_id}")

    async def schedule_publish_now(self, *, publication_id: int) -> None:
        print(f"[SCHEDULER] schedule_publish_now id={publication_id}")

    async def schedule_unpin(self, *, channel_id: int, message_id: int, run_at_utc: datetime) -> None:
        print(f"[SCHEDULER] schedule_unpin channel_id={channel_id} msg={message_id} at={run_at_utc.isoformat()}")
