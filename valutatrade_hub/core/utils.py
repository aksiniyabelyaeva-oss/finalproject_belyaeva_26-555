from datetime import datetime, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def validate_amount(amount: float) -> None:
    """Проверяет, что сумма — положительное число."""
    is_number = isinstance(amount, (int, float)) and not isinstance(amount, bool)
    if not is_number or amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")


def format_rate(rate: float) -> str:
    """Форматирует курс: большие числа с 2 знаками, маленькие с 8."""
    if rate >= 1:
        return f"{rate:.2f}"
    return f"{rate:.8f}"


def utc_timestamp() -> str:
    """Возвращает текущее время UTC в формате 2025-10-10T12:00:00Z."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def parse_timestamp(text: str) -> datetime:
    """Превращает строку вида 2025-10-10T12:00:00Z в дату с часовым поясом UTC."""
    return datetime.strptime(text, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
