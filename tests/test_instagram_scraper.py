import pytest
from modules.sources.instagram_scraper import extract_instagram_data
from modules.http_client import get_http_client
import respx
import httpx

mock_html = """
<html>
    <head>
        <title>Business Name (@username) • Instagram</title>
        <meta property="og:title" content="Business Name" />
        <meta property="og:description" content="Welcome to our business! Call us at (555) 123-4567 or email at contact@business.com. 📍 New York, NY 10001" />
    </head>
    <body>
        <a href="https://www.business.com">Visit our website</a>
    </body>
</html>
"""

@pytest.mark.asyncio
async def test_extract_instagram_data_placeholder():
    client = await get_http_client()

    with respx.mock:
        async def mock_callback(request):
            return httpx.Response(200, text=mock_html)

        respx.get("https://www.instagram.com/business/").mock(side_effect=mock_callback)

        async with client:
            result = await extract_instagram_data("https://www.instagram.com/business/")
            assert result is not None
            assert result["business_name"] == "Business Name"
            assert "(555) 123-4567" in result["phone_numbers"]
            assert "contact@business.com" in result["email_addresses"]
