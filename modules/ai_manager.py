"""
AI Manager - Intelligent Multi-Model Rotation
Handles API calls with automatic model switching on rate limits
"""

import requests
import json
import time
from modules.utils import logger


class AIManager:
    """
    Manages AI API calls with intelligent model rotation
    
    Features:
    - Rotates through multiple models
    - Auto-switches on 429 errors
    - Tracks failed models
    - Retry logic with exponential backoff
    """
    
    def __init__(self, api_key, models, base_url):
        """
        Initialize AI Manager
        
        Args:
            api_key: OpenRouter API key
            models: List of model names to rotate through
            base_url: API endpoint
        """
        self.api_key = api_key
        self.models = models
        self.base_url = base_url
        self.current_index = 0
        self.failed_models = {}  # {model: failed_time}
        self.cooldown_period = 60  # seconds before retrying failed model
        
    def _make_request(self, model, system_prompt, user_prompt, temperature):
        """Execute the HTTP POST request to the API."""
        return requests.post(
            self.base_url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': temperature
            },
            timeout=30
        )

    def _handle_response_errors(self, response, model, consecutive_failures, max_consecutive_failures):
        """
        Handle specific HTTP status codes and raise exceptions for others.
        Returns a tuple: (should_continue, should_return_none, new_consecutive_failures)
        """
        if response.status_code == 429:
            logger.warning(f"Rate limit on {model}, rotating...")
            self._mark_failed(model)
            return True, False, consecutive_failures + 1

        if response.status_code == 401:
            logger.error(f"401 Unauthorized on {model} - check API key!")
            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures:
                logger.error("Multiple consecutive 401 errors - invalid API key!")
                return False, True, consecutive_failures
            return True, False, consecutive_failures

        response.raise_for_status()
        return False, False, consecutive_failures

    def _parse_response(self, response):
        """Parse JSON response from the API, handling markdown code blocks if present."""
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()

        # Extract JSON from markdown if needed
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()

        # Parse JSON
        return json.loads(content)

    def call(self, system_prompt, user_prompt, temperature=0.3, max_retries=3):
        """
        Call AI with automatic model rotation
        
        Args:
            system_prompt: System instruction
            user_prompt: User query
            temperature: Creativity (0-1)
            max_retries: Max attempts per model
            
        Returns:
            Parsed JSON response or None
        """
        # FIXED: Prevent infinite loops - max 15 total attempts
        max_total_attempts = min(15, len(self.models) * max_retries)
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        # Try each model
        for attempt in range(max_total_attempts):
            model = self._get_next_model()
            
            if not model:
                logger.error("All models failed or on cooldown!")
                return None
            
            try:
                logger.debug(f"AI call with model: {model} (attempt {attempt + 1}/{max_total_attempts})")
                
                response = self._make_request(model, system_prompt, user_prompt, temperature)
                
                # Handle status codes and errors
                should_continue, should_return_none, consecutive_failures = self._handle_response_errors(
                    response, model, consecutive_failures, max_consecutive_failures
                )
                if should_return_none:
                    return None
                if should_continue:
                    continue
                
                data = self._parse_response(response)
                logger.debug(f"AI call successful with {model}")
                return data
                
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error on {model}: {e}")
                self._mark_failed(model)
                consecutive_failures += 1
                continue
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error on {model}: {e}")
                # Don't mark as failed, might be prompt issue
                continue
                
            except Exception as e:
                logger.error(f"Error with {model}: {e}")
                consecutive_failures += 1
                continue
        
        logger.error(f"All AI call attempts exhausted ({max_total_attempts} attempts)")
        return None
    
    def _get_next_model(self):
        """
        Get next available model (not on cooldown)
        
        Returns:
            Model name or None if all on cooldown
        """
        # Clean up old failures
        current_time = time.time()
        self.failed_models = {
            model: failed_time 
            for model, failed_time in self.failed_models.items()
            if current_time - failed_time < self.cooldown_period
        }
        
        # Try to find available model
        attempts = 0
        while attempts < len(self.models):
            model = self.models[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.models)
            
            if model not in self.failed_models:
                return model
            
            attempts += 1
        
        # All models on cooldown
        return None
    
    def _mark_failed(self, model):
        """Mark model as failed (puts on cooldown)"""
        self.failed_models[model] = time.time()
        logger.debug(f"Marked {model} as failed, cooldown for {self.cooldown_period}s")


# Global AI manager instance (initialized in config)
_ai_manager = None


def init_ai_manager(api_key, models, base_url):
    """Initialize global AI manager"""
    global _ai_manager
    _ai_manager = AIManager(api_key, models, base_url)
    logger.info(f"AI Manager initialized with {len(models)} models")


def get_ai_manager():
    """Get global AI manager instance"""
    return _ai_manager


def ai_call(system_prompt, user_prompt, temperature=0.3):
    """
    Convenience function for AI calls
    
    Uses global AI manager instance
    """
    if not _ai_manager:
        raise RuntimeError("AI Manager not initialized! Call init_ai_manager() first")
    
    return _ai_manager.call(system_prompt, user_prompt, temperature)
