import secrets
from datetime import datetime, timezone

from valutatrade_hub.core.currencies import CURRENCIES, CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import parse_timestamp, validate_amount
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import run_scheduler
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

settings = SettingsLoader()
db = DatabaseManager()

RATES_TTL_SECONDS = settings.get("rates_ttl_seconds")
BASE_CURRENCY = settings.get("base_currency")


def user_to_dict(user: User) -> dict:
    """Упаковывает объект User в словарь для записи в JSON."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(),
    }


def dict_to_user(data: dict) -> User:
    """Распаковывает словарь из JSON в объект User."""
    return User(
        user_id=data["user_id"],
        username=data["username"],
        hashed_password=data["hashed_password"],
        salt=data["salt"],
        registration_date=datetime.fromisoformat(data["registration_date"]),
    )


def portfolio_to_dict(portfolio: Portfolio) -> dict:
    """Упаковывает объект Portfolio в словарь для записи в JSON."""
    wallets = {}
    for code, wallet in portfolio.wallets.items():
        wallets[code] = {"balance": wallet.balance}
    return {"user_id": portfolio.user_id, "wallets": wallets}


def dict_to_portfolio(data: dict) -> Portfolio:
    """Распаковывает словарь из JSON в объект Portfolio."""
    wallets = {}
    for code, info in data["wallets"].items():
        wallets[code] = Wallet(code, info["balance"])
    return Portfolio(data["user_id"], wallets)


def register_user(username: str, password: str) -> User:
    """Регистрирует нового пользователя и создаёт ему пустой портфель."""
    users = db.load("users", [])
    for item in users:
        if item["username"] == username.strip():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = len(users) + 1
    salt = secrets.token_hex(4)
    user = User(user_id, username, "", salt, datetime.now())
    user.change_password(password)

    users.append(user_to_dict(user))
    db.save("users", users)

    portfolios = db.load("portfolios", [])
    portfolios.append(portfolio_to_dict(Portfolio(user_id)))
    db.save("portfolios", portfolios)
    return user


_session = {"user": None}


def login_user(username: str, password: str) -> User:
    """Проверяет логин и пароль и запоминает вошедшего пользователя."""
    users = db.load("users", [])
    for item in users:
        if item["username"] == username.strip():
            user = dict_to_user(item)
            if not user.verify_password(password):
                raise ValueError("Неверный пароль")
            _session["user"] = user
            return user
    raise ValueError(f"Пользователь '{username}' не найден")


def get_current_user() -> User:
    """Возвращает вошедшего пользователя или просит выполнить login."""
    user = _session["user"]
    if user is None:
        raise ValueError("Сначала выполните login")
    return user


def build_updater() -> RatesUpdater:
    """Создаёт RatesUpdater с клиентами CoinGecko и ExchangeRate-API."""
    config = ParserConfig()
    clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    return RatesUpdater(clients, RatesStorage())


def update_rates(source: str | None = None) -> dict:
    """Запускает Parser Service (все источники или один) и обновляет кеш."""
    updater = build_updater()
    if source is not None:
        source = source.strip().lower()
        known = [client.key for client in updater.clients]
        if source not in known:
            raise ValueError(
                f"Неизвестный источник '{source}'. Доступно: {', '.join(known)}"
            )
    return updater.run_update(source)


def start_rates_scheduler(interval_seconds: int, on_report=None) -> None:
    """Запускает периодическое обновление курсов (остановка по Ctrl+C)."""
    run_scheduler(build_updater(), interval_seconds, on_report)


def _rate_to_base(pairs: dict, code: str) -> dict | None:
    """Возвращает свежий курс code→USD из кеша или None, если его нет или он старый."""
    now = datetime.now(timezone.utc)
    if code == BASE_CURRENCY:
        return {"rate": 1.0, "updated_at": now}
    entry = pairs.get(f"{code}_{BASE_CURRENCY}")
    if entry is None:
        return None
    updated_at = parse_timestamp(entry["updated_at"])
    if (now - updated_at).total_seconds() > RATES_TTL_SECONDS:
        return None
    return {"rate": entry["rate"], "updated_at": updated_at}


def _rate_from_cache(from_code: str, to_code: str) -> dict | None:
    """Считает курс from→to через USD по свежим данным кеша."""
    pairs = db.load("rates", {}).get("pairs", {})
    source = _rate_to_base(pairs, from_code)
    target = _rate_to_base(pairs, to_code)
    if source is None or target is None:
        return None
    return {
        "rate": source["rate"] / target["rate"],
        "updated_at": min(source["updated_at"], target["updated_at"]),
    }


def get_rate(from_code: str, to_code: str) -> dict:
    """Возвращает курс from→to из свежего кеша; если он устарел, обновляет его."""
    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code
    if from_code == to_code:
        return {"rate": 1.0, "updated_at": datetime.now(timezone.utc)}

    result = _rate_from_cache(from_code, to_code)
    if result is None:
        report = update_rates()
        result = _rate_from_cache(from_code, to_code)
        if result is None:
            reason = "; ".join(report["errors"])
            raise ApiRequestError(reason or f"курс {from_code}→{to_code} недоступен")
    return result


def get_cached_rates(
    currency: str | None = None, top: int | None = None, base: str | None = None
) -> dict:
    """Возвращает курсы из локального кеша с фильтрами currency, top и base."""
    snapshot = db.load("rates", {})
    pairs = snapshot.get("pairs", {})
    if not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. Выполните 'update-rates', "
            "чтобы загрузить данные."
        )
    base_code = BASE_CURRENCY if base is None else get_currency(base).code
    usd_rates = {BASE_CURRENCY: 1.0}
    for pair, entry in pairs.items():
        usd_rates[pair.split("_")[0]] = entry["rate"]
    if base_code not in usd_rates:
        raise ValueError(f"Курс для '{base_code}' не найден в кеше.")

    rows = {}
    for code, usd_rate in usd_rates.items():
        if code != base_code:
            rows[f"{code}_{base_code}"] = usd_rate / usd_rates[base_code]

    if currency is not None:
        wanted = currency.strip().upper()
        rows = {p: r for p, r in rows.items() if p.split("_")[0] == wanted}
        if not rows:
            raise ValueError(f"Курс для '{wanted}' не найден в кеше.")
    if top is not None:
        crypto = {}
        for pair, rate in rows.items():
            if isinstance(CURRENCIES.get(pair.split("_")[0]), CryptoCurrency):
                crypto[pair] = rate
        ordered = sorted(crypto.items(), key=lambda item: item[1], reverse=True)
        rows = dict(ordered[:top])
    else:
        rows = dict(sorted(rows.items()))
    return {
        "updated_at": snapshot.get("last_refresh"),
        "base": base_code,
        "rows": list(rows.items()),
    }


def load_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя из файла (или создаёт пустой)."""
    for item in db.load("portfolios", []):
        if item["user_id"] == user_id:
            return dict_to_portfolio(item)
    return Portfolio(user_id)


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель пользователя в файл."""
    portfolios = db.load("portfolios", [])
    new_item = portfolio_to_dict(portfolio)
    found = False
    for index, item in enumerate(portfolios):
        if item["user_id"] == portfolio.user_id:
            portfolios[index] = new_item
            found = True
    if not found:
        portfolios.append(new_item)
    db.save("portfolios", portfolios)


def convert(amount: float, from_code: str, to_code: str) -> float:
    """Переводит сумму из одной валюты в другую по текущему курсу."""
    if from_code == to_code:
        return amount
    return amount * get_rate(from_code, to_code)["rate"]


def show_portfolio(base_currency: str = "USD") -> dict:
    """Собирает данные портфеля вошедшего пользователя в базовой валюте."""
    user = get_current_user()
    base = base_currency.strip().upper()
    if base not in CURRENCIES:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")
    portfolio = load_portfolio(user.user_id)
    rows = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        value = convert(wallet.balance, code, base)
        rows.append({"currency": code, "balance": wallet.balance, "value": value})
        total += value
    return {"username": user.username, "base": base, "rows": rows, "total": total}


def get_or_create_wallet(portfolio: Portfolio, code: str) -> Wallet:
    """Возвращает кошелёк валюты, создавая его, если его ещё нет."""
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)
    return wallet


def get_rate_to_base(code: str) -> float:
    """Возвращает курс валюты к базовой (USD)."""
    if code == BASE_CURRENCY:
        return 1.0
    return get_rate(code, BASE_CURRENCY)["rate"]


@log_action("BUY", get_current_user, verbose=True)
def buy_currency(currency: str, amount: float) -> dict:
    """Покупает валюту: списывает USD и пополняет кошелёк покупаемой валюты."""
    user = get_current_user()
    code = get_currency(currency).code
    validate_amount(amount)
    portfolio = load_portfolio(user.user_id)
    wallet = get_or_create_wallet(portfolio, code)
    balance_before = wallet.balance

    rate = get_rate_to_base(code)
    if code != BASE_CURRENCY:
        get_or_create_wallet(portfolio, BASE_CURRENCY).withdraw(amount * rate)
    wallet.deposit(amount)
    save_portfolio(portfolio)
    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "before": balance_before,
        "after": wallet.balance,
        "cost": amount * rate,
    }


@log_action("SELL", get_current_user, verbose=True)
def sell_currency(currency: str, amount: float) -> dict:
    """Продаёт валюту: списывает её с кошелька и начисляет USD."""
    user = get_current_user()
    code = get_currency(currency).code
    validate_amount(amount)
    portfolio = load_portfolio(user.user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )
    balance_before = wallet.balance

    rate = get_rate_to_base(code)
    wallet.withdraw(amount)
    if code != BASE_CURRENCY:
        get_or_create_wallet(portfolio, BASE_CURRENCY).deposit(amount * rate)
    save_portfolio(portfolio)
    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "before": balance_before,
        "after": wallet.balance,
        "revenue": amount * rate,
    }