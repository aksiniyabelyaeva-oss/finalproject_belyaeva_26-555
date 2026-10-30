from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError

CODE_MIN_LENGTH = 2
CODE_MAX_LENGTH = 5


class Currency(ABC):
    """Абстрактная валюта: общие атрибуты и интерфейс."""

    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        is_valid_code = (
            isinstance(code, str)
            and CODE_MIN_LENGTH <= len(code) <= CODE_MAX_LENGTH
            and " " not in code
            and code == code.upper()
        )
        if not is_valid_code:
            raise ValueError(
                "Код валюты должен быть в верхнем регистре, "
                f"от {CODE_MIN_LENGTH} до {CODE_MAX_LENGTH} символов, без пробелов"
            )
        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строку с описанием валюты для интерфейса и логов."""


class FiatCurrency(Currency):
    """Фиатная (государственная) валюта."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
        super().__init__(name, code)
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        market_cap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {market_cap})"
        )


CURRENCIES = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of History", 8.0e10),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду или выбрасывает CurrencyNotFoundError."""
    key = code.strip().upper()
    if key not in CURRENCIES:
        raise CurrencyNotFoundError(key)
    return CURRENCIES[key]