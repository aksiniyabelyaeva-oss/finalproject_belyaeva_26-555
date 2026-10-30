import time
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig

HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_TOO_MANY_REQUESTS = 429
MS_IN_SECOND = 1000
RATE_DIGITS = 8


def _is_valid_rate(value) -> bool:
    """Проверяет, что значение — положительное число (не bool)."""
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    return is_number and value > 0


class BaseApiClient(ABC):
    """Общий интерфейс клиентов внешних API курсов."""

    name = ""  # имя источника для логов и истории
    key = ""  # короткий ключ для команды update-rates --source

    def __init__(self, config: ParserConfig):
        self.config = config
        self.meta: dict = {}  # дополнительные данные запроса по каждой паре

    @abstractmethod
    def fetch_rates(self) -> dict:
        """Возвращает курсы к базовой валюте: {"BTC_USD": 59337.21, ...}."""

    def _request(self, url: str, params: dict | None = None):
        """Выполняет GET-запрос и превращает сбои в ApiRequestError."""
        started = time.monotonic()
        try:
            response = requests.get(
                url, params=params, timeout=self.config.REQUEST_TIMEOUT
            )
        except requests.exceptions.RequestException as error:
            # Текст исходной ошибки не показываем: в нём может быть адрес с ключом
            raise ApiRequestError(
                f"сетевая ошибка ({type(error).__name__})"
            ) from None
        request_ms = int((time.monotonic() - started) * MS_IN_SECOND)
        status = response.status_code
        if status == HTTP_TOO_MANY_REQUESTS:
            raise ApiRequestError(f"превышен лимит запросов ({status})")
        if status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
            raise ApiRequestError("доступ запрещён, проверьте ключ")
        if status != HTTP_OK:
            raise ApiRequestError(f"сервис ответил статусом {status}")
        return response, request_ms

    def _read_json(self, response):
        """Разбирает JSON-ответ или выбрасывает ApiRequestError."""
        try:
            return response.json()
        except ValueError:
            raise ApiRequestError("некорректный ответ сервиса") from None

    def _make_meta(self, raw_id: str, response, request_ms: int) -> dict:
        """Собирает служебные данные запроса для истории."""
        return {
            "raw_id": raw_id,
            "request_ms": request_ms,
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
        }


class CoinGeckoClient(BaseApiClient):
    """Курсы криптовалют из CoinGecko."""

    name = "CoinGecko"
    key = "coingecko"

    def fetch_rates(self) -> dict:
        config = self.config
        base = config.BASE_CURRENCY.lower()
        ids = ",".join(config.CRYPTO_ID_MAP[code] for code in config.CRYPTO_CURRENCIES)
        response, request_ms = self._request(
            config.COINGECKO_URL, {"ids": ids, "vs_currencies": base}
        )
        data = self._read_json(response)
        rates = {}
        for code in config.CRYPTO_CURRENCIES:
            raw_id = config.CRYPTO_ID_MAP[code]
            entry = data.get(raw_id) if isinstance(data, dict) else None
            price = entry.get(base) if isinstance(entry, dict) else None
            if not _is_valid_rate(price):
                continue
            pair = f"{code}_{config.BASE_CURRENCY}"
            rates[pair] = float(price)
            self.meta[pair] = self._make_meta(raw_id, response, request_ms)
        if not rates:
            raise ApiRequestError("в ответе нет ожидаемых курсов")
        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Курсы фиатных валют из ExchangeRate-API."""

    name = "ExchangeRate-API"
    key = "exchangerate"

    def fetch_rates(self) -> dict:
        config = self.config
        if not config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                "не задана переменная EXCHANGERATE_API_KEY"
            )
        url = (
            f"{config.EXCHANGERATE_API_URL}/{config.EXCHANGERATE_API_KEY}"
            f"/latest/{config.BASE_CURRENCY}"
        )
        response, request_ms = self._request(url)
        data = self._read_json(response)
        if not isinstance(data, dict) or data.get("result") != "success":
            reason = data.get("error-type") if isinstance(data, dict) else None
            raise ApiRequestError(f"сервис вернул ошибку ({reason})")
        # В реальном ответе таблица называется conversion_rates (в описании: rates)
        table = data.get("conversion_rates") or data.get("rates") or {}
        rates = {}
        for code in config.FIAT_CURRENCIES:
            value = table.get(code)
            if not _is_valid_rate(value):
                continue
            pair = f"{code}_{config.BASE_CURRENCY}"
            # API отдаёт «сколько единиц валюты за 1 USD», нам нужен обратный курс
            rates[pair] = round(1 / value, RATE_DIGITS)
            self.meta[pair] = self._make_meta(code, response, request_ms)
        if not rates:
            raise ApiRequestError("в ответе нет ожидаемых курсов")
        return rates
