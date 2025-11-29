from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from vihorki.domain.entities.metric import Metric


class IMetricRepository(ABC):
    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def get_by_timedelta(self, time_start: datetime, time_end: datetime) -> list[Metric]: ...

    @abstractmethod
    async def get_by_new_users(self, is_new_user: int) -> list[Metric]:
        """1 - новый юзер, 0 - если нет"""

    @abstractmethod
    async def get_by_region(self, region_country: str, region_city: str) -> list[Metric]: ...

    @abstractmethod
    async def get_by_device(self, device: str, operating_system: str, is_landscape: str = None) -> list[Metric]:
        """device 1 - komp, device 2 - mobila, если мобила и лендскейп - считаем планшетом"""
        ...
