import json

import pytest
from unittest.mock import AsyncMock, patch
from redis.asyncio import Redis

from vihorki.domain.entities.cached_message import CachedMetric
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache


class TestRedisConnContext:
    @pytest.mark.asyncio
    async def test_redis_conn_context_standalone(self):
        """Тест контекста подключения к standalone Redis"""
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_instance = AsyncMock()
            mock_redis_class.return_value = mock_redis_instance
            mock_redis_instance.initialize = AsyncMock()
            mock_redis_instance.close = AsyncMock()

            async with redis_conn_context(
                redis_host='localhost', redis_port=6379, redis_user=None, redis_password=None, redis_is_cluster=False
            ) as conn:
                assert conn == mock_redis_instance
                mock_redis_class.assert_called_once_with(host='localhost', port=6379, decode_responses=True)
                mock_redis_instance.initialize.assert_called_once()

            mock_redis_instance.close.assert_called_once()


class TestRedisCache:
    @pytest.fixture
    def redis_cache(self):
        """Фикстура для создания экземпляра RedisCache"""
        cache = RedisCache()
        cache.cache_client = AsyncMock(spec=Redis)
        return cache

    @pytest.mark.asyncio
    async def test_get_value_success(self, redis_cache):
        """Тест получения значения с успешной десериализацией"""
        await redis_cache.set_value('test_key', 'test_value', ex=3600)
        expected_data = {'metric': 'test_value', 'timestamp': 1234567890}
        redis_cache.cache_client.get.return_value = json.dumps(expected_data)

        result = await redis_cache.get_value('test_key')

        assert isinstance(result, CachedMetric)
        assert result.key == 'test_key'
        assert result.value == expected_data

    