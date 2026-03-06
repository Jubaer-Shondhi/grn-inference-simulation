"""Configuration management utilities."""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_dir: str = "configs"):
        """
        Initialize the config manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        
    def load_config(self, config_name: str = "config.yaml") -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_name: Name of the config file
            
        Returns:
            Dictionary containing configuration
        """
        config_path = self.config_dir / config_name
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        logger.info(f"Loaded configuration from {config_path}")
        return config
    
    def load_objectives(self) -> Dict[str, Any]:
        """Load objectives configuration."""
        return self.load_config("objectives.yaml")
    
    def merge_configs(self, *config_names: str) -> Dict[str, Any]:
        """
        Merge multiple configuration files.
        
        Args:
            *config_names: Variable number of config file names
            
        Returns:
            Merged configuration dictionary
        """
        merged_config = {}
        
        for config_name in config_names:
            config = self.load_config(config_name)
            merged_config.update(config)
            
        return merged_config