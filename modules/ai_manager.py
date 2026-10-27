"""
OpenRouter AI Manager for LeadScraper 2.0 Enhanced
Provides zero-cost AI extraction and discovery utilizing OpenRouter's free auto-router (`openrouter/free`)
and server-side multi-model fallbacks.
"""

import json
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
import config

logger = logging.getLogger(__name__)


class OpenRouterAIManager:
    """
    Manages optional OpenRouter AI integration with automatic free-model routing and fallbacks.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or getattr(config, 'OPENROUTER_API_KEY', '') or '').strip()
        self.base_url = getattr(config, 'OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1').rstrip('/')
        self.model = model or getattr(config, 'OPENROUTER_MODEL', 'openrouter/free')
        self.fallback_models = getattr(
            config,
            'OPENROUTER_FALLBACK_MODELS',
            [
                'openrouter/free',
                'meta-llama/llama-3.3-70b-instruct:free',
                'google/gemini-2.0-flash-exp:free',
                'qwen/qwen-2.5-72b-instruct:free',
                'mistralai/mistral-7b-instruct:free',
            ]
        )
        self.timeout = getattr(config, 'AI_REQUEST_TIMEOUT', 15)

    def is_available(self) -> bool:
        """Returns True if an OpenRouter API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/Abdullah-Al-Raju/LeadScraper-2.0-Enhanched-",
            "X-Title": "LeadScraper 2.0 Enhanced",
            "Content-Type": "application/json",
        }

    async def call_ai(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Calls OpenRouter API using the free auto-router and multi-model fallback array.
        """
        if not self.is_available():
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "models": self.fallback_models,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200,
        }

        url = f"{self.base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=self._get_headers(), json=payload)

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        model_used = data.get("model", self.model)
                        logger.info(f"OpenRouter response received [model: {model_used}]")
                        return choices[0]["message"].get("content", "").strip()
                elif response.status_code == 401:
                    logger.warning("OpenRouter API key is invalid or unauthorized.")
                elif response.status_code == 429:
                    logger.warning("OpenRouter free tier rate limit reached. Proceeding with deterministic fallback.")
                else:
                    logger.warning(f"OpenRouter API returned status {response.status_code}: {response.text[:200]}")

        except httpx.TimeoutException:
            logger.warning(f"OpenRouter request timed out after {self.timeout}s.")
        except Exception as e:
            logger.warning(f"OpenRouter call failed: {e}")

        return None

    def call_ai_sync(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Synchronous wrapper for call_ai."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Run in executor to avoid nested event loop conflicts
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(asyncio.run, self.call_ai(prompt, system_prompt)).result()
            return loop.run_until_complete(self.call_ai(prompt, system_prompt))
        except Exception as e:
            logger.debug(f"Sync OpenRouter call error: {e}")
            return None

    async def extract_contacts_with_ai(self, text: str, category: str = "") -> Dict[str, Any]:
        """
        Uses OpenRouter free models to extract contact details from unstructured webpage text.
        """
        if not self.is_available() or not text:
            return {}

        # Limit text length to preserve token budget
        truncated_text = text[:4000]

        system_prompt = (
            "You are a high-precision business contact extraction engine. "
            "Extract business contact details from the given text and return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "business_name": "string or null",\n'
            '  "phone_numbers": ["string"],\n'
            '  "email_addresses": ["string"],\n'
            '  "street_address": "string or null",\n'
            '  "city": "string or null",\n'
            '  "state": "string or null",\n'
            '  "zip_code": "string or null",\n'
            '  "social_media": {\n'
            '    "instagram": "url or null",\n'
            '    "facebook": "url or null",\n'
            '    "twitter": "url or null",\n'
            '    "linkedin": "url or null"\n'
            "  }\n"
            "}\n"
            "Do not include explanation, greetings, or markdown code blocks. Output JSON only."
        )

        prompt = f"Category: {category or 'Business'}\n\nWebpage Text:\n{truncated_text}"

        response_text = await self.call_ai(prompt, system_prompt)
        if not response_text:
            return {}

        return self._parse_json_response(response_text)

    def extract_contacts_with_ai_sync(self, text: str, category: str = "") -> Dict[str, Any]:
        """Synchronous contact extraction."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(asyncio.run, self.extract_contacts_with_ai(text, category)).result()
            return loop.run_until_complete(self.extract_contacts_with_ai(text, category))
        except Exception:
            return {}

    async def discover_businesses_with_ai(self, location: str, category: str, quantity: int = 10) -> List[Dict[str, str]]:
        """
        Asks OpenRouter free models to suggest real operating businesses in a target location.
        """
        if not self.is_available():
            return []

        system_prompt = (
            "You are a local business research assistant. "
            "List real, currently operating businesses in the requested location and category. "
            "Return ONLY a JSON array of objects with 'business_name' and 'city'. Example:\n"
            '[{"business_name": "Tartine Bakery", "city": "San Francisco"}]\n'
            "Output JSON only, no markdown formatting."
        )

        prompt = f"Find {quantity} popular, real {category} businesses located in or around {location}."

        response_text = await self.call_ai(prompt, system_prompt)
        if not response_text:
            return []

        try:
            cleaned = self._clean_json_string(response_text)
            data = json.loads(cleaned)
            if isinstance(data, list):
                results = []
                for item in data:
                    if isinstance(item, dict) and item.get("business_name"):
                        results.append({
                            "business_name": item["business_name"].strip(),
                            "city": item.get("city", location).strip()
                        })
                return results
        except Exception as e:
            logger.debug(f"Failed to parse AI discovery JSON: {e}")

        return []

    def discover_businesses_with_ai_sync(self, location: str, category: str, quantity: int = 10) -> List[Dict[str, str]]:
        """Synchronous business discovery."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(asyncio.run, self.discover_businesses_with_ai(location, category, quantity)).result()
            return loop.run_until_complete(self.discover_businesses_with_ai(location, category, quantity))
        except Exception:
            return []

    def _clean_json_string(self, text: str) -> str:
        """Strips markdown code blocks and surrounding whitespace."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Safely parses JSON contact dictionary."""
        try:
            cleaned = self._clean_json_string(text)
            data = json.loads(cleaned)
            if isinstance(data, dict):
                # Normalize structure
                return {
                    "business_name": data.get("business_name"),
                    "phone_numbers": [str(p) for p in data.get("phone_numbers", []) if p],
                    "email_addresses": [str(e) for e in data.get("email_addresses", []) if e],
                    "street_address": data.get("street_address"),
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "zip_code": data.get("zip_code"),
                    "facebook": (data.get("social_media") or {}).get("facebook"),
                    "instagram": (data.get("social_media") or {}).get("instagram"),
                    "twitter": (data.get("social_media") or {}).get("twitter"),
                    "linkedin": (data.get("social_media") or {}).get("linkedin"),
                }
        except Exception as e:
            logger.debug(f"JSON parsing error from AI response: {e}")
        return {}


# Global singleton instance
ai_manager = OpenRouterAIManager()


def get_ai_manager() -> OpenRouterAIManager:
    """Returns the global OpenRouter AI manager instance."""
    return ai_manager
