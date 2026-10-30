import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_LOG_BYTES = 1_000_000
BACKUP_COUNT = 3


def _configure_logger(name: str, file_name: str) -> None:
    """Подключает к логгеру запись в файл с ротацией по размеру."""
    settings = SettingsLoader()
    log_dir = settings.get("log_dir")
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(settings.get("log_level"))
    if logger.handlers:
        return
    handler = RotatingFileHandler(
        os.path.join(log_dir, file_name),
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(handler)


def setup_logging() -> None:
    """Настраивает логи операций (actions.log) и Parser Service (parser.log)."""
    settings = SettingsLoader()
    _configure_logger("valutatrade", settings.get("log_file"))
    _configure_logger("parser_service", settings.get("parser_log_file"))
