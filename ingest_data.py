import logging
import sys
import os
import argparse # For command-line arguments

# Добавляем корневую папку проекта в PYTHONPATH, чтобы найти api
# Это нужно, если запускать ingest_data.py напрямую из корня
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from api import config # Импортируем конфиг из api
from api.data_management import ingest_from_folder # Импортируем функцию

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_ingestion_for_source(source_type: str):
    """Запускает процесс индексации данных для указанного источника."""
    logging.info(f"--- Starting Data Ingestion Trigger for source: {source_type} ---")

    folder_to_ingest = ""
    if source_type.lower() == "ozon":
        folder_to_ingest = getattr(config, 'OZON_DATA_FOLDER', config.DATA_FOLDER)
        logging.info(f"Using Ozon data folder: {folder_to_ingest}")
    elif source_type.lower() == "wildberries":
        folder_to_ingest = getattr(config, 'WILDBERRIES_DATA_FOLDER', None)
        if not folder_to_ingest:
            logging.error("WILDBERRIES_DATA_FOLDER is not configured in api/config.py. Cannot ingest Wildberries data.")
            sys.exit(1)
        logging.info(f"Using Wildberries data folder: {folder_to_ingest}")
    else:
        logging.error(f"Invalid source_type: {source_type}. Choose 'ozon' or 'wildberries'.")
        sys.exit(1)

    success = ingest_from_folder(folder_to_ingest, source_type.lower())

    if success:
        logging.info(f"--- Data Ingestion for {source_type} Finished Successfully ---")
    else:
        logging.error(f"--- Data Ingestion for {source_type} Failed --- Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run data ingestion for a specified source (Ozon or Wildberries).")
    parser.add_argument(
        "source", 
        type=str, 
        choices=["ozon", "wildberries"], 
        help="The data source to ingest ('ozon' or 'wildberries')"
    )
    args = parser.parse_args()

    run_ingestion_for_source(args.source)