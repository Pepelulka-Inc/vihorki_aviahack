import json
from datetime import timedelta

import pytest
from unittest.mock import AsyncMock, patch
from redis.asyncio import Redis

from vihorki.domain.entities.cached_message import CachedMetric
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache


class TestRedisConnContext:
    @pytest.mark.asyncio
    async def test_redis_conn_context_standalone(self):
        """Тест контекста подключения к standalone Redis"""
        with patch('Redis') as mock_redis_class:
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
    async def test_set_value_with_expiry(self, redis_cache):
        """Тест установки значения с TTL"""
        await redis_cache.set_value('test_key', 'test_value', ex=3600)

        redis_cache.cache_client.set.assert_called_once_with('test_key', 'test_value', ex=3600)

    @pytest.mark.asyncio
    async def test_set_value_without_expiry(self, redis_cache):
        """Тест установки значения без TTL"""
        await redis_cache.set_value('test_key', 'test_value')

        redis_cache.cache_client.set.assert_called_once_with('test_key', 'test_value', ex=None)

    @pytest.mark.asyncio
    async def test_set_value_with_timedelta_expiry(self, redis_cache):
        """Тест установки значения с TTL в виде timedelta"""
        expiry = timedelta(minutes=10)
        await redis_cache.set_value('test_key', 'test_value', ex=expiry)

        redis_cache.cache_client.set.assert_called_once_with('test_key', 'test_value', ex=expiry)

    @pytest.mark.asyncio
    async def test_get_value_success(self, redis_cache):
        """Тест получения значения с успешной десериализацией"""
        expected_data = {'metric': 'value', 'timestamp': 1234567890}
        redis_cache.cache_client.get.return_value = json.dumps(expected_data)

        result = await redis_cache.get_value('test_key')

        redis_cache.cache_client.get.assert_called_once_with('test_key')
        assert isinstance(result, CachedMetric)
        assert result.key == 'test_key'
        assert result.value == expected_data

    @pytest.mark.asyncio
    async def test_get_value_json_decode_error(self, redis_cache, caplog):
        """Тест получения значения с ошибкой десериализации JSON"""
        invalid_json = 'invalid json string'
        redis_cache.cache_client.get.return_value = invalid_json

        with pytest.raises(json.JSONDecodeError):
            await redis_cache.get_value('test_key')

        redis_cache.cache_client.get.assert_called_once_with('test_key')

        # Проверяем, что ошибка была залогирована
        assert 'Wrong redis value:' in caplog.text
        assert invalid_json in caplog.text

    @pytest.mark.asyncio
    async def test_get_value_none_response(self, redis_cache, caplog):
        """Тест получения значения, когда Redis возвращает None"""
        redis_cache.cache_client.get.return_value = None

        with pytest.raises(json.JSONDecodeError):
            await redis_cache.get_value('test_key')

        redis_cache.cache_client.get.assert_called_once_with('test_key')

    @pytest.mark.asyncio
    async def test_get_value_empty_string(self, redis_cache, caplog):
        """Тест получения значения с пустой строкой"""
        redis_cache.cache_client.get.return_value = ''

        with pytest.raises(json.JSONDecodeError):
            await redis_cache.get_value('test_key')

        redis_cache.cache_client.get.assert_called_once_with('test_key')
        assert 'Wrong redis value:' in caplog.text


class TestRedisCacheIntegration:
    """Интеграционные тесты (требуют запущенного Redis)"""

    @pytest.mark.asyncio
    @pytest.mark.integration  # Используйте pytest -m integration для запуска
    async def test_redis_cache_full_flow(self):
        """Полный тест кэширования и получения данных"""
        cache = RedisCache()
        cache.cache_client = Redis(host='localhost', port=6379, decode_responses=True)

        try:
            test_key = 'integration_test_key'
            test_value = {'data': 'test_data', 'number': 42}
            json_value = json.dumps(test_value)

            # Установка значения
            await cache.set_value(test_key, json_value, ex=60)

            # Получение значения
            result = await cache.get_value(test_key)

            assert isinstance(result, CachedMetric)
            assert result.key == test_key
            assert result.value == test_value

        finally:
            # Очистка после теста
            await cache.cache_client.delete(test_key)
            await cache.cache_client.close()


# Дополнительные параметризованные тесты
class TestRedisCacheParameterized:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'input_value',
        [{'simple': 'value'}, [1, 2, 3], 'string_value', 42, True, None, {'nested': {'deep': {'value': 'test'}}}],
    )
    async def test_set_get_various_values(self, input_value):
        """Тест установки и получения различных типов значений"""
        cache = RedisCache()
        cache.cache_client = AsyncMock(spec=Redis)

        json_value = json.dumps(input_value)
        cache.cache_client.get.return_value = json_value

        # Тест установки
        await cache.set_value('test_key', json_value)
        cache.cache_client.set.assert_called_once_with('test_key', json_value, ex=None)

        # Тест получения
        cache.cache_client.set.reset_mock()
        result = await cache.get_value('test_key')

        assert result.key == 'test_key'
        assert result.value == input_value
