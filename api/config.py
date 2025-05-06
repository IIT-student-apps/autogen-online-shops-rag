# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- Основные Настройки ---
DATA_FOLDER = "ozon_data"
CHROMA_PERSIST_DIR = "chroma_db"
CHROMA_COLLECTION_NAME = "ozon_products_v1"

# --- Настройки Моделей ---
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'

# --- Конфигурация LLM с использованием litellm для Google Gemini ---
LLM_CONFIG = {
    "config_list": [
        {
            "model": "gemini-1.5-flash-latest", # Используем имя модели без префикса
            "api_key": os.environ.get("GOOGLE_API_KEY"),
            "api_type": "google" # Явно указываем тип API
            # "base_url": None # Не нужно, litellm сам определит эндпоинт Google
        }
    ],
    "cache_seed": 42,
    "temperature": 0.5,
    # "timeout": 300, # Можно увеличить таймаут, если ответы приходят медленно
}

# --- Настройки RAG ---
RETRIEVAL_TASK_TYPE = "qa"
RETRIEVAL_NUM_RESULTS = 10