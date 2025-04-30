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

# --- Настройка страницы ---
st.set_page_config(page_title="Shops RAG Chat", page_icon="🛒")

# --- Боковая панель (Sidebar) ---
st.sidebar.title("Меню")

# --- Кнопка "Новый чат" ---
if st.sidebar.button("➕ Новый чат"):
    # Сохраняем текущий чат перед созданием нового, если он не пустой и не был загружен
    if st.session_state.messages and st.session_state.current_chat_id is None:
        new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.chat_history[new_chat_id] = st.session_state.messages
        save_history(st.session_state.chat_history)
        logger.info(f"Saved new chat with ID: {new_chat_id}")

    # Очищаем текущий чат и сбрасываем ID
    st.session_state.messages = []
    st.session_state.current_chat_id = None
    logger.info("Started a new chat.")
    st.rerun() # Перезагружаем страницу, чтобы очистить основной интерфейс

st.sidebar.markdown("---")

# --- Раздел индексации данных ---
st.sidebar.title("Управление данными")
st.sidebar.markdown("Запустите процесс индексации данных из папки `ozon_data`.")
if st.sidebar.button("Запустить индексацию данных"):
    st.sidebar.info("Запрос на индексацию отправлен...")
    try:
        with st.spinner("Идет индексация... Это может занять некоторое время."):
            response = requests.post(INGEST_API_URL)
            response.raise_for_status() # Проверяем на HTTP ошибки (4xx, 5xx)
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
# --- Конец раздела индексации ---

st.sidebar.markdown("---")

# --- Раздел истории чатов ---
st.sidebar.title("История чатов")
# Сортируем ID чатов (ключи словаря) в обратном порядке, чтобы новые были сверху
sorted_chat_ids = sorted(st.session_state.chat_history.keys(), reverse=True)

if not sorted_chat_ids:
    st.sidebar.caption("Пока нет сохраненных чатов.")
else:
    for chat_id in sorted_chat_ids:
        # Используем первую фразу пользователя как название чата, если возможно
        chat_title = chat_id # По умолчанию ID
        if st.session_state.chat_history[chat_id]:
            first_message = st.session_state.chat_history[chat_id][0]
            if first_message.get("role") == "user":
                 chat_title = first_message.get("content", chat_id)[:30] + "..." # Обрезаем для краткости

        # Кнопка для загрузки чата
        if st.sidebar.button(chat_title, key=f"load_{chat_id}", use_container_width=True):
            # Сохраняем текущий НЕЗАГРУЖЕННЫЙ чат перед переключением
            if st.session_state.messages and st.session_state.current_chat_id is None:
                new_chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state.chat_history[new_chat_id] = st.session_state.messages
                save_history(st.session_state.chat_history)
                logger.info(f"Saved previous new chat with ID: {new_chat_id} before switching.")

            # Загружаем выбранный чат
            st.session_state.messages = st.session_state.chat_history[chat_id]
            st.session_state.current_chat_id = chat_id
            logger.info(f"Loaded chat with ID: {chat_id}")
            st.rerun() # Перезагружаем для отображения

        # Добавим кнопку удаления чата (опционально)
        # if st.sidebar.button("🗑️", key=f"delete_{chat_id}"):
        #     del st.session_state.chat_history[chat_id]
        #     save_history(st.session_state.chat_history)
        #     # Если удалили текущий чат, создаем новый
        #     if st.session_state.current_chat_id == chat_id:
        #         st.session_state.messages = []
        #         st.session_state.current_chat_id = None
        #     st.rerun()
# --- Конец раздела истории ---


# --- Основной интерфейс чата ---
st.title("🛒 Shops RAG Chat")
st.caption(f"Задайте вопрос о товарах Ozon (Текущий чат: {st.session_state.current_chat_id or 'Новый'})") # Показываем ID активного чата

# Отображение существующих сообщений из st.session_state.messages
if not st.session_state.messages:
     st.info("Начните диалог, задав вопрос ниже, или выберите чат из истории слева.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле ввода для нового сообщения
if prompt := st.chat_input("Ваш вопрос..."):
    # Добавляем сообщение пользователя в текущий активный чат
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Отображаем сообщение пользователя немедленно
    with st.chat_message("user"):
        st.markdown(prompt)

    # Показываем спиннер во время ожидания ответа API
    with st.spinner("Думаю..."):
        try:
            payload = {
                "query": prompt,
                # Отправляем всю историю ТЕКУЩЕГО чата, кроме последнего сообщения пользователя
                "history": st.session_state.messages[:-1]
            }
            logger.info(f"Sending query ('{prompt}') and history ({len(payload['history'])} messages) to API.")

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

    # Добавляем ответ ассистента в текущий активный чат
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

    # --- Автоматическое сохранение изменений в ИСТОРИИ, если чат был загружен ---
    if st.session_state.current_chat_id:
        st.session_state.chat_history[st.session_state.current_chat_id] = st.session_state.messages
        save_history(st.session_state.chat_history)
        logger.debug(f"Auto-saved updated messages for chat ID: {st.session_state.current_chat_id}")
    # --- КОНЕЦ АВТОСОХРАНЕНИЯ ---

    # Перерисовываем страницу, чтобы показать ответ ассистента
    st.rerun() # Используем rerun вместо хака с time.sleep 