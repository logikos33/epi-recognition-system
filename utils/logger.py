"""
Logging Configuration for EPI Recognition System
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from utils.config import get_config


class CustomFormatter(logging.Formatter):
    """
    Custom formatter with colors for console output
    """
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logger:
    """
    Logger class for the EPI Recognition System
    """

    def __init__(
        self,
        name: str,
        level: Optional[str] = None,
        log_file: Optional[Path] = None,
        console_output: bool = True
    ):
        """
        Initialize logger

        Args:
            name: Logger name (usually __name__ of the module)
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file
            console_output: Whether to output to console
        """
        self.logger = logging.getLogger(name)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        config = get_config()
        self.level = level or config.log_level
        self.log_file = log_file or config.log_file
        self.console_output = console_output

        # Set logging level
        self.logger.setLevel(getattr(logging, self.level.upper()))

        # Create handlers
        handlers = []

        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.level.upper()))
            console_handler.setFormatter(CustomFormatter())
            handlers.append(console_handler)

        # File handler
        if self.log_file:
            # Ensure log directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(getattr(logging, self.level.upper()))
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
            )
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)

        # Add handlers to logger
        for handler in handlers:
            self.logger.addHandler(handler)

    def debug(self, message, *args, **kwargs):
        """Log debug message"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """Log info message"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """Log warning message"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """Log error message"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        """Log critical message"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, *args, **kwargs)

    def get_logger(self):
        """
        Get the underlying logger instance

        Returns:
            logging.Logger: Logger instance
        """
        return self.logger


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> Logger:
    """
    Get or create a logger instance

    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file
        console_output: Whether to output to console

    Returns:
        Logger: Logger instance
    """
    return Logger(name, level, log_file, console_output)


# Convenience function for quick logger access
def log_debug(message: str):
    """Quick debug log"""
    get_logger(__name__).debug(message)


def log_info(message: str):
    """Quick info log"""
    get_logger(__name__).info(message)


def log_warning(message: str):
    """Quick warning log"""
    get_logger(__name__).warning(message)


def log_error(message: str):
    """Quick error log"""
    get_logger(__name__).error(message)


def log_critical(message: str):
    """Quick critical log"""
    get_logger(__name__).critical(message)


def log_exception(message: str):
    """Quick exception log"""
    get_logger(__name__).exception(message)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True
):
    """
    Setup logging for the entire application

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        console_output: Whether to output to console
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)'
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(CustomFormatter())
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False
