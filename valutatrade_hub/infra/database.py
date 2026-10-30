import json
import os

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Singleton: единая точка доступа к JSON-хранилищу.

    Реализован через __new__ так же, как SettingsLoader: это просто и читаемо.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
        return cls._instance

    def get_path(self, collection: str) -> str:
        """Собирает путь к файлу коллекции (users, portfolios, rates, history)."""
        data_dir = self._settings.get("data_dir")
        file_name = self._settings.get(f"{collection}_file")
        return os.path.join(data_dir, file_name)

    def load(self, collection: str, default):
        """Читает коллекцию; если файла нет, возвращает default."""
        try:
            with open(self.get_path(collection), encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return default

    def save(self, collection: str, data) -> None:
        """Записывает коллекцию в файл атомарно: временный файл, затем замена."""
        path = self.get_path(collection)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        os.replace(temp_path, path)
