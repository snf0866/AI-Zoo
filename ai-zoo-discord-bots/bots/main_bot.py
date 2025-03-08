"""
Main Discord bot implementation for AI Zoo.
"""
import os
import logging
import asyncio
from typing import Optional

from utils.config_loader import get_env, load_env_vars
from bots.base_bot import BaseDiscordBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIZooBot(BaseDiscordBot):
    """Main Discord bot for AI Zoo."""
    
    def __init__(self, 
                character_name: str,
                command_prefix: str = "!",
                intents: Optional[discord.Intents] = None):
        """
        Initialize the AI Zoo bot.
        
        Args:
            character_name: Name of the character this bot will play
            command_prefix: Command prefix for bot commands
            intents: Discord intents for the bot
        """
        super().__init__(character_name, command_prefix, intents)
        
    # メインボットは常に応答するので、オーバーライド不要
    # def should_respond_to_message(self, message) -> bool:
    #     return True


async def main():
    """Main entry point for the bot."""
    # Load environment variables
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
    load_env_vars(env_path)
    
    # Get bot token from environment
    token = get_env('DISCORD_TOKEN_BOT1')
    
    # Create and start the bot
    bot = AIZooBot(character_name="AI Zoo Bot 1")
    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
