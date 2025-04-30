import logging
import sys
import os

# Добавляем корневую папку проекта в PYTHONPATH, чтобы найти api
# Это нужно, если запускать ingest_data.py напрямую из корня
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from api import config # Импортируем конфиг из api
from api.data_management import ingest_from_folder # Импортируем функцию

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_main_ingestion():
    """Запускает процесс индексации данных из основной папки DATA_FOLDER."""
    logging.info("--- Starting Main Data Ingestion Trigger ---")

    success = ingest_from_folder(config.DATA_FOLDER)

    if success:
        logging.info("--- Main Data Ingestion Trigger Finished Successfully ---")
    else:
        logging.error("--- Main Data Ingestion Trigger Failed --- Check logs for details.")
        sys.exit(1) # Выход с ошибкой, если индексация не удалась

if __name__ == "__main__":
    # Этот скрипт теперь просто вызывает основную логику из api.data_management
    run_main_ingestion()