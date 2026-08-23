import pytest
from modules.http_client import AsyncHTTPClient

@pytest.mark.asyncio
async def test_async_http_client_initialization():
    client = AsyncHTTPClient(timeout=10.0, max_connections=5)
    assert client.timeout == 10.0
    assert client.limits.max_connections == 5
