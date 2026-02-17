from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from src.schemas.models import TableFilterResponse, SQLResponse
from src.services.llm_client import LLMClient
from src.services.sql_executor import SQLExecutor
from src.retriever.vector_search import TableRetriever # Предполагаем, что поиск там

# 1. Определяем структуру состояния (то, что передается между узлами)
class AgentState(TypedDict):
    question: str
    relevant_schemas: List[str]
    filtered_schema: Optional[List]
    generated_sql: Optional[str]
    explanation: Optional[str]
    error: Optional[str]
    iteration: int

class SQLGraphAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.retriever = TableRetriever()
        self.executor = SQLExecutor()
        
        # 2. Собираем граф
        workflow = StateGraph(AgentState)
        
        # Добавляем узлы (твои методы)
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("select_columns", self.select_columns_node)
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("execute_sql", self.execute_node)
        
        # 3. Устанавливаем связи (Edges)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "select_columns")
        workflow.add_edge("select_columns", "generate_sql")
        workflow.add_edge("generate_sql", "execute_sql")
        
        # Условный переход (Цикл коррекции)
        workflow.add_conditional_edges(
            "execute_sql",
            self.should_continue,
            {
                "retry": "generate_sql",
                "end": END
            }
        )
        
        # Компилируем граф
        self.app = workflow.compile()

    # --- МЕТОД ДЛЯ FASTAPI ---
    async def run(self, question: str):
        """Точка входа, которую вызывает routes.py"""
        initial_state = {
            "question": question,
            "iteration": 0,
            "relevant_schemas": [],
            "error": None
        }
        # Запускаем граф
        result = await self.app.ainvoke(initial_state)
        return result

    # --- УЗЛЫ ГРАФА ---
    def retrieve_node(self, state: AgentState):
        print("--- ЭТАП: ПОИСК ТАБЛИЦ ---")
        # Поиск в ChromaDB из прошлого шага
        schemas = self.retriever.search(state['question'])
        return {"relevant_schemas": schemas}

    def select_columns_node(self, state: AgentState):
        print("--- ЭТАП: ФИЛЬТРАЦИЯ КОЛОНОК ---")
        prompt = f"Вопрос: {state['question']}\nСхемы: {state['relevant_schemas']}"
        response = self.llm.get_structured_output(prompt, TableFilterResponse)
        return {"filtered_schema": response.selected_tables}

    def generate_sql_node(self, state: AgentState):
        print("--- ЭТАП: ГЕНЕРАЦИЯ SQL ---")
        # Если есть ошибка от прошлого запуска - передаем её в промпт
        error_context = f"\nТвой прошлый запрос упал с ошибкой: {state['error']}. Исправь его." if state.get('error') else ""
        
        prompt = f"Напиши SQL для: {state['question']}\nСхема: {state['filtered_schema']}{error_context}"
        final_response = self.llm.get_structured_output(prompt, SQLResponse)
        return {
            "generated_sql": final_response.sql_query, 
            "explanation": final_response.explanation
        }
    
    def execute_node(self, state: AgentState):
        print("--- ЭТАП: ТЕСТОВЫЙ ЗАПУСК SQL ---")
        result = self.executor.run_query(state['generated_sql'])
        
        if result["status"] == "error":
            return {"error": result["error_message"], "iteration": state["iteration"] + 1}
        return {"error": None}

    def should_continue(self, state: AgentState):
        if state.get("error") and state["iteration"] < 3:
            return "retry"
        return "end"