# ValutaTrade Hub — валютный кошелёк

Консольное приложение, которое имитирует работу валютного кошелька: можно зарегистрироваться, войти, купить и продать валюту, посмотреть портфель и узнать курс. Данные хранятся в JSON-файлах, действия пишутся в лог.

## Возможности

- регистрация и вход пользователей (пароли хранятся в виде хеша с солью);
- портфель с кошельками в разных валютах (фиатные и криптовалюты);
- покупка и продажа валюты за USD;
- просмотр портфеля и его общей стоимости в выбранной валюте;
- получение курса одной валюты к другой с кешем (по умолчанию 5 минут);
- Parser Service: загрузка реальных курсов из CoinGecko и ExchangeRate-API, история измерений и планировщик;
- логирование операций покупки и продажи с ротацией файлов;
- свои исключения и понятные сообщения об ошибках.

## Структура проекта

```
finalproject_belyaeva_26-555/
├── data/                       # JSON-«база данных»
│   ├── users.json
│   ├── portfolios.json
│   ├── rates.json              # актуальный кеш курсов для Core Service
│   └── exchange_rates.json     # история измерений Parser Service
├── logs/                       # создаётся при запуске (actions.log, parser.log)
├── valutatrade_hub/
│   ├── logging_config.py       # настройка логов
│   ├── decorators.py           # декоратор @log_action
│   ├── core/
│   │   ├── currencies.py       # Currency, FiatCurrency, CryptoCurrency, get_currency
│   │   ├── exceptions.py       # свои исключения
│   │   ├── models.py           # User, Wallet, Portfolio
│   │   ├── usecases.py         # бизнес-логика
│   │   └── utils.py            # вспомогательные функции
│   ├── infra/
│   │   ├── settings.py         # Singleton SettingsLoader
│   │   └── database.py         # Singleton DatabaseManager
│   ├── parser_service/
│   │   ├── config.py           # настройки парсера (URL, списки валют, ключ из env)
│   │   ├── api_clients.py      # клиенты CoinGecko и ExchangeRate-API
│   │   ├── updater.py          # RatesUpdater: общий процесс обновления
│   │   ├── storage.py          # запись истории и снимка курсов
│   │   └── scheduler.py        # периодическое обновление
│   └── cli/
│       └── interface.py        # консольные команды
├── main.py
├── pyproject.toml
└── README.md
```

## Установка

