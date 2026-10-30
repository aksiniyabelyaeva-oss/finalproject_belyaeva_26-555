import os
import tomllib
from typing import Any

PYPROJECT_FILE = "pyproject.toml"

DEFAULT_SETTINGS = {
    "data_dir": "data",
    "users_file": "users.json",
    "portfolios_file": "portfolios.json",
    "rates_file": "rates.json",
    "rates_ttl_seconds": 300,
    "base_currency": "USD",
    "log_dir": "logs",
    "log_file": "actions.log",
    "log_level": "INFO",
}


class SettingsLoader:
    """Singleton: загружает настройки проекта один раз.

    Singleton сделан через __new__: это проще и читабельнее метакласса,
    а повторные вызовы SettingsLoader() всегда возвращают один и тот же объект.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Читает настройки: значения по умолчанию и секцию из pyproject.toml."""
        self._settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(PYPROJECT_FILE):
            with open(PYPROJECT_FILE, "rb") as file:
                config = tomllib.load(file)
            self._settings.update(config.get("tool", {}).get("valutatrade", {}))

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу."""
        return self._settings.get(key, default)

    def reload(self) -> None:
        """Перечитывает настройки из файла."""
        self._load()