from openai import OpenAI
from src.core.config import settings

class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY
        )

    def get_structured_output(self, prompt, response_model):
        """Магия превращения ответа LLM в Pydantic объект"""
        response = self.client.chat.completions.create(
            model="upstage/solar-pro-3:free", # Или любая другая мощная модель
            messages=[{"role": "user", "content": prompt}],
            # Просим модель вернуть JSON
            response_format={ "type": "json_object" } 
        )
        
        content = response.choices[0].message.content
        # Валидируем через Pydantic
        return response_model.model_validate_json(content)