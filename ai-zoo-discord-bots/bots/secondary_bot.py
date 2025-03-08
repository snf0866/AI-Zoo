"""
Secondary Discord bot implementation for AI Zoo.
This can be used as a template for additional bots.
"""
import os
import logging
import asyncio
import random
import discord
from typing import Optional

from utils.config_loader import get_env, load_env_vars
from bots.base_bot import BaseDiscordBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecondaryBot(BaseDiscordBot):
    """Secondary Discord bot for AI Zoo."""
    
    def __init__(self, 
                character_name: str,
                command_prefix: str = "!",
                intents: Optional[discord.Intents] = None):
        """
        Initialize the secondary bot.
        
        Args:
            character_name: Name of the character this bot will play
            command_prefix: Command prefix for bot commands
            intents: Discord intents for the bot
        """
        super().__init__(character_name, command_prefix, intents)
        
        # Response probability (chance to respond to a message)
        # This helps prevent all bots from responding to every message
        self.response_probability = float(os.environ.get('RESPONSE_PROBABILITY', '0.7'))
    
    def should_respond_to_message(self, message) -> bool:
        """
        Determine if the bot should respond to a message based on probability.
        
        Args:
            message: Discord message to check
            
        Returns:
            True if the bot should respond, False otherwise
        """
        # Randomly decide whether to respond based on probability
        if random.random() > self.response_probability:
            logger.debug("Randomly decided not to respond")
            return False
        return True
    
    def get_additional_introduction_info(self) -> str:
        """
        Add response probability information to the introduction message.
        
        Returns:
            Response probability information
        """
        return f"応答確率: {int(self.response_probability * 100)}%"


async def main():
    """Main entry point for the bot."""
    # Load environment variables
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
    load_env_vars(env_path)
    
    # Get bot token and name from environment
    token = get_env('DISCORD_TOKEN_BOT2')
    bot_name = os.environ.get('BOT_NAME', 'claude-animal')  # デフォルト値としてclaude-animalを使用
    
    # Create and start the bot
    bot = SecondaryBot(character_name=bot_name)
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
