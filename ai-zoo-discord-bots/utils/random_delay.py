"""
Utility for adding random delays to bot responses to simulate more natural conversation.
"""
import asyncio
import random
import logging
from typing import Optional, Tuple

# ロガーのセットアップ
logger = logging.getLogger(__name__)

async def delay_response(min_seconds: int = 5, max_seconds: int = 15) -> None:
    """
    Delay the bot's response by a random amount of time within the specified range.
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.randint(min_seconds, max_seconds)
    await asyncio.sleep(delay)

def get_typing_duration(message_length: int, 
                         typing_speed_range: Tuple[int, int] = (400, 800)) -> Tuple[float, int]:
    """
    Calculate a realistic typing duration based on message length and typing speed.
    
    Args:
        message_length: Length of the message in characters
        typing_speed_range: Range of typing speed in characters per minute (min, max)
    
    Returns:
        Tuple of (typing duration in seconds, actual typing speed in characters per minute)
    """
    # Calculate typing speed in characters per minute
    typing_speed = random.randint(typing_speed_range[0], typing_speed_range[1])
    
    # Convert to characters per second for duration calculation
    typing_speed_per_second = typing_speed / 60
    
    # Calculate typing duration with some randomness
    base_duration = message_length / typing_speed_per_second
    randomness = random.uniform(0.8, 1.2)  # Add 20% randomness
    
    # 実際の所要時間
    actual_duration = base_duration * randomness
    
    return actual_duration, typing_speed

async def simulate_typing(channel, message_length: int, 
                          typing_speed_range: Tuple[int, int] = (400, 800)) -> Tuple[float, int]:
    """
    Simulate typing in a Discord channel for a realistic duration.
    
    Args:
        channel: Discord channel to simulate typing in
        message_length: Length of the message in characters
        typing_speed_range: Range of typing speed in characters per minute (min, max)
    
    Returns:
        Tuple of (actual typing duration in seconds, typing speed in characters per minute)
    """
    duration, typing_speed = get_typing_duration(message_length, typing_speed_range)
    
    # ログに記録
    channel_name = getattr(channel, 'name', 'Unknown')
    logger.info(f"Simulating typing in channel '{channel_name}': {message_length} chars at {typing_speed} chars/min (expected duration: {duration:.2f}s)")
    
    start_time = asyncio.get_event_loop().time()
    
    # Discord's typing indicator lasts 10 seconds, so we need to send it multiple times
    # for longer messages
    async with channel.typing():
        remaining_time = duration
        while remaining_time > 0:
            await asyncio.sleep(min(remaining_time, 9.5))
            remaining_time -= 9.5
            if remaining_time > 0:
                # Need to restart typing indicator
                async with channel.typing():
                    pass
    
    actual_duration = asyncio.get_event_loop().time() - start_time
    
    # 実際の所要時間もログに記録
    logger.info(f"Typing simulation completed: actual duration {actual_duration:.2f}s (expected: {duration:.2f}s)")
    
    return actual_duration, typing_speed
