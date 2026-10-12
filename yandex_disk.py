import os
import requests


class YandexDisk:
    """Класс для работы с облачным хранилищем Яндекс Диск."""

    BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"

    def __init__(self, token, remote_folder):
        self.token = token
        self.remote_folder = remote_folder.strip("/")
        self.headers = {"Authorization": f"OAuth {self.token}"}

    def _params(self, path):
        return {"path": f"{self.remote_folder}/{path}".strip("/")}

    def get_info(self):
        """Возвращает словарь {имя_файла: {'size': ..., 'modified': ...}}."""
        params = {"path": self.remote_folder, "limit": 1000}
        response = requests.get(
            self.BASE_URL, headers=self.headers, params=params, timeout=10
        )
        response.raise_for_status()
        items = response.json().get("_embedded", {}).get("items", [])
        return {
            item["name"]: {
                "size": item.get("size"),
                "modified": item.get("modified"),
            }
            for item in items
            if item["type"] == "file"
        }

    def load(self, path):
        """Загружает новый файл в облако."""
        upload_url = self._get_upload_url(path)
        with open(path, "rb") as file:
            response = requests.put(upload_url, files={"file": file}, timeout=60)
        response.raise_for_status()

    def reload(self, path):
        """Перезаписывает существующий файл в облаке."""
        upload_url = self._get_upload_url(path, overwrite=True)
        with open(path, "rb") as file:
            response = requests.put(upload_url, files={"file": file}, timeout=60)
        response.raise_for_status()

    def delete(self, filename):
        """Удаляет файл из облака."""
        response = requests.delete(
            self.BASE_URL,
            headers=self.headers,
            params=self._params(filename),
            timeout=10,
        )
        response.raise_for_status()

    def _get_upload_url(self, path, overwrite=False):
        params = self._params(os.path.basename(path))
        params["overwrite"] = str(overwrite).lower()
        response = requests.get(
            f"{self.BASE_URL}/upload",
            headers=self.headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["href"]
    