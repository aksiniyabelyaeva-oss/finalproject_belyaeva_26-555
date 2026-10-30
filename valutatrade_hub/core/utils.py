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