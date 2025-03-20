"""
Base Discord bot implementation for AI Zoo.
This serves as a foundation for all bot implementations.
"""
import logging

from core.bot import BaseDiscordBot as CoreBaseDiscordBot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Re-export the core implementation for backwards compatibility
BaseDiscordBot = CoreBaseDiscordBot

# This module now serves as a compatibility layer and re-exports the refactored implementation
# All functionality has been moved to the core and mixins modules
