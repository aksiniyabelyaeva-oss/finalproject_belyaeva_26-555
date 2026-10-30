import shlex

from valutatrade_hub.core.currencies import CURRENCIES
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import (
    BASE_CURRENCY,
    buy_currency,
    get_rate,
    login_user,
    register_user,
    sell_currency,
    show_portfolio,
)
from valutatrade_hub.core.utils import format_rate
from valutatrade_hub.logging_config import setup_logging


def print_help() -> None:
    """Печатает список доступных команд."""
    print("Доступные команды:")
    print("  register --username <имя> --password <пароль>")
    print("  login --username <имя> --password <пароль>")
    print("  show-portfolio [--base <валюта>]")
    print("  buy --currency <код> --amount <число>")
    print("  sell --currency <код> --amount <число>")
    print("  get-rate --from <код> --to <код>")
    print("  help, exit")


def parse_options(tokens: list[str]) -> dict:
    """Превращает ['--username', 'alice'] в {'username': 'alice'}."""
    options = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and index + 1 < len(tokens):
            options[token[2:]] = tokens[index + 1]
            index += 2
        else:
            raise ValueError(f"Неверный аргумент '{token}'")
    return options


def require_option(options: dict, name: str) -> str:
    """Возвращает значение аргумента или сообщает, что он не указан."""
    if name not in options:
        raise ValueError(f"Не указан аргумент --{name}")
    return options[name]


def parse_amount(text: str) -> float:
    """Превращает текст в число или сообщает об ошибке."""
    try:
        return float(text)
    except ValueError:
        raise ValueError("'amount' должен быть положительным числом")


def handle_register(options: dict) -> None:
    """Команда register."""
    username = require_option(options, "username")
    password = require_option(options, "password")
    user = register_user(username, password)
    print(
        f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {user.username} --password ****"
    )


def handle_login(options: dict) -> None:
    """Команда login."""
    username = require_option(options, "username")
    password = require_option(options, "password")
    user = login_user(username, password)
    print(f"Вы вошли как '{user.username}'")


def handle_show_portfolio(options: dict) -> None:
    """Команда show-portfolio."""
    data = show_portfolio(options.get("base", BASE_CURRENCY))
    if not data["rows"]:
        print("У вас пока нет кошельков.")
        return
    base = data["base"]
    print(f"Портфель пользователя '{data['username']}' (база: {base}):")
    for row in data["rows"]:
        line = f"- {row['currency']}: {row['balance']:.4f}"
        print(f"{line}  → {row['value']:,.2f} {base}")
    print("-" * 33)
    print(f"ИТОГО: {data['total']:,.2f} {base}")


def handle_buy(options: dict) -> None:
    """Команда buy."""
    currency = require_option(options, "currency")
    amount = parse_amount(require_option(options, "amount"))
    result = buy_currency(currency, amount)
    code = result["currency"]
    print(
        f"Покупка выполнена: {result['amount']:.4f} {code} "
        f"по курсу {format_rate(result['rate'])} {BASE_CURRENCY}/{code}"
    )
    print("Изменения в портфеле:")
    print(f"- {code}: было {result['before']:.4f} → стало {result['after']:.4f}")
    print(f"Оценочная стоимость покупки: {result['cost']:,.2f} {BASE_CURRENCY}")


def handle_sell(options: dict) -> None:
    """Команда sell."""
    currency = require_option(options, "currency")
    amount = parse_amount(require_option(options, "amount"))
    result = sell_currency(currency, amount)
    code = result["currency"]
    print(
        f"Продажа выполнена: {result['amount']:.4f} {code} "
        f"по курсу {format_rate(result['rate'])} {BASE_CURRENCY}/{code}"
    )
    print("Изменения в портфеле:")
    print(f"- {code}: было {result['before']:.4f} → стало {result['after']:.4f}")
    print(f"Оценочная выручка: {result['revenue']:,.2f} {BASE_CURRENCY}")


def handle_get_rate(options: dict) -> None:
    """Команда get-rate."""
    from_code = require_option(options, "from").strip().upper()
    to_code = require_option(options, "to").strip().upper()
    data = get_rate(from_code, to_code)
    updated = data["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
    rate_text = format_rate(data["rate"])
    print(f"Курс {from_code}→{to_code}: {rate_text} (обновлено: {updated})")
    reverse_text = format_rate(1 / data["rate"])
    print(f"Обратный курс {to_code}→{from_code}: {reverse_text}")


def handle_help(options: dict) -> None:
    """Команда help."""
    print_help()


HANDLERS = {
    "register": handle_register,
    "login": handle_login,
    "show-portfolio": handle_show_portfolio,
    "buy": handle_buy,
    "sell": handle_sell,
    "get-rate": handle_get_rate,
    "help": handle_help,
}


def run() -> None:
    """Главный цикл: читает команды и вызывает нужные обработчики."""
    setup_logging()
    print_help()
    while True:
        line = input(">>> ").strip()
        if not line:
            continue
        try:
            tokens = shlex.split(line)
            command = tokens[0]
            if command == "exit":
                break
            handler = HANDLERS.get(command)
            if handler is None:
                print(f"Неизвестная команда '{command}'. Введите help.")
                continue
            handler(parse_options(tokens[1:]))
        except InsufficientFundsError as error:
            print(error)
        except CurrencyNotFoundError as error:
            codes = ", ".join(CURRENCIES)
            print(f"{error}. Поддерживаемые коды: {codes}")
        except ApiRequestError as error:
            print(f"{error}. Повторите попытку позже или проверьте сеть.")
        except ValueError as error:
            print(error)