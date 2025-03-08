"""
Service for interacting with Language Model APIs (OpenAI, Anthropic, etc.)
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Union
import aiohttp
import asyncio

from utils.config_loader import get_env

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with various LLM APIs."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.max_token_limit = int(os.environ.get('MAX_TOKEN_LIMIT', '500'))
        
    async def generate_response(self, 
                               messages: Union[List[Dict[str, str]], str],
                               model: str = "gpt-4",
                               max_tokens: Optional[int] = None) -> str:
        """
        Generate a response from an LLM based on the provided messages.
        
        Args:
            messages: Either a list of messages for OpenAI format or a string for Anthropic format
            model: Model to use for generation
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated response text
            
        Raises:
            ValueError: If the model is not supported or API keys are missing
            Exception: If the API request fails
        """
        if max_tokens is None:
            max_tokens = self.max_token_limit
            
        if model.startswith("gpt"):
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required for GPT models")
            return await self._generate_openai_response(messages, model, max_tokens)
        elif model.startswith("claude"):
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required for Claude models")
            return await self._generate_anthropic_response(messages, model, max_tokens)
        else:
            raise ValueError(f"Unsupported model: {model}")
            
    async def _generate_openai_response(self, 
                                      messages: List[Dict[str, str]],
                                      model: str,
                                      max_tokens: int) -> str:
        """
        Generate a response using OpenAI API.
        
        Args:
            messages: List of messages in OpenAI format
            model: OpenAI model to use
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated response text
        """
        logger.info(f"Generating response with OpenAI model: {model}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 1.0
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error: {error_text}")
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
                
    async def _generate_anthropic_response(self, 
                                         prompt: str,
                                         model: str,
                                         max_tokens: int) -> str:
        """
        Generate a response using Anthropic Claude API.
        
        Args:
            prompt: Prompt string in Anthropic format
            model: Anthropic model to use
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated response text
        """
        logger.info(f"Generating response with Anthropic model: {model}")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # Use Messages API for Claude 3 models, otherwise use Complete API
        if model.startswith("claude-3"):
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            api_endpoint = "https://api.anthropic.com/v1/messages"
        else:
            # Format prompt for Complete API
            formatted_prompt = f"\n\nHuman: {prompt}\n\nAssistant:"
            payload = {
                "model": model,
                "prompt": formatted_prompt,
                "max_tokens_to_sample": max_tokens,
                "temperature": 0.7,
                "top_p": 1.0
            }
            api_endpoint = "https://api.anthropic.com/v1/complete"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_endpoint,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Anthropic API error: {error_text}")
                    raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                
                result = await response.json()
                # Handle different response formats between APIs
                if model.startswith("claude-3"):
                    return result["content"][0]["text"]
                else:
                    return result["completion"]
