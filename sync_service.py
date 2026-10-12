import configparser
import logging
import os
import sys
import time
from datetime import datetime

from yandex_disk import YandexDisk


def read_config(path="config.ini"):
    """Читает параметры из config.ini."""
    config = configparser.ConfigParser()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл конфигурации {path} не найден.")
    config.read(path, encoding="utf-8")
    return config["Settings"]


def setup_logging(log_file):
    """Настраивает логирование в файл."""
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        # encoding="utf-8",
    )


def validate_settings(settings):
    """Проверяет корректность параметров запуска."""
    local_folder = settings.get("local_folder", "")
    token = settings.get("token", "")

    if not os.path.isdir(local_folder):
        raise NotADirectoryError(
            f"Синхронизируемая папка '{local_folder}' не существует."
        )
    if not token or token == "YOUR_TOKEN_HERE":
        raise ValueError("В config.ini не задан корректный токен доступа.")

    sync_period = settings.getint("sync_period", fallback=10)
    if sync_period <= 0:
        raise ValueError("Период синхронизации должен быть больше нуля.")

    return local_folder, token, sync_period


def get_local_files(local_folder):
    """Возвращает словарь {имя_файла: mtime} для файлов в папке."""
    files = {}
    for name in os.listdir(local_folder):
        full_path = os.path.join(local_folder, name)
        if os.path.isfile(full_path):
            files[name] = os.path.getmtime(full_path)
    return files


def upload_file(storage, local_folder, filename):
    """Загружает новый файл в облако."""
    full_path = os.path.join(local_folder, filename)
    try:
        storage.load(full_path)
        logging.info("Файл %s успешно записан.", filename)
    except Exception as error:
        logging.error("Файл %s не записан. %s", filename, error)


def update_file(storage, local_folder, filename):
    """Перезаписывает изменённый файл в облаке."""
    full_path = os.path.join(local_folder, filename)
    try:
        storage.reload(full_path)
        logging.info("Файл %s успешно перезаписан.", filename)
    except Exception as error:
        logging.error("Файл %s не перезаписан. %s", filename, error)


def remove_file(storage, filename):
    """Удаляет файл из облака."""
    try:
        storage.delete(filename)
        logging.info("Файл %s успешно удалён.", filename)
    except Exception as error:
        logging.error("Файл %s не удалён. %s", filename, error)


def sync_once(storage, local_folder, previous_state):
    """Одна итерация синхронизации. Возвращает актуальное состояние."""
    current_state = get_local_files(local_folder)
    remote_files = safe_get_remote(storage)

    added = current_state.keys() - previous_state.keys()
    removed = previous_state.keys() - current_state.keys()
    changed = {
        name
        for name in current_state.keys() & previous_state.keys()
        if current_state[name] != previous_state[name]
    }

    for name in added:
        upload_file(storage, local_folder, name)

    for name in changed:
        update_file(storage, local_folder, name)

    for name in removed:
        remove_file(storage, name)

    # Удаляем из облака то, чего нет локально (первичная синхронизация).
    for name in remote_files.keys() - current_state.keys():
        if name not in removed:
            remove_file(storage, name)

    return current_state


def safe_get_remote(storage):
    """Безопасно получает список файлов в облаке."""
    try:
        return storage.get_info()
    except Exception as error:
        logging.error("Не удалось получить список файлов из облака. %s", error)
        return {}


def main():
    try:
        settings = read_config()
        local_folder, token, sync_period = validate_settings(settings)
    except Exception as error:
        print(f"Ошибка запуска: {error}")
        sys.exit(1)

    setup_logging(settings.get("log_file", "sync.log"))
    logging.info(
        "Программа синхронизации файлов начинает работу с директорией %s.",
        os.path.abspath(local_folder),
    )

    storage = YandexDisk(token, settings.get("remote_folder", "backup"))

    # Первичная синхронизация: пустое предыдущее состояние.
    previous_state = sync_once(storage, local_folder, {})

    while True:
        time.sleep(sync_period)
        previous_state = sync_once(storage, local_folder, previous_state)


if __name__ == "__main__":
    main()
