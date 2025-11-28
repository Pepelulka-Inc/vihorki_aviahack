import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from vihorki.infrastructure.postgres.on_startup.init_tables import Base
from vihorki.infrastructure.settings import DB_URL


logger = logging.getLogger(__name__)

engine = create_async_engine(DB_URL, echo=True)
Session = async_sessionmaker(engine)


async def init_db_and_tables():
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f'Попытка {attempt + 1} не удалась. Повторная попытка через 2 секунды...')
                await asyncio.sleep(2)
            else:
                raise e
