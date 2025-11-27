# import logging
# import asyncio

# import pytest
# from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
# from sqlalchemy.orm import declarative_base

from vihorki.infrastructure.settings import DB_URL, DB_HOST, DB_PASSWORD, DB_PORT


def test_get_pwd():
    assert DB_PASSWORD is not None


def test_get_host():
    assert DB_HOST is not None


def test_get_port():
    assert DB_PORT is not None


def test_get_url():
    assert DB_URL is not None


# logger = logging.getLogger(__name__)
# Base = declarative_base()
# engine = create_async_engine(DB_URL, echo=True)
# Session = async_sessionmaker(engine)


# @pytest.fixture(scope='session')
# async def db_sessionmaker():
#     """Возвращает фабрику сессий для тестов."""
#     return Session


# async def setup_database(db_engine: AsyncEngine):
#     """Инициализирует базу данных перед каждым тестом."""
#     max_attempts = 5
#     for attempt in range(max_attempts):
#         try:
#             async with db_engine.begin() as conn:
#                 yield conn
#             break
#         except Exception as e:
#             if attempt < max_attempts - 1:
#                 logger.warning(f'Попытка {attempt + 1} не удалась. Повторная попытка через 2 секунды...')
#                 await asyncio.sleep(2)
#             else:
#                 raise e


# def test_setup():
#     assert setup_database(engine) is not None
