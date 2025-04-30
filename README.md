# Ozon RAG Chat Project

Репозиторий: [https://github.com/IIT-student-apps/autogen-online-shops-rag](https://github.com/IIT-student-apps/autogen-online-shops-rag)

Проект для создания чат-бота с использованием Retrieval-Augmented Generation (RAG) для ответов на вопросы о товарах Ozon.

## Структура проекта

- `api/`: Содержит бэкенд FastAPI и основную логику.
  - `main.py`: Основной файл FastAPI приложения с эндпоинтом `/chat`.
  - `rag_logic.py`: Логика настройки агентов AutoGen и получения RAG-ответа.
  - `data_management.py`: Функции для управления данными (индексация и т.д.).
  - `data_processing.py`: Функции для обработки и форматирования данных о товарах.
  - `vector_store.py`: Логика взаимодействия с векторной базой данных ChromaDB.
  - `config.py`: Конфигурация (LLM API ключи, пути и т.д.). **Не забудьте создать `.env` файл!**
- `app/`: Содержит фронтенд Streamlit.
  - `streamlit_app.py`: Файл Streamlit приложения для чат-интерфейса.
- `ingest_data.py`: Скрипт в корне для запуска процесса начальной/массовой индексации данных из папки `DATA_FOLDER`.
- `.gitignore`: Список файлов и папок, игнорируемых Git.
- `requirements.txt`: Список зависимостей Python.
- `README.md`: Этот файл.

## Установка

1.  **Клонируйте репозиторий (если вы этого еще не сделали):**
    ```bash
    # git clone <repo-url>
    # cd <repo-directory>
    ```

2.  **Создайте и активируйте виртуальное окружение:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте API ключ:**
    Создайте файл `.env` в корневой директории проекта и добавьте ваш API ключ для Google Generative AI:
    ```dotenv
    GOOGLE_API_KEY="YOUR_API_KEY"
    ```
    *Примечание: Убедитесь, что файл `.env` добавлен в `.gitignore`.*

5.  **Подготовьте данные для индексации:**
    Поместите ваши JSON файлы с данными о товарах в папку, указанную в `api/config.py` (по умолчанию `data/`).

6.  **Запустите начальную индексацию данных:**
    Выполните скрипт `ingest_data.py` из корневой папки проекта:
    ```bash
    python ingest_data.py
    ```
    Этот шаг необходимо выполнить перед первым запуском API, чтобы заполнить векторную базу данных.

## Запуск

1.  **Запустите FastAPI сервер:**
    Откройте терминал, убедитесь, что вы находитесь в **корневой директории проекта**, и выполните:
    ```bash
    # НЕ переходите в папку api!
    uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
    ```
    API будет доступен по адресу `http://127.0.0.1:8000`.

2.  **Запустите Streamlit приложение:**
    Откройте *другой* терминал, перейдите в корневую директорию проекта и выполните:
    ```bash
    cd app
    streamlit run streamlit_app.py
    ```
    Приложение откроется в вашем браузере по адресу `http://localhost:8501` (или другому порту, если 8501 занят).

Теперь вы можете общаться с RAG-ассистентом через интерфейс Streamlit. 