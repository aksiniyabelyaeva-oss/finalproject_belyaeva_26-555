import shlex

from valutatrade_hub.core.usecases import login_user, register_user


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


def handle_help(options: dict) -> None:
    """Команда help."""
    print_help()


HANDLERS = {
    "register": handle_register,
    "login": handle_login,
    "help": handle_help,
}


def run() -> None:
    """Главный цикл: читает команды и вызывает нужные обработчики."""
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
        except ValueError as error:
            print(error)