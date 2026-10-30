import logging
from functools import wraps

from valutatrade_hub.infra.settings import SettingsLoader

logger = logging.getLogger("valutatrade")


def _get_username(user_getter) -> str | None:
    """Возвращает имя вошедшего пользователя или None."""
    try:
        return user_getter().username
    except Exception:
        return None


def log_action(action: str, user_getter, verbose: bool = False):
    """Фабрика декоратора: логирует операцию, не глотая исключения."""

    def decorator(func):
        @wraps(func)
        def wrapper(currency: str, amount: float):
            base = SettingsLoader().get("base_currency")
            username = _get_username(user_getter)
            head = f"{action} user={username!r} currency={currency!r}"
            head += f" amount={amount:.4f}"
            try:
                result = func(currency, amount)
            except Exception as error:
                logger.info(
                    f"{head} result=ERROR error_type={type(error).__name__} "
                    f"error_message={str(error)!r}"
                )
                raise
            message = f"{head} rate={result['rate']:.8g} base={base!r} result=OK"
            if verbose:
                message += f" balance={result['before']:.4f}->{result['after']:.4f}"
            logger.info(message)
            return result

        return wrapper

    return decorator