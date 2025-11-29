import asyncio
import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from vihorki.infrastructure.postgres.on_startup.init_tables import Base
from vihorki.infrastructure.postgres.on_startup.load_csv_data import load_all_data
from vihorki.infrastructure.settings import DB_URL


logger = logging.getLogger(__name__)

engine = create_async_engine(DB_URL, echo=True)
Session = async_sessionmaker(engine)


async def init_db_and_tables():
    """
    Initialize database tables.
    If RELOAD_DATA env var is set to 'true', drops tables and reloads from CSV.
    Otherwise, just creates tables if they don't exist.
    """
    max_attempts = 5
    reload_data = os.getenv('RELOAD_DATA', 'false').lower() == 'true'
    
    for attempt in range(max_attempts):
        try:
            if reload_data:
                logger.info("RELOAD_DATA=true: Dropping tables and loading fresh data from CSV...")
                await load_all_data(engine)
                logger.info("Data reload complete")
            else:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            return
        except Exception as e:
            if attempt < max_attempts - 1:
                logger.warning(f'{DB_URL=}')
                logger.warning(f'Попытка {attempt + 1} не удалась. Повторная попытка через 2 секунды...')
                await asyncio.sleep(2)
            else:
                raise e
