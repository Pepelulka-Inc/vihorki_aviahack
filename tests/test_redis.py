import orjson
import pytest
from unittest.mock import AsyncMock, patch

from vihorki.infrastructure.redis.redis_tools import Redis
from vihorki.domain.entities.cached_message import CachedMetric
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache


@pytest.mark.asyncio
async def test_redis_cache_client():
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.close = AsyncMock()
    test_key = 'test_key'
    test_value = { "test": "value" }
    test_value_bytes = orjson.dumps(test_value)
    test_expiration = 60

    mock_redis.set = AsyncMock()
    mock_redis.get = AsyncMock(return_value=test_value_bytes)

    with patch("vihorki.infrastructure.redis.redis_tools.Redis", return_value=mock_redis):
        async with redis_conn_context(redis_host="localhost", port=6379) as redis:
            client = RedisCache(redis)

            await client.set_value(test_key, test_value_bytes, ex=test_expiration)
            mock_redis.set.assert_awaited_once_with(test_key, test_value_bytes, ex=test_expiration)

            result = await client.get_value(test_key)
            assert result is not None
            assert result.key == test_key
            assert result.value == test_value
            mock_redis.get.assert_awaited_once_with(test_key)

            mock_redis.get.return_value = b'invalid_json'
            with pytest.raises(orjson.JSONDecodeError):
                await client.get_value(test_key)
        
        mock_redis.close.assert_awaited_once()