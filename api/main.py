import logging
from fastapi import FastAPI, HTTPException, Body
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
    title="RAG Chat API",
    description="API для чата с RAG-ассистентами (Ozon, Wildberries) и управления данными",
    version="1.3.0" # Обновим версию
)

# Модель для входящего запроса - добавляем history и expert_type
class ChatRequest(BaseModel):
    query: str
    expert_type: str = "ozon" # "ozon" or "wildberries", defaults to "ozon"
    history: Optional[List[Dict[str, str]]] = None # История опциональна

# Модель для ответа
class ChatResponse(BaseModel):
    answer: str

# --- Ingestion Request and Response Models ---
class IngestRequest(BaseModel):
    source: str # "ozon" or "wildberries"

class IngestResponse(BaseModel):
    status: str
    message: str
    source_ingested: Optional[str] = None

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """Принимает запрос, тип эксперта (ozon/wildberries) и историю, возвращает ответ RAG-ассистента."""
    logger.info(f"Received chat request for expert_type '{request.expert_type}' with query: {request.query}")
    if request.history:
        logger.info(f"Received history with {len(request.history)} messages.")

    if request.expert_type.lower() not in ["ozon", "wildberries"]:
        raise HTTPException(status_code=400, detail="Invalid expert_type. Must be 'ozon' or 'wildberries'.")

    try:
        response_text = get_rag_response(request.query, request.expert_type.lower(), request.history)
        logger.info(f"Generated response for {request.expert_type}: {response_text[:100]}...")
        return ChatResponse(answer=response_text)
    except ValueError as ve:
        logger.error(f"ValueError processing chat request: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing chat request for {request.expert_type}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error for {request.expert_type}")

# ----- НОВЫЙ ЭНДПОИНТ ДЛЯ ИНДЕКСАЦИИ -----
@app.post("/ingest", response_model=IngestResponse)
def ingest_endpoint(request: IngestRequest):
    """Запускает процесс индексации данных для указанного источника (ozon/wildberries)."""
    source_type = request.source.lower()
    logger.info(f"Received request to start ingestion for source: {source_type}")

    folder_to_ingest = ""
    if source_type == "ozon":
        # Пытаемся получить OZON_DATA_FOLDER из конфига
        folder_to_ingest = getattr(config, 'OZON_DATA_FOLDER', None)
        if not folder_to_ingest:
            logger.error("OZON_DATA_FOLDER is not configured in api/config.py")
            raise HTTPException(status_code=500, detail="Ozon data folder not configured.")
    elif source_type == "wildberries":
        folder_to_ingest = getattr(config, 'WILDBERRIES_DATA_FOLDER', None)
        if not folder_to_ingest:
            logger.error("WILDBERRIES_DATA_FOLDER is not configured in api/config.py")
            raise HTTPException(status_code=500, detail="Wildberries data folder not configured.")
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Must be 'ozon' or 'wildberries'.")

    logger.info(f"Target folder for ingestion ({source_type}): {folder_to_ingest}")

    try:
        success = ingest_from_folder(folder_to_ingest, source_type)
        if success:
            logger.info(f"Ingestion process for {source_type} completed successfully.")
            return IngestResponse(status="success", message=f"Индексация данных для '{source_type}' успешно завершена.", source_ingested=source_type)
        else:
            # Это может означать как ошибку внутри ingest_from_folder, так и просто отсутствие новых файлов (где ingest_from_folder вернет True, но тут мы хотим warning)
            # data_management.ingest_from_folder теперь возвращает False только при критической ошибке.
            # Если ingest_from_folder вернул True, но processed_data был пуст - это успех без новых данных.
            # Если ingest_from_folder вернул False - это ошибка.
            # Разделим логику: ingest_from_folder теперь более точно отражает свой успех.
            # Здесь мы должны вернуть warning если success=True но нет новых данных, но это сложно определить отсюда.
            # Пока что, если success=False, это error. Если True, то success или warning (нужно доработать для warning).
            # Однако, ingest_from_folder теперь возвращает False только при ошибке. Если нет данных, вернет True.
            # Поэтому, если success=False, это точно ошибка с точки зрения API.
            logger.warning(f"Ingestion process for {source_type} finished with issues or failed.")
            return IngestResponse(status="error", message=f"Процесс индексации для '{source_type}' завершился с ошибками. Проверьте логи API.", source_ingested=source_type)

    except HTTPException: # Перехватываем HTTP исключения, чтобы не попасть в общий Exception
        raise
    except Exception as e:
        logger.error(f"Ingestion process for {source_type} failed critically: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Критическая ошибка во время индексации для '{source_type}': {e}")
# ----- КОНЕЦ НОВОГО ЭНДПОИНТА -----

# Дополнительно: endpoint для проверки работы API
@app.get("/")
def read_root():
    return {"message": "RAG Chat API is running (supporting Ozon and Wildberries)"}

# Если нужно запускать напрямую (хотя обычно используется uvicorn)
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000) 