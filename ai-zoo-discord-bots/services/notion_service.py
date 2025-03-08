"""
Service for interacting with Notion API to retrieve character settings.
"""
import os
import logging
import json
import time
from typing import Dict, Any, List, Optional
import aiohttp
import asyncio

from utils.config_loader import get_env, load_json_config, get_config_path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NotionService:
    """Service for interacting with Notion API."""
    
    def __init__(self):
        """Initialize the Notion service."""
        self.api_key = os.environ.get('NOTION_API_KEY')
        self.database_id = os.environ.get('NOTION_DATABASE_ID')
        
        # Load Notion configuration
        try:
            self.config = load_json_config(str(get_config_path('notion_config.json')))
            logger.info("Loaded Notion configuration")
        except Exception as e:
            logger.error(f"Failed to load Notion configuration: {e}")
            self.config = {
                "database_id": self.database_id,
                "character_properties": {
                    "name": "Name",
                    "personality": "Personality",
                    "speaking_style": "Speaking Style",
                    "language": "Language",
                    "restrictions": "Restrictions",
                    "background": "Background",
                    "interests": "Interests",
                    "model": "Model"
                },
                "refresh_interval_minutes": 60,
                "cache_expiry_hours": 24
            }
            
        # Use database_id from config if not set in environment
        if not self.database_id and "database_id" in self.config:
            self.database_id = self.config["database_id"]
            
        # Character cache
        self.character_cache: Dict[str, Dict[str, Any]] = {}
        self.last_refresh_time = 0
        
    async def get_character(self, character_name: str) -> Optional[Dict[str, Any]]:
        """
        Get character settings from Notion.
        
        Args:
            character_name: Name of the character to retrieve
            
        Returns:
            Character settings or None if not found
        """
        logger.info(f"Getting character settings for: '{character_name}'")
        
        # Check if we need to refresh the cache
        current_time = time.time()
        refresh_interval = self.config.get("refresh_interval_minutes", 60) * 60  # Convert to seconds
        
        time_since_refresh = current_time - self.last_refresh_time
        logger.debug(f"Time since last cache refresh: {time_since_refresh:.2f} seconds (interval: {refresh_interval} seconds)")
        
        if time_since_refresh > refresh_interval:
            logger.info(f"Cache expired (last refresh was {time_since_refresh:.2f} seconds ago). Refreshing character cache.")
            await self.refresh_character_cache()
        else:
            logger.debug("Using existing character cache")
        
        # Look up the character in the cache
        character_key = character_name.lower()
        character = self.character_cache.get(character_key)
        
        if character:
            logger.info(f"Character '{character_name}' found in cache with properties: {list(character.keys())}")
            return character
        else:
            # Try with transformed name (remove spaces)
            transformed_key = character_key.replace(' ', '')
            character = self.character_cache.get(transformed_key)
            
            if character:
                logger.info(f"Character '{character_name}' found in cache using transformed key '{transformed_key}'")
                return character
            else:
                logger.warning(f"Character '{character_name}' not found in cache. Available characters: {list(self.character_cache.keys())}")
                return None
    
    async def refresh_character_cache(self) -> None:
        """Refresh the character cache from Notion."""
        logger.info("Refreshing character cache from Notion")
        
        if not self.api_key:
            logger.error("Notion API key is not set")
            return
            
        if not self.database_id:
            logger.error("Notion database ID is not set")
            return
            
        try:
            characters = await self._query_notion_database()
            logger.info(f"Retrieved {len(characters)} characters from Notion database")
            
            # Update cache
            old_cache_keys = set(self.character_cache.keys())
            new_cache = {}
            
            for character in characters:
                if "name" in character:
                    char_name = character["name"]
                    # Store with both original (lowercase) and transformed (no spaces) keys
                    key = char_name.lower()
                    transformed_key = key.replace(' ', '')
                    
                    new_cache[key] = character
                    if key != transformed_key:
                        new_cache[transformed_key] = character
                        logger.debug(f"Character '{char_name}' stored with keys: '{key}' and '{transformed_key}'")
                    else:
                        logger.debug(f"Character '{char_name}' stored with key: '{key}'")
            
            self.character_cache = new_cache
            self.last_refresh_time = time.time()
            
            # Log cache changes
            new_cache_keys = set(self.character_cache.keys())
            added_keys = new_cache_keys - old_cache_keys
            removed_keys = old_cache_keys - new_cache_keys
            
            if added_keys:
                logger.info(f"Added characters to cache: {added_keys}")
            if removed_keys:
                logger.info(f"Removed characters from cache: {removed_keys}")
                
            logger.info(f"Character cache refreshed with {len(characters)} characters. Total cache entries: {len(self.character_cache)}")
        except Exception as e:
            logger.error(f"Failed to refresh character cache: {e}", exc_info=True)
    
    async def _query_notion_database(self) -> List[Dict[str, Any]]:
        """
        Query the Notion database for character settings.
        
        Returns:
            List of character settings
        """
        logger.info(f"Querying Notion database: {self.database_id}")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        
        async with aiohttp.ClientSession() as session:
            logger.debug(f"Sending request to Notion API: {url}")
            start_time = time.time()
            
            async with session.post(url, headers=headers, json={}) as response:
                response_time = time.time() - start_time
                logger.debug(f"Notion API response received in {response_time:.2f} seconds with status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Notion API error: {error_text}")
                    raise Exception(f"Notion API error: {response.status} - {error_text}")
                
                result = await response.json()
                logger.debug(f"Retrieved {len(result.get('results', []))} pages from Notion database")
                
                # Parse results
                characters = []
                for page in result.get("results", []):
                    character = self._parse_notion_page(page)
                    if character:
                        characters.append(character)
                        logger.debug(f"Successfully parsed character: {character.get('name', 'Unknown')}")
                    else:
                        logger.warning("Failed to parse a Notion page into character settings")
                
                logger.info(f"Successfully parsed {len(characters)} characters from Notion database")
                return characters
    
    def _parse_notion_page(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a Notion page into character settings.
        
        Args:
            page: Notion page object
            
        Returns:
            Character settings or None if parsing fails
        """
        try:
            properties = page.get("properties", {})
            character = {}
            
            # Map Notion properties to character settings
            property_mapping = self.config.get("character_properties", {})
            
            for char_prop, notion_prop in property_mapping.items():
                if notion_prop in properties:
                    prop_value = self._extract_property_value(properties[notion_prop])
                    if prop_value is not None:
                        character[char_prop] = prop_value
                        logger.debug(f"Extracted property '{char_prop}' with value: {prop_value}")
                    else:
                        logger.debug(f"Property '{char_prop}' extraction returned None")
                else:
                    logger.debug(f"Property '{notion_prop}' not found in Notion page properties")
            
            if "name" in character:
                return character
            else:
                logger.warning("Parsed character object is missing required 'name' property")
                return None
        except Exception as e:
            logger.error(f"Failed to parse Notion page: {e}", exc_info=True)
            return None
    
    def _extract_property_value(self, property_obj: Dict[str, Any]) -> Optional[Any]:
        """
        Extract value from a Notion property object.
        
        Args:
            property_obj: Notion property object
            
        Returns:
            Extracted value or None if extraction fails
        """
        try:
            prop_type = property_obj.get("type")
            
            if prop_type == "title":
                title_objects = property_obj.get("title", [])
                if title_objects:
                    return title_objects[0].get("plain_text", "")
                else:
                    logger.debug("Empty title property")
            elif prop_type == "rich_text":
                text_objects = property_obj.get("rich_text", [])
                if text_objects:
                    return text_objects[0].get("plain_text", "")
                else:
                    logger.debug("Empty rich_text property")
            elif prop_type == "select":
                select_obj = property_obj.get("select")
                if select_obj:
                    return select_obj.get("name")
                else:
                    logger.debug("Empty select property")
            elif prop_type == "multi_select":
                multi_select = property_obj.get("multi_select", [])
                return [item.get("name") for item in multi_select if "name" in item]
            elif prop_type == "checkbox":
                return property_obj.get("checkbox")
            elif prop_type == "number":
                return property_obj.get("number")
            else:
                logger.debug(f"Unsupported property type: {prop_type}")
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract property value: {e}", exc_info=True)
            return None
    
    def format_character_prompt(self, character: Dict[str, Any]) -> str:
        """
        Format character settings into a system prompt for LLM.
        
        Args:
            character: Character settings
            
        Returns:
            Formatted system prompt
        """
        prompt_parts = []
        
        # Add character name
        if "name" in character:
            prompt_parts.append(f"You are {character['name']}.")
        
        # Add personality
        if "personality" in character:
            prompt_parts.append(f"Personality: {character['personality']}")
        
        # Add speaking style
        if "speaking_style" in character:
            prompt_parts.append(f"Speaking style: {character['speaking_style']}")
        
        # Add language preference
        if "language" in character:
            prompt_parts.append(f"You primarily communicate in {character['language']}.")
        
        # Add background
        if "background" in character:
            prompt_parts.append(f"Background: {character['background']}")
        
        # Add interests
        if "interests" in character:
            interests = character["interests"]
            if isinstance(interests, list):
                interests_str = ", ".join(interests)
            else:
                interests_str = interests
            prompt_parts.append(f"Your interests include: {interests_str}")
        
        # Add restrictions
        if "restrictions" in character:
            prompt_parts.append(f"Restrictions: {character['restrictions']}")
        
        # Add general instructions
        prompt_parts.append(
            "You are participating in a Discord chat with other AI bots and possibly humans. "
            "Keep your responses concise and engaging. Respond naturally to the conversation "
            "flow and stay in character at all times."
        )
        
        return "\n\n".join(prompt_parts)
