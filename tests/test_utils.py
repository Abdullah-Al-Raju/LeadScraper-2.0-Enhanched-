import pytest
import asyncio
import time
from modules.utils import retry_on_failure, rate_limit
import config

config.MAX_RETRIES = 1
config.RETRY_BACKOFF = 0.1
config.DELAY_BETWEEN_LEADS = 0.1
config.DELAY_JITTER = 0

class DummyException(Exception):
    pass

def test_sync_retry():
    calls = []

    @retry_on_failure(max_retries=1, backoff=0.1, exceptions=(DummyException,))
    def failing_func():
        calls.append(1)
        raise DummyException("Fail")

    with pytest.raises(DummyException):
        failing_func()

    assert len(calls) == 2

@pytest.mark.asyncio
async def test_async_retry():
    calls = []

    @retry_on_failure(max_retries=1, backoff=0.1, exceptions=(DummyException,))
    async def failing_func():
        calls.append(1)
        raise DummyException("Fail")

    with pytest.raises(DummyException):
        await failing_func()

    assert len(calls) == 2

def test_sync_rate_limit():
    @rate_limit(min_delay=0.1, jitter=0)
    def test_func():
        return True

    start = time.time()
    test_func()
    test_func()
    end = time.time()
    assert end - start >= 0.1

@pytest.mark.asyncio
async def test_async_rate_limit():
    @rate_limit(min_delay=0.1, jitter=0)
    async def test_func():
        return True

    start = time.time()
    await test_func()
    await test_func()
    end = time.time()
    assert end - start >= 0.1
