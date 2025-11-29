from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from vihorki.domain.repositories.metric_repo import IMetricRepository
from vihorki.domain.entities.metric import Metric
from vihorki.domain.entities.hit import Hit
from vihorki.domain.entities.visit import Visit
from vihorki.infrastructure.postgres.on_startup.init_tables import VisitTable, HitTable


def to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC)
        return dt.replace(tzinfo=None)
    return dt


class MetricRepository(IMetricRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_timedelta(self, time_start: datetime, time_end: datetime) -> list[Metric]:
        stmt_visits = select(VisitTable).where(
            VisitTable.date_time.between(to_naive_utc(time_start), to_naive_utc(time_end))
        )
        result_visits = await self.session.execute(stmt_visits)
        visits = result_visits.scalars().all()
        res = await self._build_metrics(visits)
        return res

    async def get_by_new_users(self, is_new_user: int) -> list[Metric]:
        flag = bool(is_new_user)
        stmt_visits = select(VisitTable).where(VisitTable.is_new_user == flag)
        result_visits = await self.session.execute(stmt_visits)
        visits = result_visits.scalars().all()
        res = await self._build_metrics(visits)
        return res

    async def get_by_region(self, region_country: str, region_city: str) -> list[Metric]:
        stmt_visits = select(VisitTable).where(VisitTable.region_city == region_city)
        result_visits = await self.session.execute(stmt_visits)
        visits = result_visits.scalars().all()
        res = await self._build_metrics(visits)
        return res

    async def get_by_device(self, device: str, operating_system: str, is_landscape: str | None = None) -> list[Metric]:
        device_category = int(device)

        stmt_visits = select(VisitTable).where(
            and_(VisitTable.device_category == device_category, VisitTable.operating_system == operating_system)
        )

        if is_landscape is not None:
            stmt_visits = stmt_visits.where(
                VisitTable.screen_orientation_name == ('landscape' if is_landscape == '1' else 'portrait')
            )

        result_visits = await self.session.execute(stmt_visits)
        visits = result_visits.scalars().all()
        create_metrics = await self._build_metrics(visits)
        return create_metrics

    async def _build_metrics(self, visits: list[VisitTable]) -> list[Metric]:
        metrics = []
        for visit in visits:
            visit_dto = Visit(
                visit_id=visit.visit_id,
                watch_ids=visit.watch_ids,
                date_time=visit.date_time,
                is_new_user=visit.is_new_user,
                start_url=visit.start_url,
                end_url=visit.end_url,
                page_views=visit.page_views,
                visit_duration=visit.visit_duration,
                region_city=visit.region_city,
                client_id=visit.client_id,
                last_search_engine_root=visit.last_search_engine_root,
                device_category=visit.device_category,
                mobile_phone=visit.mobile_phone,
                mobile_phone_model=visit.mobile_phone_model,
                operating_system=visit.operating_system,
                browser=visit.browser,
                screen_format=visit.screen_format,
                screen_orientation_name=visit.screen_orientation_name,
            )

            if not visit.watch_ids:
                hits = []
            else:
                watch_ids_list = [wid.strip() for wid in visit.watch_ids.split(',') if wid.strip()]
                if not watch_ids_list:
                    hits = []
                else:
                    stmt_hits = select(HitTable).where(HitTable.watch_id.in_(watch_ids_list))
                    result_hits = await self.session.execute(stmt_hits)
                    hit_rows = result_hits.scalars().all()
                    hits = [
                        Hit(
                            watch_id=h.watch_id,
                            client_id=h.client_id,
                            url=h.url,
                            datetime_hit=h.datetime_hit,
                            title=h.title,
                        )
                        for h in hit_rows
                    ]

            metrics.append(Metric(visit=visit_dto, hits=hits))

        return metrics
