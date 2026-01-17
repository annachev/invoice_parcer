#!/usr/bin/env python3
"""
Configuration Management
Loads and validates application configuration from config.yaml
"""

import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .logging_config import get_logger
from .exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class WindowConfig:
    """GUI window configuration"""
    width: int = 1200
    height: int = 600
    title: str = "Invoice Processor"

    @property
    def geometry(self) -> str:
        """Return window geometry string"""
        return f"{self.width}x{self.height}"


@dataclass
class FolderConfig:
    """Folder paths configuration"""
    pending: Path
    processed: Path

    def __post_init__(self):
        """Convert strings to Path objects"""
        if isinstance(self.pending, str):
            self.pending = Path(self.pending)
        if isinstance(self.processed, str):
            self.processed = Path(self.processed)

    def ensure_folders_exist(self):
        """Create folders if they don't exist"""
        self.pending.mkdir(parents=True, exist_ok=True)
        self.processed.mkdir(parents=True, exist_ok=True)
        logger.info(f"Folders ensured: {self.pending}, {self.processed}")


@dataclass
class ScannerConfig:
    """Background scanner configuration"""
    interval_seconds: int = 300
    enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: Optional[str] = "invoice_processor.log"
    console: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class ParserConfig:
    """Parser configuration"""
    confidence_threshold: float = 0.9
    strategies: dict = None

    def __post_init__(self):
        if self.strategies is None:
            self.strategies = {
                'two_column': True,
                'single_column': True,
                'company_specific': True,
                'pattern_fallback': True
            }


@dataclass
class ThreadingConfig:
    """Threading configuration"""
    max_workers: int = 4
    update_delay_ms: int = 50


@dataclass
class DevelopmentConfig:
    """Development settings"""
    debug: bool = False
    verbose_errors: bool = False


@dataclass
class Config:
    """Main application configuration"""
    window: WindowConfig
    folders: FolderConfig
    scanner: ScannerConfig
    logging: LoggingConfig
    parser: ParserConfig
    threading: ThreadingConfig
    development: DevelopmentConfig

    @classmethod
    def from_file(cls, config_path: str = "config.yaml") -> 'Config':
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml file

        Returns:
            Config instance with loaded settings

        Raises:
            ConfigurationError: If config file is missing or invalid
        """
        config_file = Path(config_path)

        try:
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return cls.default()

            logger.info(f"Loading configuration from: {config_path}")

            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                logger.warning(f"Empty config file: {config_path}, using defaults")
                return cls.default()

            # Parse each section
            return cls(
                window=WindowConfig(**data.get('app', {}).get('window', {})),
                folders=FolderConfig(**data.get('folders', {})),
                scanner=ScannerConfig(**data.get('scanner', {})),
                logging=LoggingConfig(**data.get('logging', {})),
                parser=ParserConfig(**data.get('parser', {})),
                threading=ThreadingConfig(**data.get('threading', {})),
                development=DevelopmentConfig(**data.get('development', {}))
            )

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {e}") from e

    @classmethod
    def default(cls) -> 'Config':
        """
        Create configuration with default values.

        Returns:
            Config instance with all default settings
        """
        logger.info("Using default configuration")
        return cls(
            window=WindowConfig(),
            folders=FolderConfig(
                pending=Path("invoice_processor/invoices/pending"),
                processed=Path("invoice_processor/invoices/processed")
            ),
            scanner=ScannerConfig(),
            logging=LoggingConfig(),
            parser=ParserConfig(),
            threading=ThreadingConfig(),
            development=DevelopmentConfig()
        )

    def validate(self):
        """
        Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate window size
        if self.window.width < 800 or self.window.height < 600:
            raise ConfigurationError("Window size must be at least 800x600")

        # Validate scanner interval
        if self.scanner.interval_seconds < 10:
            raise ConfigurationError("Scanner interval must be at least 10 seconds")

        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ConfigurationError(f"Invalid log level: {self.logging.level}")

        # Validate confidence threshold
        if not 0.0 <= self.parser.confidence_threshold <= 1.0:
            raise ConfigurationError("Confidence threshold must be between 0.0 and 1.0")

        # Validate max workers
        if self.threading.max_workers < 1 or self.threading.max_workers > 16:
            raise ConfigurationError("Max workers must be between 1 and 16")

        logger.debug("Configuration validated successfully")


# Global config instance (loaded on import)
_config: Optional[Config] = None


def get_config(config_path: str = "config.yaml") -> Config:
    """
    Get the global configuration instance.

    Args:
        config_path: Path to config file (only used on first call)

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        try:
            _config = Config.from_file(config_path)
            _config.validate()
            _config.folders.ensure_folders_exist()
        except Exception as e:
            logger.error(f"Failed to load config, using defaults: {e}")
            _config = Config.default()
            _config.folders.ensure_folders_exist()
    return _config


def reload_config(config_path: str = "config.yaml"):
    """
    Reload configuration from file.

    Args:
        config_path: Path to config file
    """
    global _config
    _config = None
    return get_config(config_path)


if __name__ == "__main__":
    # Test configuration loading
    config = get_config()
    print(f"Window: {config.window.geometry}")
    print(f"Pending folder: {config.folders.pending}")
    print(f"Scanner interval: {config.scanner.interval_seconds}s")
    print(f"Log level: {config.logging.level}")
    print(f"Confidence threshold: {config.parser.confidence_threshold}")
