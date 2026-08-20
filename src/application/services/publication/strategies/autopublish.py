from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from src.domain.entities.publication import Publication
from src.domain.entities.publication_service import PublicationService
from src.application.services.publication.context import ServiceContext
from src.domain.value_objects.slot_key import SlotKey


class AutopublishStrategy:
    async def apply(
        self,
        publication: Publication,
        service: PublicationService,
        context: ServiceContext,
    ) -> None:
        if service.params is None:
            service.mark_used()
            return

        days = service.params.get("days", 7)

        region_tz = ZoneInfo(context.region.timezone.value)
        now_utc = datetime.now(timezone.utc)
        now_local = now_utc.astimezone(region_tz)
        today_local = now_local.date()

        # Время серии — всегда слот-время родителя (или фактическое время
        # выхода, если слота нет).
        if publication.slot is not None:
            base_time = publication.slot.local_time
        elif publication.published_at_utc is not None:
            base_time = (
                publication.published_at_utc.astimezone(region_tz)
                .time()
                .replace(second=0, microsecond=0)
            )
        else:
            base_time = now_local.time().replace(second=0, microsecond=0)

        # База отсчёта:
        # 1) Родитель уже фактически вышел (в т.ч. через PRIORITY_PUBLISH) —
        #    считаем от дня фактической публикации.
        # 2) Иначе — от планового слота.
        if publication.published_at_utc is not None:
            base_day = publication.published_at_utc.astimezone(region_tz).date()
        elif publication.slot is not None:
            base_day = publication.slot.local_day
        else:
            base_day = today_local

        # Докупка к старой публикации (база в прошлом): отсчёт от момента
        # покупки. Если слот-время сегодня ещё впереди — первый пост сегодня,
        # иначе — с завтрашнего дня. Сдвигаем базу так, чтобы base + 1 день
        # дал нужный первый пост.
        if base_day < today_local:
            if now_local.time() < base_time:
                base_day = today_local - timedelta(days=1)  # первый пост сегодня
            else:
                base_day = today_local  # первый пост завтра

        # days постов: дни +1 ... +days от базы
        for i in range(1, days + 1):
            next_slot = SlotKey(
                region_id=publication.region_id,
                local_day=base_day + timedelta(days=i),
                local_time=base_time,
            )
            publish_at_utc = context.time_resolver.resolve_publish_at_utc(
                tz=context.region.timezone,
                slot=next_slot,
            )

            if publish_at_utc <= now_utc:
                continue

            new_pub = Publication(
                ad_id=publication.ad_id,
                region_id=publication.region_id,
                is_child=True,
            )
            new_pub.schedule(slot=next_slot, publish_at_utc=publish_at_utc)
            created = await context.publication_repo.create(new_pub)

            await context.scheduler.schedule_publication(
                publication_id=created.id,
                run_at_utc=publish_at_utc,
            )

            created = await context.publication_repo.get_by_id(created.id)

            notify_at = publish_at_utc - timedelta(
                hours=context.pre_publication_window_hours
            )
            if notify_at > now_utc:
                await context.task_queue.schedule(
                    task_name="notify_pre_publication_users",
                    args=(publication.ad_id,),
                    run_at_utc=notify_at,
                )
                created.notify_scheduled = True
                await context.publication_repo.save(created)

        service.mark_used()
