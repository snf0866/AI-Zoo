"""
Utility for adding random delays to bot responses to simulate more natural conversation.
"""
import asyncio
import random
from typing import Optional, Tuple


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
                         typing_speed_range: Tuple[int, int] = (50, 100)) -> float:
    """
    Calculate a realistic typing duration based on message length and typing speed.
    
    Args:
        message_length: Length of the message in characters
        typing_speed_range: Range of typing speed in characters per minute (min, max)
    
    Returns:
        Typing duration in seconds
    """
    # Calculate typing speed in characters per second
    typing_speed = random.randint(typing_speed_range[0], typing_speed_range[1]) / 60
    
    # Calculate typing duration with some randomness
    base_duration = message_length / typing_speed
    randomness = random.uniform(0.8, 1.2)  # Add 20% randomness
    
    return base_duration * randomness


async def simulate_typing(channel, message_length: int, 
                          typing_speed_range: Tuple[int, int] = (50, 100)) -> None:
    """
    Simulate typing in a Discord channel for a realistic duration.
    
    Args:
        channel: Discord channel to simulate typing in
        message_length: Length of the message in characters
        typing_speed_range: Range of typing speed in characters per minute (min, max)
    """
    duration = get_typing_duration(message_length, typing_speed_range)
    
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
