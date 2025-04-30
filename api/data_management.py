import logging
from . import config
# Обратите внимание на относительный импорт или настройку PYTHONPATH, если запускать не из корня
from .data_processing import load_and_process_json_files
from .vector_store import ingest_data_to_chroma

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ingest_from_folder(folder_path: str):
    """Загружает, обрабатывает JSON из папки и индексирует в ChromaDB."""
    logging.info(f"Starting data ingestion process from folder: {folder_path}")

    # 1. Загрузка и обработка JSON файлов
    logging.info(f"Loading and processing data from: {folder_path}")
    processed_data = load_and_process_json_files(folder_path)

    if not processed_data:
        logging.warning(f"No data was processed from {folder_path}. Check folder and JSON files.")
        return False # Возвращаем False при неудаче

    # 2. Индексация данных в ChromaDB
    logging.info(f"Ingesting {len(processed_data)} processed documents into ChromaDB...")
    try:
        ingest_data_to_chroma(processed_data)
        logging.info("Data ingestion from folder finished successfully.")
        return True # Возвращаем True при успехе
    except Exception as e:
        logging.error(f"Failed to ingest data into ChromaDB: {e}", exc_info=True)
        return False # Возвращаем False при ошибке индексации

# Сюда можно будет добавить другие функции, например:
# def ingest_single_product(product_data: dict):
#     """Обрабатывает и индексирует данные одного продукта."""
#     # ... логика обработки одного объекта ...
#     formatted_text = format_product_info(product_data)
#     if formatted_text:
#         product_id = ... # Генерация ID
#         metadata = ... # Генерация метаданных
#         ingest_data_to_chroma([{"id": product_id, "document": formatted_text, "metadata": metadata}])
#     pass 