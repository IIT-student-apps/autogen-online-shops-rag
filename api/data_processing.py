import json
import os
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Новые функции форматирования для чанков ---

def format_main_product_info(data: Dict) -> Optional[str]:
    """Форматирует основную информацию о продукте (без отзывов)."""
    if not isinstance(data, dict):
        return None
    text_parts = []
    # Название, Цена, Описание
    if "Название" in data: text_parts.append(f"Название: {data['Название']}")
    if "Цена" in data: text_parts.append(f"Цена: {data['Цена']}")
    if "Описание" in data and data["Описание"]: text_parts.append(f"Описание: {data['Описание']}")
    # Характеристики
    if "Характеристики" in data and isinstance(data["Характеристики"], dict):
        char_str = ", ".join([f"{k}: {v}" for k, v in data["Характеристики"].items() if v])
        if char_str: text_parts.append(f"Характеристики: {char_str}")
    # Оценка
    if "Оценка" in data and isinstance(data["Оценка"], dict):
        rating = data["Оценка"].get("overall_rating")
        if rating: text_parts.append(f"Оценка: {rating}")
    # URL
    if "URL товара" in data: text_parts.append(f"URL: {data['URL товара']}")
    
    return "\n\n".join(text_parts) if text_parts else None

def format_reviews_info(data: Dict) -> Optional[str]:
    """Форматирует информацию об отзывах."""
    if not isinstance(data, dict) or "Отзывы" not in data or not isinstance(data["Отзывы"], list):
        return None
    
    reviews_text = []
    for review in data["Отзывы"]:
        if isinstance(review, dict):
            reviewer = review.get("reviewer", "Аноним")
            comment = review.get("comment", "")
            rating_val = review.get("rating")
            if comment: # Добавляем только отзывы с текстом комментария
                reviews_text.append(f"- {reviewer} ({rating_val}/5): {comment}")
    
    if not reviews_text:
        return None
        
    # Добавляем название товара для контекста к блоку отзывов
    title = f"Отзывы на товар: {data.get('Название', 'N/A')}\n"
    return title + "\n".join(reviews_text)

# --- Старая функция (больше не используется напрямую для индексации) ---
# def format_product_info(data: Dict) -> Optional[str]: ... 

# --- Обновленная функция загрузки и обработки --- 
def load_and_process_json_files(folder_path: str) -> List[Dict[str, str]]:
    """Загружает JSON, обрабатывает и создает чанки (main, reviews)."""
    processed_chunks = [] # Теперь это список чанков
    if not os.path.isdir(folder_path):
        logging.error(f"Data folder not found: {folder_path}")
        return []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Генерируем базовый ID продукта (строка)
                base_product_id = str(data.get("Артикул", data.get("URL товара", filename)))
                if not base_product_id:
                     logging.warning(f"Could not generate a base ID for {filename}. Skipping.")
                     continue

                # --- Создаем чанк с основной информацией ---
                main_text = format_main_product_info(data)
                if main_text:
                    main_metadata = {
                        "source": "ozon", 
                        "type": "main", 
                        "product_id": base_product_id
                    }
                    if "URL товара" in data: main_metadata["url"] = data["URL товара"]
                    if "Цена" in data: main_metadata["price"] = data["Цена"]
                    
                    processed_chunks.append({
                        "id": base_product_id + "_main", # Уникальный ID для чанка
                        "document": main_text,
                        "metadata": main_metadata
                    })

                # --- Создаем чанк с отзывами (если есть) ---
                reviews_text = format_reviews_info(data)
                if reviews_text:
                    reviews_metadata = {
                        "source": "ozon", 
                        "type": "reviews", 
                        "product_id": base_product_id 
                    }
                    if "URL товара" in data: reviews_metadata["url"] = data["URL товара"]
                    if "Название" in data: reviews_metadata["product_name"] = data["Название"]
                    
                    processed_chunks.append({
                        "id": base_product_id + "_reviews", # Уникальный ID для чанка
                        "document": reviews_text,
                        "metadata": reviews_metadata
                    })
            
            except json.JSONDecodeError:
                logging.warning(f"Skipping invalid JSON file: {filename}")
            except Exception as e:
                logging.error(f"Error processing file {filename}: {e}", exc_info=True)

    logging.info(f"Successfully processed {len(processed_chunks)} chunks from {folder_path}")
    return processed_chunks