import logging
import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine

from vihorki.infrastructure.settings import DB_URL


logger = logging.getLogger(__name__)
engine = create_async_engine(DB_URL, echo=True)
Session = async_sessionmaker(engine)


@pytest.fixture(scope='session')
async def db_sessionmaker():
    return Session


async def setup_database(db_engine: AsyncEngine):
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            async with db_engine.begin() as conn:
                yield conn
            break
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f'Попытка {attempt + 1} не удалась. Повторная попытка через 2 секунды...')
                await asyncio.sleep(2)
            else:
                raise e


def test_setup():
    assert setup_database(engine) is not None
