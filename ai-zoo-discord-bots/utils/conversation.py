"""
Utility for managing conversation history and formatting messages for LLM APIs.
"""
from typing import List, Dict, Any, Optional
import re
import datetime


class ConversationManager:
    def __init__(self, max_history: int = 10, max_tokens: int = 4000):
        """
        Initialize the conversation manager.
        
        Args:
            max_history: Maximum number of messages to keep in history
            max_tokens: Approximate maximum number of tokens to keep in history
                        (rough estimate, not exact)
        """
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.max_tokens = max_tokens
        self.conversation_turns = 0
        
    def add_message(self, author: str, content: str, bot_name: Optional[str] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            author: Name or ID of the message author
            content: Message content
            bot_name: Name of the bot processing this message (to track if this is the bot's own message)
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Check if this is a message from the bot itself
        is_self = bot_name is not None and author == bot_name
        
        message = {
            "author": author,
            "content": content,
            "timestamp": timestamp,
            "is_self": is_self
        }
        
        self.history.append(message)
        
        # If we've exceeded max history, remove oldest messages
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            
        # If this is not the bot's own message, increment conversation turns
        if not is_self:
            self.conversation_turns += 1
            
    def get_recent_messages(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent messages from the conversation history.
        
        Args:
            count: Number of recent messages to retrieve
            
        Returns:
            List of recent messages
        """
        return self.history[-count:] if len(self.history) >= count else self.history
    
    def format_for_openai(self, system_prompt: str) -> List[Dict[str, str]]:
        """
        Format the conversation history for OpenAI API.
        
        Args:
            system_prompt: System prompt to use for the conversation
            
        Returns:
            List of messages formatted for OpenAI API
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in self.history:
            role = "assistant" if msg.get("is_self", False) else "user"
            
            # 他のボットからのメッセージを区別するためのプレフィックスを追加
            if not msg.get("is_self", False) and msg['author'].lower() in ['gpt-4o-animal', 'claude-animal', 'gpt-4o', 'claude']:
                # ボットの名前リストを拡張する必要がある場合は、ここに追加
                content = f"Bot ({msg['author']}): {msg['content']}"
            else:
                content = f"{msg['author']}: {msg['content']}"
                
            messages.append({"role": role, "content": content})
            
        return messages
    
    def format_for_anthropic(self, system_prompt: str) -> str:
        """
        Format the conversation history for Anthropic Claude API.
        
        Args:
            system_prompt: System prompt to use for the conversation
            
        Returns:
            Formatted conversation for Anthropic API
        """
        conversation = f"{system_prompt}\n\n"
        
        for msg in self.history:
            # 自分のメッセージはAssistant、他のボットのメッセージはBot (名前)、それ以外はHuman (名前)として表示
            if msg.get("is_self", False):
                prefix = "Assistant"
            elif msg['author'].lower() in ['gpt-4o-animal', 'claude-animal', 'gpt-4o', 'claude']:
                # ボットの名前リストを拡張する必要がある場合は、ここに追加
                prefix = f"Bot ({msg['author']})"
            else:
                prefix = f"Human ({msg['author']})"
            
            conversation += f"{prefix}: {msg['content']}\n\n"
            
        conversation += "Assistant: "
        return conversation
    
    def reset_conversation_turns(self) -> None:
        """Reset the conversation turn counter."""
        self.conversation_turns = 0
        
    def should_cool_down(self, max_turns: int = 10) -> bool:
        """
        Check if the bot should cool down (stop responding) based on conversation turns.
        
        Args:
            max_turns: Maximum number of turns before cooling down
            
        Returns:
            True if the bot should cool down, False otherwise
        """
        return self.conversation_turns >= max_turns
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history = []
        self.conversation_turns = 0
        
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in a text.
        This is a rough approximation, not an exact count.
        
        Args:
            text: Text to estimate token count for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
