import os
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod
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

        # Автоматическое сохранение графа при инициализации
        self.save_graph_visualization()

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

    # src/services/graph_agent.py

    def select_columns_node(self, state):
        print("--- ЭТАП: ФИЛЬТРАЦИЯ КОЛОНОК ---")
        
        # Добавляем слово JSON и жесткую структуру
        prompt = f"""
        You are a SQL Architect. 
        Analyze the user question and the schemas below. 
        Your goal is to return a JSON object that lists only the necessary tables and columns needed to answer the question.
        
        User Question: "{state['question']}"
        Found Schemas: {state['relevant_schemas']}
        
        IMPORTANT: You must return ONLY a JSON object. 
        The JSON must have a key "selected_tables" which is a list of objects.
        Each object must contain: "table_name", "relevant_columns", and "reasoning".
        
        Example format:
        {{
            "selected_tables": [
                {{
                    "table_name": "public.f6",
                    "relevant_columns": ["id", "reg_date"],
                    "reasoning": "Needed to filter documents by date"
                }}
            ]
        }}
        """
        
        # Вызываем LLM. Убедись, что в llm_client.py передается этот промпт.
        response = self.llm.get_structured_output(prompt, TableFilterResponse)
        
        # Теперь Pydantic не упадет, так как мы явно разжевали формат
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
        executor = SQLExecutor()
        result = executor.run_query(state['generated_sql'])
        
        if result["status"] == "error":
            print(f"ОШИБКА ОТ POSTGRES: {result['error_message']}") # <--- ДОБАВЬ ЭТО
            return {"error": result["error_message"], "iteration": state.get("iteration", 0) + 1}
        return {"error": None}

    def should_continue(self, state: AgentState):
        if state.get("error") and state["iteration"] < 3:
            return "retry"
        return "end"
    
    def save_graph_visualization(self):
        """Сохраняет структуру графа в файл PNG"""
        try:
            # Создаем папку, если её нет
            output_dir = "materials"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            output_path = os.path.join(output_dir, "graph_schema.png")
            
            # Генерируем изображение через Mermaid API
            graph_png = self.app.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API,
            )
            
            with open(output_path, "wb") as f:
                f.write(graph_png)
            print(f"--- ГРАФ АГЕНТА СОХРАНЕН: {output_path} ---")
        except Exception as e:
            print(f"Ошибка при сохранении графа: {e}")
            print("Попробуйте установить: pip install pygraphviz")