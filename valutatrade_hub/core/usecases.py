import secrets
from datetime import datetime

from valutatrade_hub.core.models import EXCHANGE_RATES, Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    load_json,
    save_json,
)

RATES_TTL_SECONDS = 300


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
    from_code = from_code.strip().upper()
    to_code = to_code.strip().upper()
    if not from_code or not to_code:
        raise ValueError("Код валюты не может быть пустым")

    key = f"{from_code}_{to_code}"
    rates = load_json(RATES_FILE, {})
    cached = rates.get(key)
    if cached is not None:
        updated_at = datetime.fromisoformat(cached["updated_at"])
        if (datetime.now() - updated_at).total_seconds() < RATES_TTL_SECONDS:
            return {"rate": cached["rate"], "updated_at": updated_at}

    rate = fetch_rate_from_stub(from_code, to_code)
    if rate is None:
        raise ValueError(
            f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже."
        )
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