import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.utils import utc_timestamp
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("parser_service")


class RatesUpdater:
    """Координирует обновление курсов: опрос клиентов, объединение, сохранение."""

    def __init__(self, clients: list[BaseApiClient], storage: RatesStorage):
        self.clients = clients
        self.storage = storage

    def run_update(self, source: str | None = None) -> dict:
        """Обновляет курсы; сбой одного клиента не останавливает остальных."""
        steps: list[str] = []
        errors: list[str] = []
        records: list[dict] = []
        updates: dict = {}
        self._note(steps, logging.INFO, "Starting rates update...")

        for client in self.clients:
            if source is not None and client.key != source:
                continue
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                errors.append(f"{client.name}: {error.reason}")
                self._note(
                    steps,
                    logging.ERROR,
                    f"Failed to fetch from {client.name}: {error.reason}",
                )
                continue
            timestamp = utc_timestamp()
            for pair, rate in rates.items():
                from_code, to_code = pair.split("_")
                records.append(
                    {
                        "id": f"{pair}_{timestamp}",
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": client.name,
                        "meta": client.meta.get(pair, {}),
                    }
                )
                updates[pair] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": client.name,
                }
            self._note(
                steps,
                logging.INFO,
                f"Fetching from {client.name}... OK ({len(rates)} rates)",
            )

        last_refresh = utc_timestamp()
        if updates:
            self._note(
                steps,
                logging.INFO,
                f"Writing {len(updates)} rates to {self.storage.rates_path}...",
            )
            self.storage.append_history(records)
            self.storage.update_snapshot(updates, last_refresh)
        self._note(
            steps,
            logging.INFO,
            f"Update finished: {len(updates)} rates, {len(errors)} errors",
        )
        return {
            "total": len(updates),
            "errors": errors,
            "steps": steps,
            "last_refresh": last_refresh,
        }

    def _note(self, steps: list[str], level: int, message: str) -> None:
        """Пишет сообщение в лог и в список шагов для вывода пользователю."""
        steps.append(f"{logging.getLevelName(level)}: {message}")
        logger.log(level, message)
