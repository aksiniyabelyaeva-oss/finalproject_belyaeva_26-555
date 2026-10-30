import secrets
from datetime import datetime

from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    USERS_FILE,
    load_json,
    save_json,
)


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