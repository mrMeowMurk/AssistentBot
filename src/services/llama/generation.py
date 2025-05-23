"""
    ╔════════════════════════════════════════════════════════════╗
    ║                    Модуль generator.py                     ║
    ╚════════════════════════════════════════════════════════════╝

    Описание:
        Этот модуль содержит класс TextGenerator, который предоставляет метод
        generate_text для генерации ответа на основе запроса пользователя и
        данных поиска. Класс отправляет асинхронный POST-запрос к API генерации текста
        и возвращает сгенерированный ответ

    Зависимости:
        • aiohttp - для асинхронных HTTP запросов
        • config - для конфигурации API
        • logger - для логирования
"""

import sys
import json
import aiohttp

from typing    import Optional, Dict, Any
from config    import config
from src.utils import logger


class TextGenerator:
    """
        Класс для генерации текстовых ответов с использованием LLM API.
    """
    
    def __init__(self):
        """
            Инициализация генератора текста.
        """
        self.url = config.services.ai_api
        self.headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {config.services.ai_key}"
        }
        self.model = config.services.ai_model
        self._session: Optional[aiohttp.ClientSession] = None


    async def __aenter__(self):
        """
            Создание сессии при входе в контекстный менеджер
        """
        self._session = aiohttp.ClientSession()
        return self


    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
            Закрытие сессии при выходе из контекстного менеджера
        """
        if self._session:
            await self._session.close()


    async def generate_text(self, query: str, result_data: str) -> str:
        """
            Генерация текстового ответа на основе запроса и данных.
        """
        try:
            # Проверяем тип входных данных
            if not isinstance(result_data, str):
                result_data = json.dumps(result_data, ensure_ascii=False)
            
            logger.info(f"Отправка запроса к API: {self.url}")
            logger.debug(f"Запрос: {query}")
            logger.debug(f"Данные: {result_data}")
            
            payload = self._prepare_payload(query, result_data)
            
            if not self._session:
                self._session = aiohttp.ClientSession()
                
            async with self._session.post(self.url, headers=self.headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ошибка API: {response.status}, {error_text}")
                    return "Извините, произошла ошибка при генерации ответа."
                    
                resp_data = await response.json()
                return resp_data['choices'][0]['message']['content']
                
        except Exception as e:
            logger.error(f"Ошибка при генерации текста: {str(e)}")
            return "Извините, произошла ошибка при генерации ответа."


    def _prepare_payload(self, query: str, result_data: str) -> Dict[str, Any]:
        """
            Подготовка payload для запроса к API.
        """
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt(result_data)
                },
                {
                    "role": "user",
                    "content": f"Запрос: {query}."
                }
            ],
        }


    def _get_system_prompt(self, result_data: str) -> str:
        """
            Формирование системного промпта для модели.
        """
        return (
            '''
            Ты бот-ассистент для работы с товарами.
            
            ВАЖНО: Ты должен ВСЕГДА использовать точные значения из предоставленных данных.
            НЕ ПРИДУМЫВАЙ значения, которых нет в данных.
            НЕ ПИШИ "Не указано" если значение есть в данных.
            
            Инструкции по обработке данных:
            1. Проанализируй предоставленные данные о товаре (они в формате JSON)
            2. Используй ТОЧНО те значения, которые есть в данных
            3. Для цен используй следующие поля:
               - "Цена" для базовой цены
               - "Цена с НДС" для цены с НДС
               - "РРЦ" для рекомендованной розничной цены
            4. Если пользователь спрашивает о цене, укажи все доступные цены из данных
            5. Если значение в данных равно null, None или пустой строке, то пиши "Не указано"
            
            Сначала дай прямой ответ на вопрос пользователя, затем выведи полную информацию о товаре:
            
            Шаблон ответа:  
                ### 1. Товар:
                    - Артикул: [значение из поля "Артикул"]
                    - Наименование: [значение из поля "Наименование"]
                    - Описание: [значение из поля "Описание"]

                ### 2. Цены:
                    - Базовая цена: [значение из поля "Цена"]
                    - Цена с НДС: [значение из поля "Цена с НДС"]
                    - РРЦ: [значение из поля "РРЦ"]
                    - Акции/Скидки: Не указаны

                ### 3. Характеристики:
                    - Ед. изм.: [значение из поля "Ед. изм."]
                    - Кол-во листов: [значение из поля "Кол-во листов"]
                    - Формат: [значение из поля "Формат"]
                    - Класс: [значение из поля "Класс"]
                    - Материал: [значение из поля "Материал"]
                    - Карты, стенды, таблицы: [значение из поля "Карты, стенды, таблицы"]

                ### 4. Наличие:
                    - Статус: [Требует уточнения]

                ### 5. Рекомендации:
                    Похожие товары:
                        - (Артикул 1: [значение 1]), [Название 1], цена 1: [значение 1], преимущество 1: [описание 1]
                        - (Артикул 2: [значение 2]), [Название 2], цена 2: [значение 2], преимущество 2: [описание 2]
            '''
            + f" Вот данные для анализа (в формате JSON): {result_data}"
        )

    async def close(self):
        """
            Закрытие сессии клиента
        """
        if self._session:
            await self._session.close()
            self._session = None
