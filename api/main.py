import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional # Добавляем типы
# Импортируем логику RAG и управления данными
from .rag_logic import get_rag_response
from .data_management import ingest_from_folder
from . import config # Импортируем config для доступа к DATA_FOLDER

# Настройка логирования для API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ozon RAG Chat API",
    description="API для чата с RAG-ассистентом Ozon и управления данными", # Обновили описание
    version="1.2.0" # Обновим версию
)

# Модель для входящего запроса - добавляем history
class ChatRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, str]]] = None # История опциональна

# Модель для ответа
class ChatResponse(BaseModel):
    answer: str

class IngestResponse(BaseModel):
    status: str
    message: str

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Принимает запрос пользователя и историю чата, возвращает ответ RAG-ассистента."""
    logger.info(f"Received chat request with query: {request.query}")
    if request.history:
        logger.info(f"Received history with {len(request.history)} messages.")

    try:
        # Передаем и запрос, и историю в логику RAG
        response_text = get_rag_response(request.query, request.history)
        logger.info(f"Generated response: {response_text[:100]}...")
        return ChatResponse(answer=response_text)
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ----- НОВЫЙ ЭНДПОИНТ ДЛЯ ИНДЕКСАЦИИ -----
@app.post("/ingest", response_model=IngestResponse)
def ingest_endpoint():
    """Запускает процесс индексации данных из папки, указанной в config.DATA_FOLDER."""
    logger.info(f"Received request to start ingestion from folder: {config.DATA_FOLDER}")
    try:
        success = ingest_from_folder(config.DATA_FOLDER)
        if success:
            logger.info("Ingestion process completed successfully.")
            return IngestResponse(status="success", message="Индексация данных успешно завершена.")
        else:
            logger.warning("Ingestion process finished with issues (e.g., no new data found or partial failure).")
            return IngestResponse(status="warning", message="Процесс индексации завершен, но возможны проблемы (нет новых данных или частичная ошибка). Проверьте логи API.")
    except Exception as e:
        logger.error(f"Ingestion process failed critically: {e}", exc_info=True)
        # Возвращаем ошибку сервера, если функция вызвала исключение
        raise HTTPException(status_code=500, detail=f"Критическая ошибка во время индексации: {e}")
# ----- КОНЕЦ НОВОГО ЭНДПОИНТА -----

# Дополнительно: endpoint для проверки работы API
@app.get("/")
def read_root():
    return {"message": "Ozon RAG Chat API is running"}

# Если нужно запускать напрямую (хотя обычно используется uvicorn)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000) 