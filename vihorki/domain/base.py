from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from vihorki.domain.repositories.metric_repo import IMetricRepository


class BaseUseCase(ABC):
    @abstractmethod
    async def __call__(self, *args):
        result = await self.execute(*args)
        return result


class IUnitOfWork(ABC):
    session: AsyncSession
    metric_repo: 'IMetricRepository'

    @abstractmethod
    async def __aenter__(self):
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args):
        raise NotImplementedError

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError
