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
_initialized_experts: Dict[str, AssistantAgent] = {} # Словарь для хранения экспертов

OZON_EXPERT_NAME = "OzonExpert"
WILDBERRIES_EXPERT_NAME = "WildberriesExpert"

def _get_or_initialize_user_proxy():
    """Инициализирует UserProxyAgent, если он еще не создан."""
    global _user_proxy
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
    return _user_proxy

def _get_or_initialize_expert_agent(expert_name: str) -> AssistantAgent:
    """Инициализирует или возвращает существующего экспертного агента по имени."""
    global _initialized_experts
    if expert_name not in _initialized_experts:
        system_message = ""
        if expert_name == OZON_EXPERT_NAME:
            logging.info(f"Initializing {OZON_EXPERT_NAME} AssistantAgent...")
            system_message = (
                "Ты - русскоязычный ИИ-ассистент, эксперт по товарам из интернет-магазина OZON.\n"
                "Тебе будет предоставлено сообщение в формате, которое может включать:\n"
                "[Недавняя история диалога (если есть)]\n\n"
                "Вопрос: [Текущий вопрос пользователя]\n\n"
                "Контекст:\n"
                "[Найденная информация о товарах OZON]\n\n"
                "Ты отвечаешь на Текущий вопрос пользователя. В первую очередь используй предоставленный Контекст.\n"
                "Если Контекст релевантен, отвечай СТРОГО на его основе. Недавняя история диалога может помочь понять, о каком товаре из Контекста идет речь в Текущем вопросе, если он неясен сам по себе.\n"
                "Не придумывай информацию, которой нет в Контексте. Если Контекста для ответа недостаточно или он нерелевантен, или вопрос не связан с товарами OZON, вежливо сообщи об этом.\n"
                "Формулируй ответы четко, лаконично и по делу. Всегда включай URL товара в конец своего ответа, если URL присутствует в предоставленном Контексте. Если URL в Контексте отсутствует, не указывай его и не пытайся его сгенерировать.\n"
                "Не упоминай слова \"Контекст\" или \"предоставленная информация\" в своем ответе, просто давай ответ по существу, как будто продолжаешь диалог.\n"
                "Иногда тебя могут попросить прокомментировать ответ другого эксперта (например, по Wildberries). В этом случае, используй свой основной контекст OZON для предоставления только существенных дополнений или альтернатив. Если дополнить нечего, так и сообщи."
            )
        elif expert_name == WILDBERRIES_EXPERT_NAME:
            logging.info(f"Initializing {WILDBERRIES_EXPERT_NAME} AssistantAgent...")
            system_message = (
                "Ты - русскоязычный ИИ-ассистент, эксперт по товарам из интернет-магазина Wildberries.\n"
                "Тебе будет предоставлено сообщение в формате, которое может включать:\n"
                "[Недавняя история диалога (если есть)]\n\n"
                "Вопрос: [Текущий вопрос пользователя]\n\n"
                "Контекст:\n"
                "[Найденная информация о товарах Wildberries (может быть неполной или отсутствовать)]\n\n"
                "Ты отвечаешь на Текущий вопрос пользователя. В первую очередь используй предоставленный Контекст, если он доступен и релевантен.\n"
                "Если Контекст релевантен, отвечай СТРОГО на его основе. Недавняя история диалога может помочь понять, о каком товаре из Контекста идет речь.\n"
                "Не придумывай информацию, которой нет в Контексте. Если Контекста для ответа недостаточно, он нерелевантен, отсутствует, или вопрос не связан с товарами Wildberries, вежливо сообщи об этом (например, 'К сожалению, информация по товарам Wildberries для данного запроса не найдена' или 'Мой контекст по Wildberries пока не готов').\n"
                "Формулируй ответы четко, лаконично и по делу. Всегда включай URL товара в конец своего ответа, если URL присутствует в предоставленном Контексте. Если URL в Контексте отсутствует, не указывай его и не пытайся его сгенерировать.\n"
                "Не упоминай слова \"Контекст\" или \"предоставленная информация\" в своем ответе, просто давай ответ по существу.\n"
                "Иногда тебя могут попросить прокомментировать ответ другого эксперта (например, по Ozon). В этом случае, используй свой основной контекст Wildberries (если он есть) для предоставления только существенных дополнений. Если твой контекст не готов или дополнить нечего, четко сообщи об этом."
            )
        else:
            raise ValueError(f"Unknown expert name: {expert_name}")

        expert_agent = AssistantAgent(
            name=expert_name,
            system_message=system_message,
            llm_config=config.LLM_CONFIG,
        )
        _initialized_experts[expert_name] = expert_agent
        logging.info(f"{expert_name} AssistantAgent initialized.")
    return _initialized_experts[expert_name]

