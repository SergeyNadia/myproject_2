import json
from src.schemas.models import TableFilterResponse, SQLResponse
from src.services.llm_client import LLMClient # Наш клиент к OpenRouter

class SQLGraphAgent:
    def __init__(self):
        self.llm = LLMClient()
        
    def select_columns_node(self, state):
        """Узел 1: Из найденных таблиц выбираем только нужные колонки"""
        print("--- ЭТАП: ФИЛЬТРАЦИЯ КОЛОНОК ---")
        
        # Передаем список таблиц и их полное описание из ChromaDB
        prompt = f"""
        У меня есть вопрос: "{state['question']}"
        И вот список найденных таблиц с их колонками:
        {state['relevant_schemas']}
        
        Выбери только те таблицы и колонки, которые необходимы для написания SQL.
        Верни ответ в формате JSON.
        """
        
        # Используем structured output (многие модели OpenRouter это поддерживают)
        response = self.llm.get_structured_output(prompt, TableFilterResponse)
        
        # Теперь в состоянии у нас не огромная схема, а сжатая
        return {"filtered_schema": response.selected_tables}

    def generate_sql_node(self, state):
        """Узел 2: Пишем SQL на основе обрезанной схемы"""
        print("--- ЭТАП: ГЕНЕРАЦИЯ SQL ---")
        
        # Теперь промпт чистый и короткий
        prompt = f"""
        Напиши SQL для вопроса: "{state['question']}"
        Используй только эти таблицы и колонки:
        {state['filtered_schema']}
        """
        
        final_response = self.llm.get_structured_output(prompt, SQLResponse)
        return {"generated_sql": final_response.sql_query}
    
    def execute_node(self, state):
        """Узел 3: Пробуем запустить SQL"""
        print("--- ЭТАП: ТЕСТОВЫЙ ЗАПУСК SQL ---")
        executor = SQLExecutor()
        
        result = executor.run_query(state['generated_sql'])
        
        if result["status"] == "error":
            return {
                "error": result["error_message"], 
                "iteration": state["iteration"] + 1
            }
        else:
            return {"error": None, "sample_results": result["sample_data"]}

    def should_continue(self, state):
        """Логика перехода: если есть ошибка и мы не превысили лимит попыток — идем на круг"""
        if state.get("error") and state.get("iteration", 0) < 3:
            print(f"--- НАЙДЕНА ОШИБКА, ИДУ НА КРУГ {state['iteration']} ---")
            return "generate_sql" # Возвращаемся к узлу генерации
        return END # Завершаем