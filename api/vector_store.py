import chromadb
import logging
from chromadb.utils import embedding_functions
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import os

from . import config # ИЗМЕНЕНИЕ: Относительный импорт

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Инициализация ChromaDB и Embedding Function ---
# Используем SentenceTransformerEmbeddingFunction из ChromaDB > 0.5.0
# Это гарантирует, что та же модель используется при индексации и запросе
chroma_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=config.EMBEDDING_MODEL_NAME,
    # device="cuda" # Раскомментируйте, если есть GPU и хотите его использовать
)

# Создаем или подключаемся к персистентной базе
chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

# Получаем или создаем коллекцию с указанной функцией эмбеддинга
try:
    collection = chroma_client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        embedding_function=chroma_ef,
        metadata={"hnsw:space": "cosine"} # Рекомендуется для эмбеддингов Sentence Transformers
    )
    logging.info(f"ChromaDB collection '{config.CHROMA_COLLECTION_NAME}' ready.")
except Exception as e:
    logging.error(f"Failed to get or create ChromaDB collection: {e}", exc_info=True)
    # Можно добавить выход из программы или альтернативную логику
    raise

def ingest_data_to_chroma(processed_data: List[Dict[str, str]]):
    """Добавляет обработанные данные в коллекцию ChromaDB."""
    if not processed_data:
        logging.warning("No processed data provided for ingestion.")
        return

    ids = [item["id"] for item in processed_data]
    documents = [item["document"] for item in processed_data]
    metadatas = [item["metadata"] for item in processed_data]

    # Проверка существующих ID, чтобы избежать дублирования (опционально, но полезно)
    try:
        existing_items = collection.get(ids=ids)['ids']
        new_ids = []
        new_documents = []
        new_metadatas = []

        for i, doc_id in enumerate(ids):
            if doc_id not in existing_items:
                new_ids.append(doc_id)
                new_documents.append(documents[i])
                new_metadatas.append(metadatas[i])
            else:
                 logging.debug(f"Document with ID {doc_id} already exists. Skipping.")

        if not new_ids:
            logging.info("No new documents to add to ChromaDB.")
            return

        logging.info(f"Adding {len(new_ids)} new documents to ChromaDB...")
        collection.add(
            ids=new_ids,
            documents=new_documents,
            metadatas=new_metadatas
        )
        logging.info(f"Successfully added {len(new_ids)} documents to ChromaDB.")

    except Exception as e:
        logging.error(f"Error during ChromaDB ingestion: {e}", exc_info=True)

# Функция поиска (хотя RetrieveUserProxyAgent будет делать это сам)
# Может быть полезна для отладки
def search_in_chroma(query_text: str, n_results: int = config.RETRIEVAL_NUM_RESULTS) -> List[str]:
    """Выполняет поиск в ChromaDB."""
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents"] # Получаем только тексты документов
        )
        logging.info(f"Retrieved {len(results['documents'][0])} documents for query: '{query_text}'")
        return results['documents'][0] if results and results['documents'] else []
    except Exception as e:
        logging.error(f"Error during ChromaDB search: {e}", exc_info=True)
        return []