def get_rag_response(query: str, expert_type: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    """Выполняет RAG поиск, учитывает историю и получает ответ от указанного эксперта, с возможным комментарием от другого эксперта."""

    # --- Определение имен экспертов ---
    primary_expert_name = ""
    secondary_expert_name = ""
    source_filter_primary = ""
    source_filter_secondary = ""

    if expert_type.lower() == "ozon":
        primary_expert_name = OZON_EXPERT_NAME
        secondary_expert_name = WILDBERRIES_EXPERT_NAME
        source_filter_primary = "ozon"
        source_filter_secondary = "wildberries"
    elif expert_type.lower() == "wildberries":
        primary_expert_name = WILDBERRIES_EXPERT_NAME
        secondary_expert_name = OZON_EXPERT_NAME
        source_filter_primary = "wildberries"
        source_filter_secondary = "ozon"
    else:
        logging.error(f"Invalid expert_type provided: {expert_type}")
        return "Ошибка: указан неверный тип эксперта."

    # --- Инициализация агентов ---
    user_proxy = _get_or_initialize_user_proxy()
    primary_expert = _get_or_initialize_expert_agent(primary_expert_name)
    secondary_expert = _get_or_initialize_expert_agent(secondary_expert_name)

    # --- 1. Консультация с Первичным Экспертом ---
    logging.info(f"--- Primary Consultation with {primary_expert_name} for query: '{query}' ---")
    # Важно: search_in_chroma ДОЛЖНА БЫТЬ ОБНОВЛЕНА для поддержки source_filter - ПРОВЕРЕНО, ОНА ПОДДЕРЖИВАЕТ where_filter
    primary_search_results = search_in_chroma(
        query,
        n_results=config.RETRIEVAL_NUM_RESULTS,
        where_filter={"source": source_filter_primary} # ИСПРАВЛЕНО: используем where_filter и передаем словарь
    )
    logging.debug(f"Primary search results for {primary_expert_name} from ChromaDB: {primary_search_results}")

    primary_context_section = f"Контекст ({source_filter_primary}):\\n[Контекст не найден]"
    if primary_search_results:
        documents_texts = [result.get("document", "") for result in primary_search_results if result.get("document")]
        if documents_texts:
            context_str = "\\n\\n---\\n\\n".join(documents_texts)
            logging.info(f"Formatted primary context from {len(documents_texts)} retrieved documents for {primary_expert_name}.")
            primary_context_section = f"Контекст ({source_filter_primary}):\\n{context_str}"
        else:
            logging.warning(f"Primary search for {primary_expert_name} found results but no document texts.")
    else:
        logging.warning(f"Primary search for {primary_expert_name} found NO results.")

    history_str = ""
    if history:
        formatted_history = [f"{('Пользователь' if msg.get('role') == 'user' else 'Ассистент')}: {msg.get('content', '')}" for msg in history]
        if formatted_history:
            history_str = "Недавняя история диалога:\\n" + "\\n".join(formatted_history) + "\\n\\n"
            logging.info(f"Formatted ALL history ({len(history)} messages) for {primary_expert_name} prompt.")

    message_to_primary = f"{history_str}Вопрос: {query}\\n\\n{primary_context_section}"
    logging.info(f"--- Sending message to {primary_expert_name} ---\n{message_to_primary}\n--- End of Message ---")

    user_proxy.reset()
    user_proxy.send(
        message=message_to_primary,
        recipient=primary_expert,
        request_reply=True,
        silent=True,
    )
    primary_response_data = user_proxy.last_message(primary_expert)
    primary_answer_content = ""
    if primary_response_data and isinstance(primary_response_data, dict) and primary_response_data.get("content"):
        primary_answer_content = primary_response_data["content"]
        logging.info(f"--- Received response from {primary_expert_name} ---\n{primary_answer_content}\n--- End of Response ---")
    else:
        logging.error(f"Failed to get a valid response from {primary_expert_name}.")
        # Если основной эксперт не ответил, возвращаем ошибку.
        # Если это был WB и он должен был сказать "нет контекста", это должно прийти как "content".
        return f"Извините, произошла ошибка при получении ответа от {primary_expert_name}."

    # --- 2. Консультация с Вторичным Экспертом (для комментариев) ---
    logging.info(f"--- Secondary Consultation with {secondary_expert_name} ---")
    secondary_search_results = search_in_chroma(
        query, 
        n_results=config.RETRIEVAL_NUM_RESULTS, 
        where_filter={"source": source_filter_secondary} # ИСПРАВЛЕНО: используем where_filter и передаем словарь
    )
    logging.debug(f"Secondary search results for {secondary_expert_name} from ChromaDB: {secondary_search_results}")
    
    secondary_context_section = f"Контекст ({source_filter_secondary}):\\n[Контекст не найден или не используется для данной задачи]"
    if source_filter_secondary == "wildberries" and not secondary_search_results: # Явно указываем, что для WB контекст может быть пуст
         secondary_context_section = f"Контекст ({source_filter_secondary}):\\n[Контекст по Wildberries не найден или еще не подготовлен]"
    elif secondary_search_results:
        documents_texts_secondary = [result.get("document", "") for result in secondary_search_results if result.get("document")]
        if documents_texts_secondary:
            context_str_secondary = "\\n\\n---\\n\\n".join(documents_texts_secondary)
            logging.info(f"Formatted secondary context from {len(documents_texts_secondary)} retrieved documents for {secondary_expert_name}.")
            secondary_context_section = f"Контекст ({source_filter_secondary}):\\n{context_str_secondary}"
        else:
            logging.warning(f"Secondary search for {secondary_expert_name} found results but no document texts.")
    else:
        logging.warning(f"Secondary search for {secondary_expert_name} found NO results (expected for WB initially).")

    prompt_for_secondary = (
        f"Текущий вопрос пользователя: '{query}'\\n\\n"
        f"Ответ от эксперта {primary_expert_name} на этот вопрос был: '{primary_answer_content}'\\n\\n"
        f"Доступный тебе контекст ({source_filter_secondary}):\\n{secondary_context_section}\\n\\n"
        f"Твоя задача, {secondary_expert_name}: Прочитай ответ {primary_expert_name}. "
        f"Основываясь ИСКЛЮЧИТЕЛЬНО на СВОЕМ контексте ({source_filter_secondary}), есть ли у тебя СУЩЕСТВЕННЫЕ дополнения или альтернативные предложения? "
        f"Если дополнений нет, твой контекст пуст/нерелевантен, или ты не можешь ничего добавить к ответу {primary_expert_name}, "
        f"просто ответь фразой типа: 'Дополнений по {source_filter_secondary} нет.' или 'Контекст {source_filter_secondary} не позволяет дополнить ответ.' "
        f"Не повторяй информацию из ответа {primary_expert_name} или из вопроса пользователя."
    )
    logging.info(f"--- Sending message to {secondary_expert_name} ---\n{prompt_for_secondary}\n--- End of Message ---")
    
    user_proxy.reset() # Сбрасываем user_proxy перед новым независимым запросом
    user_proxy.send(
        message=prompt_for_secondary,
        recipient=secondary_expert,
        request_reply=True,
        silent=True,
    )
    secondary_response_data = user_proxy.last_message(secondary_expert)
    secondary_comment_content = ""
    if secondary_response_data and isinstance(secondary_response_data, dict) and secondary_response_data.get("content"):
        secondary_comment_content = secondary_response_data["content"]
        logging.info(f"--- Received commentary from {secondary_expert_name} ---\n{secondary_comment_content}\n--- End of Commentary ---")
    else:
        logging.warning(f"Failed to get a valid commentary from {secondary_expert_name}.")

    # --- 3. Формирование Итогового Ответа ---
    # Основной ответ - это ответ первичного эксперта.
    final_response_to_user = primary_answer_content

    # Логгируем комментарий вторичного эксперта.
    # В соответствии с требованием "WB не имел силы", его ответ пока не добавляется к итоговому.
    if secondary_comment_content:
        logging.info(f"Commentary from {secondary_expert_name} (for logging, not added to user response): {secondary_comment_content}")
        # Если в будущем понадобится добавлять комментарий WB или Ozon (когда он вторичен):
        # if secondary_expert_name == WILDBERRIES_EXPERT_NAME and "Дополнений по wildberries нет" not in secondary_comment_content.lower() and "контекст wildberries не позволяет" not in secondary_comment_content.lower():
        #    # Условие, при котором комментарий WB может быть добавлен (но сейчас не активно)
        #    # final_response_to_user += f"\\n\\nДополнительно от {WILDBERRIES_EXPERT_NAME}: {secondary_comment_content}"
        #    pass
        # elif secondary_expert_name == OZON_EXPERT_NAME and "Дополнений по ozon нет" not in secondary_comment_content.lower() and "контекст ozon не позволяет" not in secondary_comment_content.lower():
        #    # Если WB был основным и не справился, а Ozon имеет что добавить.
        #    # Это более сложный случай, как интегрировать ответ. Пока просто логгируем.
        #    pass
    
    logging.info(f"--- Final response to user will be based on {primary_expert_name}'s answer ---")
    return final_response_to_user 