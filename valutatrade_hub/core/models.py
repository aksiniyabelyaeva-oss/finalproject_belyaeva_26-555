import hashlib
from datetime import datetime


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Меняет имя, имя не может быть пустым."""
        if not value or not value.strip():
            raise ValueError("Имя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Хеш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации."""
        return self._registration_date


    def _hash_password(self, password: str) -> str:
        """Возвращает хеш пароля, посчитанный вместе с солью."""
        return hashlib.sha256((password + self._salt).encode()).hexdigest()

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Меняет пароль: проверяет длину и сохраняет хеш."""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")
        self._hashed_password = self._hash_password(new_password)

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохранённым хешем."""
        return self._hash_password(password) == self._hashed_password


class Wallet:
    """Кошелёк пользователя для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self) -> float:
        """Текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс с проверками типа и знака."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)


    def _check_amount(self, amount: float) -> None:
        """Проверяет, что сумма — положительное число."""
        is_number = isinstance(amount, (int, float)) and not isinstance(amount, bool)
        if not is_number or amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")

    def deposit(self, amount: float) -> None:
        """Пополняет баланс на указанную сумму."""
        self._check_amount(amount)
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снимает средства, если их достаточно."""
        self._check_amount(amount)
        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств: доступно {self._balance:.4f} "
                f"{self.currency_code}, требуется {amount:.4f} {self.currency_code}"
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        """Возвращает строку с информацией о балансе."""
        return f"{self.currency_code}: {self._balance:.4f}"