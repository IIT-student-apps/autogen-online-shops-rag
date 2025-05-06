import autogen
import logging
from . import config
from .vector_store import search_in_chroma
from autogen import AssistantAgent, UserProxyAgent
from typing import List, Dict, Optional # Добавляем типы

# Подавляем подробные логи AutoGen
logging.getLogger("autogen").setLevel(logging.WARNING)

# --- Проверка конфигурации LLM ---
if not config.LLM_CONFIG["config_list"][0].get("api_key"):
    logging.error("API key for LLM is missing in config. Please set GOOGLE_API_KEY in .env.")
    # Вместо exit(1) вызываем исключение, чтобы FastAPI мог его обработать
    raise ValueError("API key for LLM is missing in config.")

# --- УБИРАЕМ ГЛОБАЛЬНУЮ ИНИЦИАЛИЗАЦИЮ АГЕНТОВ ---
# user_proxy = UserProxyAgent(...)
# ozon_expert = AssistantAgent(...)

# --- Переменные для хранения инициализированных агентов ---
_user_proxy = None
_ozon_expert = None

def _initialize_agents():
    """Инициализирует агентов при первом вызове."""
    global _user_proxy, _ozon_expert
    if _user_proxy is None:
        logging.info("Initializing UserProxyAgent...")
        _user_proxy = UserProxyAgent(
           name="UserProxy",
           human_input_mode="NEVER",
           max_consecutive_auto_reply=0,
           code_execution_config=False,
           llm_config=False
        )
        logging.info("UserProxyAgent initialized.")
    if _ozon_expert is None:
        logging.info("Initializing OzonExpert AssistantAgent...")
        _ozon_expert = AssistantAgent(
            name="OzonExpert",
            system_message=(
                "Ты - русскоязычный ИИ-ассистент, эксперт по товарам из интернет-магазина OZON.\n"
                "Тебе будет предоставлено сообщение в формате, которое может включать:\n"
                "[Недавняя история диалога (если есть)]\n\n"
                "Вопрос: [Текущий вопрос пользователя]\n\n"
                "Контекст:\n"
                "[Найденная информация о товарах]\n\n"
                "Ты отвечаешь на Текущий вопрос пользователя. В первую очередь используй предоставленный Контекст.\n"
                "Если Контекст релевантен, отвечай СТРОГО на его основе. Недавняя история диалога может помочь понять, о каком товаре из Контекста идет речь в Текущем вопросе, если он неясен сам по себе.\n"
                "Не придумывай информацию, которой нет в Контексте. Если Контекста для ответа недостаточно или он нерелевантен, или вопрос не связан с товарами OZON, вежливо сообщи об этом.\n"
                "Формулируй ответы четко, лаконично и по делу. Если в Контексте есть URL товара, укажи его в конце ответа.\n"
                "Не упоминай слова \"Контекст\" или \"предоставленная информация\" в своем ответе, просто давай ответ по существу, как будто продолжаешь диалог."
            ),
            llm_config=config.LLM_CONFIG,
        )
        logging.info("OzonExpert AssistantAgent initialized.")
    return _user_proxy, _ozon_expert

def get_rag_response(query: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Выполняет RAG поиск, учитывает историю и получает ответ от OzonExpert."""

    # --- Инициализация агентов (если еще не сделана) ---
    user_proxy, ozon_expert = _initialize_agents()
    # --- КОНЕЦ ИНИЦИАЛИЗАЦИИ ---

    # 1. RAG Поиск
    logging.info(f"--- Performing search for query: '{query}' ---")
    search_results = search_in_chroma(query, n_results=config.RETRIEVAL_NUM_RESULTS)
    # --- ЛОГИРОВАНИЕ РЕЗУЛЬТАТОВ ПОИСКА ---
    logging.debug(f"Search results from ChromaDB: {search_results}") 
    # --- КОНЕЦ ЛОГИРОВАНИЯ ---
    
    if search_results:
        # ИЗМЕНЕНИЕ: Извлекаем 'document' из каждого словаря перед join
        documents_texts = [result.get("document", "") for result in search_results if result.get("document")]
        context_str = "\n\n---\n\n".join(documents_texts)
        # logging.info(f"Search found {len(search_results)} results.") # Можно убрать или изменить, т.к. search_results - это словари
        logging.info(f"Formatted context from {len(documents_texts)} retrieved documents.") # Более точный лог
        context_section = f"Контекст:\n{context_str}"
    else:
        logging.warning("Search found NO results.")
        context_section = "Контекст:\n[Контекст не найден]"

    # 2. Форматирование ИСТОРИИ (ВСЕЙ)
    history_str = ""
    if history:
        formatted_history = []
        for msg in history:
            role = "Пользователь" if msg.get("role") == "user" else "Ассистент"
            formatted_history.append(f"{role}: {msg.get('content', '')}")
        if formatted_history:
            history_str = "Недавняя история диалога:\n" + "\n".join(formatted_history) + "\n\n"
            logging.info(f"Formatted ALL history ({len(history)} messages) for the prompt.")

    # 3. Формирование финального сообщения для LLM
    final_message = f"{history_str}Вопрос: {query}\n\n{context_section}"

    logging.info("--- Sending combined message (history+query+context) to OzonExpert ---")
    # --- ЛОГИРОВАНИЕ ПОЛНОГО СООБЩЕНИЯ ДЛЯ LLM ---
    logging.debug(f"Final message for LLM:\n--BEGIN LLM MESSAGE--\n{final_message}\n--END LLM MESSAGE--")
    # --- КОНЕЦ ЛОГИРОВАНИЯ ---

    # 4. Отправка сообщения эксперту и получение ответа
    user_proxy.reset()
    user_proxy.send(
        message=final_message,
        recipient=ozon_expert,
        request_reply=True,
        silent=True,
    )

    # Последнее сообщение в истории user_proxy будет ответом эксперта
    logging.info(f"--- Context being sent to LLM ---\n{final_message}\n--- End of Context ---")
    last_response = user_proxy.last_message(ozon_expert)
    if last_response and isinstance(last_response, dict) and last_response.get("content"):
        logging.info("--- Received response from OzonExpert ---")
        return last_response["content"]
    else:
        logging.error("Failed to get a valid response from OzonExpert.")
        return "Извините, произошла ошибка при получении ответа." 