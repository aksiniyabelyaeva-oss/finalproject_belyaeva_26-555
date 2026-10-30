import secrets
from datetime import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import EXCHANGE_RATES, Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    load_json,
    save_json,
)


RATES_TTL_SECONDS = 300

BASE_CURRENCY = "USD"


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
    users = load_json(USERS_FILE, [])
    for item in users:
        if item["username"] == username.strip():
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = len(users) + 1
    salt = secrets.token_hex(4)
    user = User(user_id, username, "", salt, datetime.now())
    user.change_password(password)

    users.append(user_to_dict(user))
    save_json(USERS_FILE, users)

    portfolios = load_json(PORTFOLIOS_FILE, [])
    portfolios.append(portfolio_to_dict(Portfolio(user_id)))
    save_json(PORTFOLIOS_FILE, portfolios)
    return user

_session = {"user": None}


def login_user(username: str, password: str) -> User:
    """Проверяет логин и пароль и запоминает вошедшего пользователя."""
    users = load_json(USERS_FILE, [])
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


def fetch_rate_from_stub(from_code: str, to_code: str) -> float | None:
    """Заглушка Parser Service: считает курс по фиксированной таблице."""
    if from_code not in EXCHANGE_RATES or to_code not in EXCHANGE_RATES:
        return None
    return EXCHANGE_RATES[from_code] / EXCHANGE_RATES[to_code]


def get_rate(from_code: str, to_code: str) -> dict:
    """Возвращает курс from→to из свежего кеша или из заглушки."""
    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code

    key = f"{from_code}_{to_code}"
    rates = load_json(RATES_FILE, {})
    cached = rates.get(key)
    if cached is not None:
        updated_at = datetime.fromisoformat(cached["updated_at"])
        if (datetime.now() - updated_at).total_seconds() < RATES_TTL_SECONDS:
            return {"rate": cached["rate"], "updated_at": updated_at}

    rate = fetch_rate_from_stub(from_code, to_code)
    if rate is None:
        raise ApiRequestError(f"курс {from_code}→{to_code} недоступен")
    now = datetime.now()
    rates[key] = {"rate": rate, "updated_at": now.isoformat()}
    rates["source"] = "Stub"
    rates["last_refresh"] = now.isoformat()
    save_json(RATES_FILE, rates)
    return {"rate": rate, "updated_at": now}


def load_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя из файла (или создаёт пустой)."""
    for item in load_json(PORTFOLIOS_FILE, []):
        if item["user_id"] == user_id:
            return dict_to_portfolio(item)
    return Portfolio(user_id)


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель пользователя в файл."""
    portfolios = load_json(PORTFOLIOS_FILE, [])
    new_item = portfolio_to_dict(portfolio)
    found = False
    for index, item in enumerate(portfolios):
        if item["user_id"] == portfolio.user_id:
            portfolios[index] = new_item
            found = True
    if not found:
        portfolios.append(new_item)
    save_json(PORTFOLIOS_FILE, portfolios)


def convert(amount: float, from_code: str, to_code: str) -> float:
    """Переводит сумму из одной валюты в другую по текущему курсу."""
    if from_code == to_code:
        return amount
    return amount * get_rate(from_code, to_code)["rate"]


def show_portfolio(base_currency: str = "USD") -> dict:
    """Собирает данные портфеля вошедшего пользователя в базовой валюте."""
    user = get_current_user()
    base = base_currency.strip().upper()
    if base not in EXCHANGE_RATES:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")
    portfolio = load_portfolio(user.user_id)
    rows = []
    total = 0.0
    for code, wallet in portfolio.wallets.items():
        value = convert(wallet.balance, code, base)
        rows.append({"currency": code, "balance": wallet.balance, "value": value})
        total += value
    return {"username": user.username, "base": base, "rows": rows, "total": total}


def validate_amount(amount: float) -> None:
    """Проверяет, что сумма — положительное число."""
    is_number = isinstance(amount, (int, float)) and not isinstance(amount, bool)
    if not is_number or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")


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