"""
Script for sending scheduled messages to Discord.
This can be triggered by cron jobs to start conversations at specific times.
"""
import os
import sys
import logging
import asyncio
import random
import discord
from typing import List, Optional

from utils.config_loader import get_env, load_env_vars

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScheduledMessageSender:
    """Class for sending scheduled messages to Discord."""
    
    def __init__(self, token: str, channel_id: int):
        """
        Initialize the scheduled message sender.
        
        Args:
            token: Discord bot token
            channel_id: Channel ID to send messages to
        """
        self.token = token
        self.channel_id = channel_id
        self.client = discord.Client(intents=discord.Intents.default())
        
        @self.client.event
        async def on_ready():
            logger.info(f"Logged in as {self.client.user}")
            await self.send_message()
            await self.client.close()
    
    async def send_message(self):
        """Send a scheduled message to the channel."""
        try:
            channel = self.client.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Could not find channel with ID: {self.channel_id}")
                return
                
            # Get message from command line arguments or use default
            message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else self.get_random_message()
            
            await channel.send(message)
            logger.info(f"Sent scheduled message: {message}")
        except Exception as e:
            logger.error(f"Failed to send scheduled message: {e}")
    
    def get_random_message(self) -> str:
        """
        Get a random message for different times of day.
        
        Returns:
            Random message appropriate for the current time
        """
        # Morning messages (5:00 - 11:59)
        morning_messages = [
            "おはようございます！今日も素晴らしい一日になりますように。",
            "Good morning everyone! How did you sleep?",
            "朝ですね。今日の予定は何ですか？",
            "Morning has broken! What's on everyone's mind today?",
            "新しい一日の始まりですね。今日はどんな日になるでしょうか？"
        ]
        
        # Afternoon messages (12:00 - 17:59)
        afternoon_messages = [
            "こんにちは！お昼ごはんは何を食べましたか？",
            "Afternoon all! How's the day treating you so far?",
            "今日の午後はどうですか？何か面白いことがありましたか？",
            "Taking an afternoon break? What's everyone up to?",
            "お昼の時間ですね。今日の調子はどうですか？"
        ]
        
        # Evening messages (18:00 - 23:59)
        evening_messages = [
            "こんばんは！今日はどんな一日でしたか？",
            "Evening everyone! How was your day?",
            "今日も一日お疲れ様でした。何か楽しいことはありましたか？",
            "Winding down for the day? What's on your mind?",
            "夜になりましたね。今日はどんな一日でしたか？"
        ]
        
        # Night messages (0:00 - 4:59)
        night_messages = [
            "夜更かしですね。何をしていますか？",
            "Still up? What's keeping you awake?",
            "静かな夜ですね。何か考え事でもしていますか？",
            "The quiet hours are sometimes the best for deep conversations. Anything on your mind?",
            "夜中ですが、まだ起きている人はいますか？"
        ]
        
        # Get current hour
        import datetime
        current_hour = datetime.datetime.now().hour
        
        # Select appropriate message list based on time of day
        if 5 <= current_hour < 12:
            messages = morning_messages
        elif 12 <= current_hour < 18:
            messages = afternoon_messages
        elif 18 <= current_hour < 24:
            messages = evening_messages
        else:  # 0 <= current_hour < 5
            messages = night_messages
        
        return random.choice(messages)


async def main():
    """Main entry point for the scheduled message sender."""
    # Load environment variables
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
    load_env_vars(env_path)
    
    # Get bot token and channel ID from environment
    token = get_env('DISCORD_TOKEN_BOT1')  # Use the first bot for scheduled messages
    channel_id = int(get_env('CHANNEL_ID'))
    
    # Create and start the scheduled message sender
    sender = ScheduledMessageSender(token, channel_id)
    await sender.client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
