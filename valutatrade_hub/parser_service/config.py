import os
from dataclasses import dataclass, field

from valutatrade_hub.infra.settings import SettingsLoader

settings = SettingsLoader()


def _data_path(file_key: str) -> str:
    """Собирает путь к файлу в папке данных по ключу настройки."""
    return os.path.join(settings.get("data_dir"), settings.get(file_key))


@dataclass
class ParserConfig:
    """Все настройки Parser Service в одном месте."""

    # Ключ загружается из переменной окружения (не хранится в коде)
    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )

    # Эндпоинты
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    # Пути к файлам
    RATES_FILE_PATH: str = field(default_factory=lambda: _data_path("rates_file"))
    HISTORY_FILE_PATH: str = field(
        default_factory=lambda: _data_path("history_file")
    )

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10
    UPDATE_INTERVAL_SECONDS: int = field(
        default_factory=lambda: settings.get("parser_interval_seconds")
    )
