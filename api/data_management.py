import logging
from . import config
# Обратите внимание на относительный импорт или настройку PYTHONPATH, если запускать не из корня
from .data_processing import load_and_process_json_files, OzonDataProcessor, WildberriesDataProcessor, BaseDataProcessor
from .vector_store import ingest_data_to_chroma

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ingest_from_folder(folder_path: str, source_type: str):
    """Загружает, обрабатывает JSON из папки в соответствии с source_type и индексирует в ChromaDB."""
    logging.info(f"Starting data ingestion process from folder: {folder_path} for source: {source_type}")

    processor: BaseDataProcessor
    if source_type.lower() == "ozon":
        processor = OzonDataProcessor()
    elif source_type.lower() == "wildberries":
        processor = WildberriesDataProcessor()
    else:
        logging.error(f"Unsupported source_type: {source_type}. Cannot select a data processor.")
        return False

    # 1. Загрузка и обработка JSON файлов с использованием выбранного процессора
    logging.info(f"Loading and processing data from: {folder_path} using {source_type} processor.")
    processed_data = load_and_process_json_files(folder_path, processor)

    if not processed_data:
        logging.warning(f"No data was processed from {folder_path} for source {source_type}. Check folder and JSON files.")
        # Возвращаем True, так как это не критическая ошибка самого процесса, а отсутствие данных
        return True 

    # 2. Индексация данных в ChromaDB
    # Важно: ingest_data_to_chroma может потребовать доработки для разных коллекций/фильтрации по source, 
    # если данные Ozon и WB должны храниться раздельно или иметь разные схемы в ChromaDB.
    # Пока предполагается, что metadata["source"] будет достаточно для различения.
    logging.info(f"Ingesting {len(processed_data)} processed documents for {source_type} into ChromaDB...")
    try:
        ingest_data_to_chroma(processed_data)
        logging.info(f"Data ingestion for {source_type} from folder finished successfully.")
        return True
    except Exception as e:
        logging.error(f"Failed to ingest data for {source_type} into ChromaDB: {e}", exc_info=True)
        return False

# Сюда можно будет добавить другие функции, например:
# def ingest_single_product(product_data: dict, source_type: str):
#     """Обрабатывает и индексирует данные одного продукта указанного типа."""
#     processor: BaseDataProcessor
#     if source_type.lower() == "ozon":
#         processor = OzonDataProcessor()
#     elif source_type.lower() == "wildberries":
#         processor = WildberriesDataProcessor()
#     else:
#         logging.error(f"Unsupported source_type: {source_type} for single product ingestion.")
#         return
#     
#     # ... логика обработки одного объекта с использованием processor ...
#     # base_product_id = processor.get_product_id(product_data, "single_ingest")
#     # main_text = processor.format_main_product_info(product_data)
#     # ... и т.д. ...
#     # if main_text:
#     #     main_metadata = processor.create_main_chunk_metadata(product_data, base_product_id)
#     #     ingest_data_to_chroma([{"id": base_product_id + "_main", "document": main_text, "metadata": main_metadata}])
#     pass 