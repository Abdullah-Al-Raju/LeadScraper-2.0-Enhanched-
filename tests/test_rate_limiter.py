import pytest
import asyncio
import time
from unittest.mock import patch, call
from collections import defaultdict

from modules.rate_limiter import RateLimiter


@pytest.fixture
def rate_limiter():
    """Provides a fresh instance of RateLimiter for each test."""
    return RateLimiter()


def test_rate_limiter_initialization(rate_limiter):
    """Test that RateLimiter initializes with the correct state."""
    # Check calls is correctly initialized as defaultdict of list
    assert isinstance(rate_limiter.calls, defaultdict)
    assert rate_limiter.calls.default_factory is list

    # Check that limits are correctly initialized
    expected_limits = {
        'facebook': (10, 60),
        'instagram': (10, 60),
        'google': (20, 60),
        'openrouter': (60, 60),
        'website': (30, 60),
        'default': (15, 60)
    }
    assert rate_limiter.limits == expected_limits


def test_rate_limiter_get_status_initial(rate_limiter):
    """Test get_status on initial setup for a specific service."""
    status = rate_limiter.get_status('google')

    assert status == {
        'service': 'google',
        'current_calls': 0,
        'max_calls': 20,
        'window_seconds': 60,
        'remaining': 20
    }

    # Test for an unknown service (fallback to 'default')
    status_default = rate_limiter.get_status('unknown_service')
    assert status_default == {
        'service': 'unknown_service',
        'current_calls': 0,
        'max_calls': 15,
        'window_seconds': 60,
        'remaining': 15
    }


@pytest.mark.asyncio
async def test_rate_limiter_acquire_below_limit(rate_limiter):
    """Test acquire when under the rate limit (should not block)."""
    with patch('asyncio.sleep') as mock_sleep:
        # Service 'facebook' has limit of 10 calls.
        # Make 9 calls, we should not sleep
        for _ in range(9):
            await rate_limiter.acquire('facebook')

        mock_sleep.assert_not_called()

        status = rate_limiter.get_status('facebook')
        assert status['current_calls'] == 9
        assert status['remaining'] == 1


@pytest.mark.asyncio
async def test_rate_limiter_acquire_exceeds_limit(rate_limiter):
    """Test acquire when reaching the rate limit (should block)."""
    with patch('asyncio.sleep') as mock_sleep, patch('time.time') as mock_time:
        # We need a stable time to assert sleep calculation
        current_time = 1000.0
        mock_time.return_value = current_time

        # Service 'facebook' has a limit of 10 calls per 60 seconds
        for _ in range(10):
            await rate_limiter.acquire('facebook')

        # 10 calls made, should not have slept yet
        mock_sleep.assert_not_called()

        # The 11th call should exceed the limit
        # Oldest call was at t=1000.0. Current time is still 1000.0
        # Wait time should be 60 - (1000.0 - 1000.0) = 60.0
        await rate_limiter.acquire('facebook')

        mock_sleep.assert_called_once_with(60.0)


@pytest.mark.asyncio
async def test_rate_limiter_window_cleanup(rate_limiter):
    """Test that calls older than the window are cleaned up."""
    with patch('time.time') as mock_time:
        # Start at 1000.0
        mock_time.return_value = 1000.0

        # Make 5 calls
        for _ in range(5):
            await rate_limiter.acquire('facebook')

        # Fast forward time to beyond the 60s window
        mock_time.return_value = 1061.0

        # Checking status should trigger cleanup logic (get_status checks recent calls)
        status = rate_limiter.get_status('facebook')

        # Assert that old calls were ignored
        assert status['current_calls'] == 0
        assert status['remaining'] == 10

        # The acquire method also does cleanup
        # This acquire will record a new call at 1061.0
        await rate_limiter.acquire('facebook')

        assert len(rate_limiter.calls['facebook']) == 1