Нужны Python 3.12+ и [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/aksiniyabelyaeva-oss/finalproject_belyaeva_26-555.git
cd finalproject_belyaeva_26-555
uv sync
```

## Запуск

```
uv run project
```

или

```
uv run python main.py
```

## Команды

| Команда | Что делает |
|---|---|
| `register --username <имя> --password <пароль>` | создаёт пользователя (пароль не короче 4 символов) |
| `login --username <имя> --password <пароль>` | вход в систему |
| `show-portfolio [--base <валюта>]` | показывает кошельки и итог (по умолчанию в USD) |
| `buy --currency <код> --amount <число>` | покупка валюты за USD |
| `sell --currency <код> --amount <число>` | продажа валюты за USD |
| `get-rate --from <код> --to <код>` | курс одной валюты к другой |
| `update-rates [--source coingecko\|exchangerate]` | обновляет курсы через Parser Service |
| `show-rates [--currency <код>] [--top <N>] [--base <код>]` | показывает курсы из кеша |
| `schedule-rates [--interval <секунды>]` | обновляет курсы по расписанию до Ctrl+C |
| `help`, `exit` | справка и выход |

Покупка USD (`buy --currency USD ...`) пополняет доллары. Покупка других валют списывает USD, поэтому сначала нужно пополнить USD-кошелёк.

### Пример сессии

```
>>> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****
>>> login --username alice --password 1234
Вы вошли как 'alice'
>>> buy --currency USD --amount 5000
>>> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2,966.86 USD
>>> show-portfolio
Портфель пользователя 'alice' (база: USD):
- USD: 2033.1395  → 2,033.14 USD
- BTC: 0.0500  → 2,966.86 USD
---------------------------------
ИТОГО: 5,000.00 USD
>>> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001685 (обновлено: 2025-10-09 00:03:22)
Обратный курс BTC→USD: 59337.21
```

## Поддерживаемые валюты

Валюты описаны классами `FiatCurrency` и `CryptoCurrency` (общий родитель — абстрактный класс `Currency`). Метод `get_display_info()` у каждого вида работает по-своему:

```
[FIAT] USD — US Dollar (Issuing: United States)
[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)
```

Доступные коды: `USD`, `EUR`, `RUB`, `GBP`, `BTC`, `ETH`, `SOL`. Новые валюты добавляются в реестр `CURRENCIES` в `currencies.py`.

## Ошибки

| Исключение | Когда возникает | Что видит пользователь |
|---|---|---|
| `InsufficientFundsError` | не хватает средств при продаже или покупке | `Недостаточно средств: доступно 0.0400 BTC, требуется 0.0500 BTC` |
| `CurrencyNotFoundError` | неизвестный код валюты | `Неизвестная валюта 'XYZ'. Поддерживаемые коды: USD, EUR, RUB, GBP, BTC, ETH, SOL` |
| `ApiRequestError` | сбой получения курса | `Ошибка при обращении к внешнему API: ... Повторите попытку позже или проверьте сеть.` |

Остальные ошибки ввода (пустое имя, короткий пароль, неверная сумма и т. д.) выводятся понятными сообщениями.

## Настройки

Параметры лежат в `pyproject.toml`, в секции `[tool.valutatrade]`. Их загружает класс-одиночка `SettingsLoader`.

| Ключ | Значение по умолчанию | Что означает |
|---|---|---|
| `data_dir` | `data` | папка с JSON-файлами |
| `rates_ttl_seconds` | `300` | время жизни кеша курсов (секунды) |
| `base_currency` | `USD` | базовая валюта |
| `log_dir` | `logs` | папка с логами |
| `log_file` | `actions.log` | имя файла лога операций |
| `parser_log_file` | `parser.log` | имя файла лога Parser Service |
| `history_file` | `exchange_rates.json` | файл истории курсов |
| `parser_interval_seconds` | `3600` | интервал автообновления курсов (секунды) |
| `log_level` | `INFO` | уровень логирования (`DEBUG` для отладки) |

## Хранение данных

Доступ к файлам идёт через класс-одиночку `DatabaseManager`:

- `data/users.json` — пользователи (id, имя, хеш пароля, соль, дата регистрации);
- `data/portfolios.json` — портфели и балансы кошельков;
- `data/rates.json` — кеш курсов с временем обновления.

## Логирование

Операции `buy` и `sell` пишет в `logs/actions.log` декоратор `@log_action`. Ошибки в лог записываются, но не скрываются: исключение выбрасывается дальше. Пример:

```
INFO 2025-10-09T12:05:22 BUY user='alice' currency='BTC' amount=0.0500 rate=59337.21 base='USD' result=OK balance=0.0000->0.0500
INFO 2025-10-09T12:06:10 SELL user='alice' currency='ETH' amount=1.0000 result=ERROR error_type=ValueError error_message="..."
```

Файл ротируется при достижении 1 МБ (хранятся 3 старые копии).

## Parser Service и курсы валют

Отдельный модуль `valutatrade_hub/parser_service` собирает курсы из двух открытых API:

- **CoinGecko** — криптовалюты (BTC, ETH, SOL), ключ не нужен;
- **ExchangeRate-API** — фиатные валюты (EUR, GBP, RUB), нужен бесплатный ключ.

### API-ключ

Ключ ExchangeRate-API берётся из переменной окружения `EXCHANGERATE_API_KEY` и не хранится в коде или репозитории.

Windows (PowerShell), только для текущего окна:

```
$env:EXCHANGERATE_API_KEY = "ваш_ключ"
```

Чтобы сохранить ключ навсегда: `setx EXCHANGERATE_API_KEY "ваш_ключ"`, затем перезапустите терминал.

### Как это работает

1. `update-rates` опрашивает клиентов. Если один источник недоступен, ошибка пишется в `logs/parser.log`, а остальные источники продолжают работать.
2. Каждое измерение дописывается в историю `data/exchange_rates.json` с уникальным `id` (`BTC_USD_2025-10-10T12:00:00Z`), дубликаты не добавляются.
3. Актуальные значения сохраняются в `data/rates.json` (по одной последней записи на пару) в формате:

```
{
  "pairs": {
    "EUR_USD": {"rate": 1.0786, "updated_at": "2025-10-10T12:00:00Z", "source": "ExchangeRate-API"},
    "BTC_USD": {"rate": 59337.21, "updated_at": "2025-10-10T12:00:00Z", "source": "CoinGecko"}
  },
  "last_refresh": "2025-10-10T12:00:01Z"
}
```

4. Файлы записываются атомарно (временный файл, затем замена).
5. Команды `get-rate`, `buy`, `sell` и `show-portfolio` читают кеш. Если данные старше `rates_ttl_seconds`, курсы автоматически обновляются. Если обновить не удалось, выводится ошибка `ApiRequestError`.

ExchangeRate-API отдаёт курсы вида «сколько единиц валюты за 1 USD», поэтому для пары `EUR_USD` сохраняется обратное значение.

### Примеры

```
>>> update-rates
INFO: Starting rates update...
INFO: Fetching from CoinGecko... OK (3 rates)
INFO: Fetching from ExchangeRate-API... OK (3 rates)
INFO: Writing 6 rates to data/rates.json...
INFO: Update finished: 6 rates, 0 errors
Update successful. Total rates updated: 6. Last refresh: 2025-10-10T15:30:00Z
>>> show-rates --top 2
Rates from cache (updated at 2025-10-10T15:30:00Z):
- BTC_USD: 59337.21
- ETH_USD: 3720.00
>>> show-rates --currency RUB
Rates from cache (updated at 2025-10-10T15:30:00Z):
- RUB_USD: 0.01015744
```

Если кеш пуст, `show-rates` предлагает выполнить `update-rates`. Если неизвестный источник или валюта, выводится понятное сообщение.

## Проверка кода

```
uv run ruff check .
```