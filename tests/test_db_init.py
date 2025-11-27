import logging
import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base

from vihorki.infrastructure.settings import DB_URL


logger = logging.getLogger(__name__)
Base = declarative_base()
engine = create_async_engine(DB_URL, echo=True)
Session = async_sessionmaker(engine)


@pytest.fixture(scope='session')
async def db_engine():
    """Создает асинхронный движок для тестов."""
    yield engine
    await engine.dispose()


@pytest.fixture(scope='session')
async def db_sessionmaker():
    """Возвращает фабрику сессий для тестов."""
    return Session


@pytest.fixture(scope='function', autouse=True)
async def setup_database(db_engine: AsyncEngine):
    """Инициализирует базу данных перед каждым тестом."""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            async with db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f'Попытка {attempt + 1} не удалась. Повторная попытка через 2 секунды...')
                await asyncio.sleep(2)
            else:
                raise e

    yield
