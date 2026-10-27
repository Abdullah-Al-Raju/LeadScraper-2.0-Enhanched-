"""
Unit tests for OpenRouter AI Manager
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from modules.ai_manager import OpenRouterAIManager


def test_ai_manager_availability():
    # Unavailable when no key
    mgr = OpenRouterAIManager(api_key="")
    assert not mgr.is_available()

    # Available when valid key provided
    mgr_with_key = OpenRouterAIManager(api_key="sk-or-v1-testkey12345")
    assert mgr_with_key.is_available()


def test_ai_manager_clean_json_string():
    mgr = OpenRouterAIManager(api_key="sk-or-v1-test")

    raw = '```json\n{"business_name": "Tartine"}\n```'
    assert mgr._clean_json_string(raw) == '{"business_name": "Tartine"}'

    raw2 = '```\n{"business_name": "Tartine"}\n```'
    assert mgr._clean_json_string(raw2) == '{"business_name": "Tartine"}'

    plain = '{"business_name": "Tartine"}'
    assert mgr._clean_json_string(plain) == '{"business_name": "Tartine"}'


def test_ai_manager_parse_json_response():
    mgr = OpenRouterAIManager(api_key="sk-or-v1-test")

    payload = '''
    ```json
    {
        "business_name": "Blue Bottle Coffee",
        "phone_numbers": ["(510) 653-3394"],
        "email_addresses": ["support@bluebottlecoffee.com"],
        "street_address": "300 Webster St",
        "city": "Oakland",
        "state": "CA",
        "zip_code": "94607",
        "social_media": {
            "instagram": "https://instagram.com/bluebottle",
            "facebook": "https://facebook.com/bluebottle"
        }
    }
    ```
    '''
    parsed = mgr._parse_json_response(payload)
    assert parsed["business_name"] == "Blue Bottle Coffee"
    assert parsed["phone_numbers"] == ["(510) 653-3394"]
    assert parsed["email_addresses"] == ["support@bluebottlecoffee.com"]
    assert parsed["instagram"] == "https://instagram.com/bluebottle"


@pytest.mark.asyncio
async def test_ai_manager_call_ai_mocked():
    mgr = OpenRouterAIManager(api_key="sk-or-v1-test")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "choices": [{"message": {"content": "Hello from OpenRouter!"}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await mgr.call_ai("Hi")
        assert result == "Hello from OpenRouter!"
        # Verify fallback models array is passed
        assert "models" in mock_post.call_args[1]["json"]
