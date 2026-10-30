import logging
import os
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_LOG_BYTES = 1_000_000
BACKUP_COUNT = 3


def setup_logging() -> None:
    """Настраивает запись логов в файл с ротацией по размеру."""
    settings = SettingsLoader()
    log_dir = settings.get("log_dir")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, settings.get("log_file")),
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger = logging.getLogger("valutatrade")
    logger.setLevel(settings.get("log_level"))
    if not logger.handlers:
        logger.addHandler(handler)