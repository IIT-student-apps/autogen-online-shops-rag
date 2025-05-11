import json
import os
import logging
from typing import List, Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Base Data Processor Class ---
class BaseDataProcessor:
    """
    Абстрактный базовый класс для обработки данных о продуктах из различных источников.
    """
    def __init__(self, source_name: str):
        self.source_name = source_name

    def format_main_product_info(self, data: Dict[str, Any]) -> Optional[str]:
        """Форматирует основную информацию о продукте."""
        raise NotImplementedError("Subclasses must implement format_main_product_info")

    def format_reviews_info(self, data: Dict[str, Any]) -> Optional[str]:
        """Форматирует информацию об отзывах продукта."""
        raise NotImplementedError("Subclasses must implement format_reviews_info")

    def get_product_id(self, data: Dict[str, Any], filename: str) -> str:
        """Извлекает или генерирует базовый ID продукта."""
        raise NotImplementedError("Subclasses must implement get_product_id")

    def create_main_chunk_metadata(self, data: Dict[str, Any], base_product_id: str) -> Dict[str, Any]:
        """Создает метаданные для основного чанка продукта."""
        metadata = {
            "source": self.source_name,
            "type": "main",
            "product_id": base_product_id
        }
        if "URL товара" in data: metadata["url"] = data["URL товара"] # Generic field
        return metadata

    def create_reviews_chunk_metadata(self, data: Dict[str, Any], base_product_id: str) -> Dict[str, Any]:
        """Создает метаданные для чанка с отзывами."""
        metadata = {
            "source": self.source_name,
            "type": "reviews",
            "product_id": base_product_id
        }
        if "URL товара" in data: metadata["url"] = data["URL товара"] # Generic field
        if "Название" in data: metadata["product_name"] = data["Название"] # Generic field
        return metadata

