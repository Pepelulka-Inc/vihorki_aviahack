import pytest
from aiohttp import web
from unittest.mock import patch, AsyncMock
import json

from vihorki.main import app, healthcheck, on_startup


async def test_healthcheck_returns_correct_data():
    client = app
    resp = await client.get('/health')
    
    assert resp.status == 200
    data = await resp.json()
    
    assert "status" in data
    assert "timestamp" in data
    assert "service" in data
    assert data["status"] == "healthy"
    assert data["service"] == "vihorki"
    assert isinstance(data["timestamp"], (int, float))


async def test_on_startup_initializes_db():
    with patch('vihorki.infrastructure.postgres.on_startup.run_db.init_db_and_tables', new=AsyncMock()) as mock_init:
        mock_app = AsyncMock()
        await on_startup(mock_app)
        
        mock_init.assert_called_once()


async def test_healthcheck_response_format():
    request = None
    response = await healthcheck()
    
    assert isinstance(response, web.Response)
    assert response.status == 200
    
    data = json.loads(response.body.decode())
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "vihorki"