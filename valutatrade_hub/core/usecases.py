from datetime import datetime

from valutatrade_hub.core.models import Portfolio, User, Wallet


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