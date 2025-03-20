"""
Service for interacting with Language Model APIs (OpenAI, Anthropic, etc.)
"""
import os
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union
import aiohttp
import asyncio

from utils.config_loader import get_env
from services.database import AsyncSessionLocal, log_llm_request

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
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing LLMService")
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.max_token_limit = int(os.environ.get('MAX_TOKEN_LIMIT', '500'))
        
        # OpenAI APIキーの確認
        if not os.environ.get("OPENAI_API_KEY"):
            self.logger.error("OPENAI_API_KEY is not set in environment variables")
        else:
            self.logger.info("OPENAI_API_KEY is properly set")
        
        # Anthropic APIキーの確認
        if not os.environ.get("ANTHROPIC_API_KEY"):
            self.logger.error("ANTHROPIC_API_KEY is not set in environment variables")
        else:
            self.logger.info("ANTHROPIC_API_KEY is properly set")
        
    async def generate_response(self, 
                               messages: Union[List[Dict[str, str]], str],
                               model: str = "gpt-4",
                               max_tokens: Optional[int] = None,
                               bot_name: Optional[str] = None,
                               skip_logging: bool = False,
                               n: int = 1) -> Union[str, List[str]]:
        """
        Generate a response from an LLM based on the provided messages.
        
        Args:
            messages: Either a list of messages for OpenAI format or a string for Anthropic format
            model: Model to use for generation
            max_tokens: Maximum number of tokens to generate
            bot_name: Name of the bot making the request (for logging)
            skip_logging: Whether to skip logging the request to the database
            n: Number of response candidates to generate (only supported by OpenAI models)
            
        Returns:
            Generated response text or a list of response texts if n > 1
            
        Raises:
            ValueError: If the model is not supported or API keys are missing
            Exception: If the API request fails
        """
        self.logger.info(f"Generating response using model: {model} for bot: {bot_name} with n={n}")
        self.logger.info(f"Skip logging: {skip_logging}")
        
        start_time = time.time()
        response = None
        error = None
        
        if max_tokens is None:
            max_tokens = self.max_token_limit
            
        try:
            if model.startswith("gpt"):
                if not self.openai_api_key:
                    raise ValueError("OpenAI API key is required for GPT models")
                self.logger.info("Using OpenAI API")
                response = await self._generate_openai_response(messages, model, max_tokens, n)
            elif model.startswith("claude"):
                if not self.anthropic_api_key:
                    raise ValueError("Anthropic API key is required for Claude models")
                self.logger.info("Using Anthropic API")
                # Anthropicは現在複数候補生成に対応していないため、nパラメータは無視されます
                if n > 1:
                    self.logger.warning("Multiple response generation (n > 1) is not supported by Anthropic API, ignoring n parameter")
                response = await self._generate_anthropic_response(messages, model, max_tokens)
            else:
                error_msg = f"Unsupported model: {model}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            llm_time = time.time() - start_time
            
            # Start measuring post-processing time
            post_start_time = time.time()
            
            # Here you can add any post-processing of the response if needed
            
            post_process_time = time.time() - post_start_time
            total_time = time.time() - start_time
            
            self.logger.info(f"Response generation timing for {model}:")
            self.logger.info(f"  - LLM Response Time: {llm_time:.2f} seconds")
            self.logger.info(f"  - Post-processing Time: {post_process_time:.2f} seconds")
            self.logger.info(f"  - Total Time: {total_time:.2f} seconds")
            
        except Exception as e:
            error = str(e)
            error_time = time.time() - start_time
            self.logger.error(f"Error generating response after {error_time:.2f} seconds: {e}", exc_info=True)
            raise
        finally:
            # Log request to database if bot_name is provided and logging is not skipped
            if bot_name and not skip_logging:
                total_time = time.time() - start_time
                try:
                    async with AsyncSessionLocal() as session:
                        # 複数応答の場合は最初の応答をログに記録
                        log_response = response[0] if isinstance(response, list) else response
                        await log_llm_request(
                            session=session,
                            model=model,
                            messages=messages if isinstance(messages, list) else {"prompt": messages},
                            response=log_response if log_response else "",
                            response_time=llm_time if response else total_time,
                            total_time=total_time,
                            bot_name=bot_name,
                            error=error
                        )
                    self.logger.info("Successfully logged request to database")
                except Exception as e:
                    self.logger.error(f"Failed to log request to database: {e}", exc_info=True)
            
            if response:
                return response
            
    async def _generate_openai_response(self, 
                                      messages: List[Dict[str, str]],
                                      model: str,
                                      max_tokens: int,
                                      n: int = 1) -> Union[str, List[str]]:
        """
        Generate a response using OpenAI API.
        
        Args:
            messages: List of messages in OpenAI format
            model: OpenAI model to use
            max_tokens: Maximum number of tokens to generate
            n: Number of response candidates to generate
            
        Returns:
            Generated response text or list of response texts if n > 1
        """
        self.logger.info(f"Generating {n} response(s) with OpenAI model: {model}")
        start_time = time.time()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 1.0,
            "n": n
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"OpenAI API error: {error_text}")
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                
                result = await response.json()
                api_time = time.time() - start_time
                self.logger.info(f"OpenAI API request completed in {api_time:.2f} seconds")
                
                # n=1の場合は単一の文字列、n>1の場合はリストを返す
                if n == 1:
                    return result["choices"][0]["message"]["content"]
                else:
                    # 複数の応答候補を返す
                    responses = [choice["message"]["content"] for choice in result["choices"]]
                    self.logger.info(f"Generated {len(responses)} response candidates")
                    return responses
                
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
        self.logger.info(f"Generating response with Anthropic model: {model}")
        start_time = time.time()
        
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
                    self.logger.error(f"Anthropic API error: {error_text}")
                    raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                
                result = await response.json()
                api_time = time.time() - start_time
                self.logger.info(f"Anthropic API request completed in {api_time:.2f} seconds")
                
                # Handle different response formats between APIs
                if model.startswith("claude-3"):
                    return result["content"][0]["text"]
                else:
                    return result["completion"]
