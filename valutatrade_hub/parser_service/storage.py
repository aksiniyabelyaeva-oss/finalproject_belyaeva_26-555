from valutatrade_hub.core.utils import parse_timestamp
from valutatrade_hub.infra.database import DatabaseManager


class RatesStorage:
    """Чтение и запись истории измерений и актуального снимка курсов."""

    def __init__(self):
        self._db = DatabaseManager()

    @property
    def rates_path(self) -> str:
        """Путь к файлу с актуальным снимком курсов."""
        return self._db.get_path("rates")

    def append_history(self, records: list[dict]) -> int:
        """Добавляет записи в историю, пропуская дубликаты по id."""
        history = self._db.load("history", [])
        known_ids = {item["id"] for item in history}
        new_records = [item for item in records if item["id"] not in known_ids]
        if new_records:
            self._db.save("history", history + new_records)
        return len(new_records)

    def update_snapshot(self, updates: dict, last_refresh: str) -> int:
        """Обновляет снимок курсов: запись заменяется, если она не старее текущей."""
        snapshot = self._db.load("rates", {})
        pairs = snapshot.get("pairs", {})
        updated = 0
        for pair, entry in updates.items():
            current = pairs.get(pair)
            new_time = parse_timestamp(entry["updated_at"])
            if current is None or new_time >= parse_timestamp(current["updated_at"]):
                pairs[pair] = entry
                updated += 1
        self._db.save("rates", {"pairs": pairs, "last_refresh": last_refresh})
        return updated
