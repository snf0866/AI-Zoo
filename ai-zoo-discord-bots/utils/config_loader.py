"""
Utility for loading environment variables and configuration files.
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env_vars(env_file: Optional[str] = None) -> Dict[str, str]:
    """
    Load environment variables from .env file if it exists.
    
    Args:
        env_file: Path to .env file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    # If env_file is provided and exists, load variables from it
    if env_file and os.path.exists(env_file):
        logger.info(f"Loading environment variables from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                key, value = line.split('=', 1)
                env_vars[key] = value
                
                # Also set as actual environment variable
                os.environ[key] = value
    
    return env_vars


def get_env(key: str, default: Optional[str] = None) -> str:
    """
    Get environment variable with fallback to default.
    
    Args:
        key: Environment variable name
        default: Default value if environment variable is not set
        
    Returns:
        Environment variable value or default
        
    Raises:
        ValueError: If environment variable is not set and no default is provided
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"Environment variable {key} is not set and no default provided")
    return value


def load_json_config(config_path: str) -> Dict[str, Any]:
    """
    Load JSON configuration file.
    
    Args:
        config_path: Path to JSON configuration file
        
    Returns:
        Configuration as dictionary
        
    Raises:
        FileNotFoundError: If configuration file does not exist
        json.JSONDecodeError: If configuration file is not valid JSON
    """
    logger.info(f"Loading configuration from {config_path}")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found")
        
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    # Process any environment variable references in the config
    process_env_vars_in_config(config)
        
    return config


def process_env_vars_in_config(config: Dict[str, Any]) -> None:
    """
    Process environment variable references in configuration.
    Replaces ${ENV_VAR} with the value of the environment variable.
    
    Args:
        config: Configuration dictionary to process (modified in-place)
    """
    if isinstance(config, dict):
        for key, value in config.items():
            if isinstance(value, (dict, list)):
                process_env_vars_in_config(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config[key] = get_env(env_var)
    elif isinstance(config, list):
        for i, item in enumerate(config):
            if isinstance(item, (dict, list)):
                process_env_vars_in_config(item)
            elif isinstance(item, str) and item.startswith('${') and item.endswith('}'):
                env_var = item[2:-1]
                config[i] = get_env(env_var)


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path to project root directory
    """
    # This assumes this file is in utils/ directory
    return Path(__file__).parent.parent


def get_config_path(config_name: str) -> Path:
    """
    Get the path to a configuration file.
    
    Args:
        config_name: Name of configuration file
        
    Returns:
        Path to configuration file
    """
    return get_project_root() / 'config' / config_name
