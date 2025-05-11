import streamlit as st
import requests
import logging
import os # Добавляем os для чтения переменных окружения
import json # Для работы с JSON-файлом истории
from datetime import datetime # Для генерации ID чатов

# Настройка логирования для Streamlit приложения
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Константы ---
HISTORY_FILE = "chat_history.json"
ERROR_KEYWORDS = ["Ошибка при подключении к API", "Произошла непредвиденная ошибка", "Failed to get a valid response", "Internal Server Error", "Критическая ошибка"]

# --- URLы FastAPI бэкенда ---
# Читаем базовый URL из переменной окружения, с fallback для локального запуска
BASE_API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
CHAT_API_URL = f"{BASE_API_URL}/chat"
INGEST_API_URL = f"{BASE_API_URL}/ingest"

# --- Функции для работы с историей чатов ---

def load_history():
    """Загружает историю чатов из JSON-файла."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading chat history from {HISTORY_FILE}: {e}")
            return {} # Возвращаем пустой словарь в случае ошибки
    return {}

def save_history(history_data):
    """Сохраняет историю чатов в JSON-файл."""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        logger.error(f"Error saving chat history to {HISTORY_FILE}: {e}")

# --- Инициализация Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = [] # Текущий активный чат
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history() # Загруженная история всех чатов
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None # ID текущего активного чата из истории

# --- Новые состояния для механизма повтора ---
if "allow_retry" not in st.session_state:
    st.session_state.allow_retry = False
if "prompt_to_retry_content" not in st.session_state: # Хранит текст промпта для повтора
    st.session_state.prompt_to_retry_content = None
if "process_this_prompt_on_next_run" not in st.session_state: # Флаг для запуска обработки при повторе
    st.session_state.process_this_prompt_on_next_run = None

# --- Настройка страницы ---
st.set_page_config(page_title="Shops RAG Chat", page_icon="🛒")

# --- Боковая панель (Sidebar) ---
st.sidebar.title("Меню")

def reset_retry_flags():
    st.session_state.allow_retry = False
    # st.session_state.prompt_to_retry_content не сбрасываем здесь, он сбрасывается при успешной отправке или новом вводе
    # st.session_state.process_this_prompt_on_next_run сбрасывается после использования

# --- Кнопка "Новый чат" ---
if st.sidebar.button("➕ Новый чат"):
    if st.session_state.messages and st.session_state.current_chat_id is None:
        new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.chat_history[new_chat_id] = st.session_state.messages
        save_history(st.session_state.chat_history)
        logger.info(f"Saved new chat with ID: {new_chat_id}")

    st.session_state.messages = []
    st.session_state.current_chat_id = None
    reset_retry_flags() # Сбрасываем флаги при создании нового чата
    logger.info("Started a new chat.")
    st.rerun()

st.sidebar.markdown("---")

# --- Раздел индексации данных ---
st.sidebar.title("Управление данными")
st.sidebar.markdown("Выберите источник и запустите процесс индексации данных.")

source_to_ingest = st.sidebar.radio(
    "Выберите источник для индексации:",
    ("Ozon", "Wildberries"),
    key="ingest_source_select"
)

if st.sidebar.button("🚀 Запустить индексацию данных"):
    selected_source_key = source_to_ingest.lower()
    st.sidebar.info(f"Запрос на индексацию для '{source_to_ingest}' отправлен...")
    try:
        with st.spinner(f"Идет индексация для '{source_to_ingest}'... Это может занять некоторое время."):
            payload = {"source": selected_source_key}
            response = requests.post(INGEST_API_URL, json=payload)
            response.raise_for_status()
            ingest_response = response.json()
            status = ingest_response.get("status", "error")
            message = ingest_response.get("message", "Неизвестный ответ от API.")

            if status == "success":
                st.sidebar.success(message)
            elif status == "warning":
                 st.sidebar.warning(message)
            else:
                st.sidebar.error(f"Ошибка индексации: {message}")
            logger.info(f"Ingestion response: Status={status}, Message={message}")

    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Ошибка подключения к API индексации: {e}")
        logger.error(f"Ingestion API request failed: {e}")
    except Exception as e:
        st.sidebar.error(f"Непредвиденная ошибка во время запроса на индексацию: {e}")
        logger.error(f"An unexpected error occurred during ingestion request: {e}")

st.sidebar.markdown("---")

# --- Раздел истории чатов ---
st.sidebar.title("История чатов")
sorted_chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)

if not sorted_chat_ids:
    st.sidebar.caption("Пока нет сохраненных чатов.")
else:
    for chat_id in sorted_chat_ids:
        chat_title = chat_id
        if st.session_state.chat_history[chat_id]:
            first_message = st.session_state.chat_history[chat_id][0]
            if first_message.get("role") == "user":
                 chat_title = first_message.get("content", chat_id)[:30] + "..."

        col1, col2 = st.sidebar.columns([4, 1])
        with col1:
            if st.button(chat_title, key=f"load_{chat_id}", use_container_width=True):
                if st.session_state.messages and st.session_state.current_chat_id is None:
                    new_id_for_unsaved = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    st.session_state.chat_history[new_id_for_unsaved] = st.session_state.messages
                    save_history(st.session_state.chat_history)
                    logger.info(f"Saved previous new chat with ID: {new_id_for_unsaved} before switching.")
                
                st.session_state.messages = st.session_state.chat_history[chat_id]
                st.session_state.current_chat_id = chat_id
                reset_retry_flags() # Сбрасываем флаги при загрузке чата
                logger.info(f"Loaded chat with ID: {chat_id}")
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{chat_id}", help="Удалить этот чат"):
                logger.info(f"Attempting to delete chat ID: {chat_id}")
                if chat_id in st.session_state.chat_history:
                    del st.session_state.chat_history[chat_id]
                    save_history(st.session_state.chat_history)
                    logger.info(f"Deleted chat ID: {chat_id} from history.")
                    if st.session_state.current_chat_id == chat_id:
                        st.session_state.messages = []
                        st.session_state.current_chat_id = None
                        reset_retry_flags() # Сбрасываем флаги
                        logger.info("Current chat was deleted, cleared messages and ID.")
                    st.rerun()
# --- Конец раздела истории ---

# --- Основной интерфейс чата ---
st.title("🛒 Shops RAG Chat")
st.caption(f"Задайте вопрос о товарах (Текущий чат: {st.session_state.current_chat_id or 'Новый'})")

# Отображение существующих сообщений
if not st.session_state.messages:
     st.info("Начните диалог, задав вопрос ниже, или выберите чат из истории слева.")

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Если это последнее сообщение, это ошибка от ассистента, и разрешен повтор
        if i == len(st.session_state.messages) - 1 and \
           message["role"] == "assistant" and \
           st.session_state.get("allow_retry"):
            if st.button("🔁 Повторить последний запрос", key=f"retry_msg_btn_{i}"):
                if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
                    st.session_state.messages.pop() # Удаляем сообщение об ошибке ассистента
                
                # Устанавливаем промпт для обработки в следующем цикле rerun
                st.session_state.process_this_prompt_on_next_run = st.session_state.prompt_to_retry_content
                # st.session_state.allow_retry будет сброшен при обработке
                logger.info(f"Retry button clicked. Will process prompt: {st.session_state.prompt_to_retry_content}")
                st.rerun()

# --- Логика обработки ввода и ответа API ---
prompt_to_process_this_run = None
is_newly_submitted_prompt = False

# 1. Проверяем, есть ли промпт для повтора
if st.session_state.get("process_this_prompt_on_next_run"):
    prompt_to_process_this_run = st.session_state.process_this_prompt_on_next_run
    st.session_state.process_this_prompt_on_next_run = None # Используем один раз
    # Сообщение пользователя уже в истории, мы удалили только ошибочный ответ ассистента
    st.session_state.allow_retry = False # Сбрасываем флаг, так как пытаемся повторить
    logger.info(f"Processing retried prompt: {prompt_to_process_this_run}")

# 2. Если нет промпта для повтора, проверяем новый ввод от пользователя
elif new_user_prompt := st.chat_input("Ваш вопрос..."):
    prompt_to_process_this_run = new_user_prompt
    st.session_state.messages.append({"role": "user", "content": prompt_to_process_this_run})
    # Отображаем сообщение пользователя немедленно (только для нового ввода)
    with st.chat_message("user"):
        st.markdown(prompt_to_process_this_run)
    is_newly_submitted_prompt = True
    st.session_state.allow_retry = False # Сбрасываем при новом вводе
    logger.info(f"Processing new user prompt: {prompt_to_process_this_run}")


# 3. Если есть промпт для обработки (новый или повторный)
if prompt_to_process_this_run:
    with st.spinner("Думаю..."):
        try:
            # История для API всегда это все сообщения КРОМЕ последнего (которое является текущим user prompt)
            # или если это повтор, то последнее сообщение пользователя - это то, что мы повторяем.
            history_for_api = []
            if len(st.session_state.messages) > 1 : # Если есть хотя бы одно сообщение пользователя и что-то до него
                 history_for_api = st.session_state.messages[:-1]
            elif not st.session_state.messages or st.session_state.messages[-1]["content"] != prompt_to_process_this_run :
                # Это условие может быть сложным, если это повтор и сообщение пользователя - единственное.
                # Проще: если messages не пустое, и последнее сообщение - это наш prompt_to_process_this_run, то история - это все до него.
                pass # history_for_api будет пустой, если это первое сообщение или единственное после ошибки

            # Корректная история для API: все сообщения до текущего промпта пользователя.
            # Если prompt_to_process_this_run == st.session_state.messages[-1]["content"], то история - messages[:-1]
            # Это будет верно и для нового, и для повторного запроса (после pop ошибки ассистента)
            final_history_for_api = []
            if st.session_state.messages and st.session_state.messages[-1]["role"] == "user" and st.session_state.messages[-1]["content"] == prompt_to_process_this_run:
                final_history_for_api = st.session_state.messages[:-1]


            payload = {
                "query": prompt_to_process_this_run,
                "history": final_history_for_api,
                "expert_type": "ozon" # TODO: Сделать выбор эксперта в UI
            }
            logger.info(f"Sending query ('{payload['query']}') and history ({len(payload['history'])} messages) to API.")

            response = requests.post(CHAT_API_URL, json=payload)
            response.raise_for_status()
            api_response = response.json()
            assistant_response = api_response.get("answer", "Не удалось получить ответ от API.")
            logger.info(f"Received response from API: {assistant_response[:100]}...")

        except requests.exceptions.RequestException as e:
            logger.error(f"Chat API request failed: {e}")
            assistant_response = f"Ошибка при подключении к API чата: {e}"
        except Exception as e:
            logger.error(f"An unexpected error occurred during chat request: {e}")
            assistant_response = f"Произошла непредвиденная ошибка: {e}"

    # Проверяем, не является ли ответ ошибкой, чтобы разрешить повтор
    current_response_is_error = any(keyword in assistant_response for keyword in ERROR_KEYWORDS)
    if current_response_is_error:
        st.session_state.allow_retry = True
        # Сохраняем именно тот промпт, который вызвал ошибку
        st.session_state.prompt_to_retry_content = prompt_to_process_this_run
        logger.info(f"Error detected in response. Allow_retry set. Prompt to retry: {prompt_to_process_this_run}")
    else:
        st.session_state.allow_retry = False # Сбрасываем, если ответ успешный
        st.session_state.prompt_to_retry_content = None


    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

    # --- Логика сохранения чата ---
    chat_was_just_created = False
    if not st.session_state.current_chat_id and st.session_state.messages:
        new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.current_chat_id = new_chat_id
        chat_was_just_created = True
    
    if st.session_state.current_chat_id and st.session_state.messages:
        st.session_state.chat_history[st.session_state.current_chat_id] = st.session_state.messages
        save_history(st.session_state.chat_history)
        if chat_was_just_created:
            logger.info(f"Saved new chat with ID: {st.session_state.current_chat_id}")
        else:
            logger.debug(f"Auto-saved updated messages for chat ID: {st.session_state.current_chat_id}")
    
    st.rerun() 