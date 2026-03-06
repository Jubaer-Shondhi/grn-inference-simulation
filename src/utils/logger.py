"""Logging configuration for the GRN inference pipeline."""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging(
    level="INFO",
    log_file: Optional[str] = None,
    simple_format: bool = False
) -> logging.Logger:
    """
    Setup logging configuration for the pipeline.
    """
    # Convert to uppercase if it's a string
    if isinstance(level, str):
        level = level.upper()
        numeric_level = getattr(logging, level, logging.INFO)
    else:
        numeric_level = level
    
    # Create formatters
    if simple_format:
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)