# --- Ozon Data Processor ---
class OzonDataProcessor(BaseDataProcessor):
    """Обработчик данных для продуктов Ozon."""
    def __init__(self):
        super().__init__(source_name="ozon")

    def format_main_product_info(self, data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        text_parts = []
        if "Название" in data: text_parts.append(f"Название: {data['Название']}")
        if "Цена" in data: text_parts.append(f"Цена: {data['Цена']}")
        if "Описание" in data and data["Описание"]: text_parts.append(f"Описание: {data['Описание']}")
        if "Характеристики" in data and isinstance(data["Характеристики"], dict):
            char_str = ", ".join([f"{k}: {v}" for k, v in data["Характеристики"].items() if v])
            if char_str: text_parts.append(f"Характеристики: {char_str}")
        if "Оценка" in data and isinstance(data["Оценка"], dict):
            rating = data["Оценка"].get("overall_rating")
            if rating: text_parts.append(f"Оценка: {rating}")
        if "URL товара" in data: text_parts.append(f"URL: {data['URL товара']}")
        return "\n\n".join(text_parts) if text_parts else None

    def format_reviews_info(self, data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict) or "Отзывы" not in data or not isinstance(data["Отзывы"], list):
            return None
        reviews_text = []
        for review in data["Отзывы"]:
            if isinstance(review, dict):
                reviewer = review.get("reviewer", "Аноним")
                comment = review.get("comment", "")
                rating_val = review.get("rating")
                if comment:
                    reviews_text.append(f"- {reviewer} ({rating_val}/5): {comment}")
        if not reviews_text:
            return None
        title = f"Отзывы на товар: {data.get('Название', 'N/A')}\n"
        return title + "\n".join(reviews_text)

    def get_product_id(self, data: Dict[str, Any], filename: str) -> str:
        return str(data.get("Артикул", data.get("URL товара", filename)))

    def create_main_chunk_metadata(self, data: Dict[str, Any], base_product_id: str) -> Dict[str, Any]:
        metadata = super().create_main_chunk_metadata(data, base_product_id)
        if "Цена" in data: metadata["price"] = data["Цена"] # Ozon specific
        return metadata

# --- Wildberries Data Processor ---
class WildberriesDataProcessor(BaseDataProcessor):
    """Обработчик данных для продуктов Wildberries."""
    def __init__(self):
        super().__init__(source_name="wildberries")

    def format_main_product_info(self, data: Dict[str, Any]) -> Optional[str]:
        # Placeholder: Implement Wildberries specific main info formatting
        # Example:
        # text_parts = []
        # if "name" in data: text_parts.append(f"Наименование: {data['name']}")
        # if "salePriceU" in data: text_parts.append(f"Цена: {float(data['salePriceU']) / 100.0} руб.")
        # if "description" in data: text_parts.append(f"Описание: {data['description']}")
        # # Add more fields as needed (brand, characteristics, etc.)
        # if "supplier" in data and "name" in data["supplier"]: text_parts.append(f"Продавец: {data['supplier']['name']}")
        # if "feedbacks" in data: text_parts.append(f"Количество отзывов: {data['feedbacks']}")
        # if "rating" in data: text_parts.append(f"Рейтинг: {data['rating']}")
        # product_url = f"https://www.wildberries.ru/catalog/{data.get('id')}/detail.aspx" # Assuming 'id' is the WB article
        # text_parts.append(f"URL: {product_url}")

        logging.warning(f"WildberriesDataProcessor.format_main_product_info not fully implemented for product ID: {self.get_product_id(data, '')}")
        # A minimal implementation to return something
        name = data.get('name', 'Неизвестный товар')
        return f"Наименование: {name}\nЭто заглушка для основной информации о товаре Wildberries."

    def format_reviews_info(self, data: Dict[str, Any]) -> Optional[str]:
        # Placeholder: Implement Wildberries specific reviews formatting
        # Example:
        # reviews = data.get("feedback_items", []) # Assuming reviews are in 'feedback_items'
        # if not reviews: return None
        # reviews_text_parts = []
        # for review in reviews:
        #     text = review.get("text", "").strip()
        #     valuation = review.get("productValuation")
        #     if text:
        #         reviews_text_parts.append(f"- Оценка {valuation}/5: {text}")
        # if not reviews_text_parts: return None
        # title = f"Отзывы на товар: {data.get('name', 'N/A')}\n"
        # return title + "\n".join(reviews_text_parts)

        logging.warning(f"WildberriesDataProcessor.format_reviews_info not fully implemented for product ID: {self.get_product_id(data, '')}")
        return f"Отзывы на товар: {data.get('name', 'N/A')}\nЭто заглушка для отзывов о товаре Wildberries."


    def get_product_id(self, data: Dict[str, Any], filename: str) -> str:
        # Placeholder: Wildberries uses 'id' (article number) which is usually an integer.
        # Needs to be adapted based on actual WB JSON structure.
        wb_id = data.get("id", data.get("nm_id", filename)) # 'id' or 'nm_id' are common for WB article
        return str(wb_id)

    def create_main_chunk_metadata(self, data: Dict[str, Any], base_product_id: str) -> Dict[str, Any]:
        metadata = super().create_main_chunk_metadata(data, base_product_id)
        # Add WB specific metadata if any, e.g., price
        # if "salePriceU" in data: metadata["price"] = float(data["salePriceU"]) / 100.0
        # The URL might be constructed differently for WB
        wb_id = data.get("id", data.get("nm_id"))
        if wb_id:
            metadata["url"] = f"https://www.wildberries.ru/catalog/{wb_id}/detail.aspx"
        return metadata

    def create_reviews_chunk_metadata(self, data: Dict[str, Any], base_product_id: str) -> Dict[str, Any]:
        metadata = super().create_reviews_chunk_metadata(data, base_product_id)
        # The URL might be constructed differently for WB
        wb_id = data.get("id", data.get("nm_id"))
        if wb_id:
            metadata["url"] = f"https://www.wildberries.ru/catalog/{wb_id}/detail.aspx"
        if "name" in data: metadata["product_name"] = data["name"]
        return metadata


# --- Старая функция (больше не используется напрямую для индексации) ---
# def format_product_info(data: Dict) -> Optional[str]: ...

# --- Обновленная функция загрузки и обработки ---
def load_and_process_json_files(folder_path: str, processor: BaseDataProcessor) -> List[Dict[str, str]]:
    """
    Загружает JSON из папки, обрабатывает с использованием предоставленного процессора
    и создает чанки (main, reviews).
    """
    processed_chunks = []
    if not os.path.isdir(folder_path):
        logging.error(f"Data folder not found: {folder_path}")
        return []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                base_product_id = processor.get_product_id(data, filename)
                if not base_product_id:
                     logging.warning(f"Could not generate a base ID for {filename} using {processor.source_name} processor. Skipping.")
                     continue

                # --- Создаем чанк с основной информацией ---
                main_text = processor.format_main_product_info(data)
                if main_text:
                    main_metadata = processor.create_main_chunk_metadata(data, base_product_id)
                    processed_chunks.append({
                        "id": base_product_id + "_main", # Уникальный ID для чанка
                        "document": main_text,
                        "metadata": main_metadata
                    })

                # --- Создаем чанк с отзывами (если есть) ---
                reviews_text = processor.format_reviews_info(data)
                if reviews_text:
                    reviews_metadata = processor.create_reviews_chunk_metadata(data, base_product_id)
                    processed_chunks.append({
                        "id": base_product_id + "_reviews", # Уникальный ID для чанка
                        "document": reviews_text,
                        "metadata": reviews_metadata
                    })

            except json.JSONDecodeError:
                logging.warning(f"Skipping invalid JSON file: {filename}")
            except Exception as e:
                logging.error(f"Error processing file {filename} with {processor.source_name} processor: {e}", exc_info=True)

    logging.info(f"Successfully processed {len(processed_chunks)} chunks from {folder_path} using {processor.source_name} processor.")
    return processed_chunks