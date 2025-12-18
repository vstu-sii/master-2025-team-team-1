# ml/models/baseline.py

import os
import json
import requests
from typing import Dict, List, Any, Optional
import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Настройка логирования
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Конфигурация ---
# URL вашего локального API, который предоставляет доступ к AI-моделям
# Предполагается, что API запущен на порту 8000 (см. ml/api/main.py)
LOCAL_API_URL = os.environ.get("LOCAL_AI_API_URL", "http://localhost:8000")

class BaselineLLMModel:
    """
    Клиентская модель, которая взаимодействует с вашим локальным AI API
    для выполнения задач LLM.
    """

    def __init__(self, api_base_url: str = LOCAL_API_URL):
        self.api_base_url = api_base_url
        logger.info(f"BaselineLLMModel initialized. Connecting to local API at: {self.api_base_url}")
            
    def _call_api(self, endpoint: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
        """
        Общая функция для отправки HTTP POST запросов к локальному API.
        """
        url = f"{self.api_base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()  # Вызовет исключение для плохих статусов (4xx или 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling local API {url}: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to local AI API at {url}: {e}")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON response from {url}. Response text: {response.text}", exc_info=True)
            raise ValueError(f"Invalid JSON response from local AI API at {url}.")

    def generate_response_from_prompt(self, prompt: str, model_name: str = "local_model", max_tokens: int = 500, temperature: float = 0.7) -> str:
        """
        Отправляет запрос к локальному API для генерации ответа на основе промпта.
        """
        endpoint = "generate-text" # Предполагаемый эндпоинт в вашем API для генерации текста
        payload = {
            "prompt": prompt,
            "model": model_name, # Имя модели, которое ожидает ваш API
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            result = self._call_api(endpoint, payload)
            return result.get("text", "Error: No 'text' field in local API response for generation.")
        except (ConnectionError, ValueError) as e:
            return f"Error: {e}"

    def evaluate_suitability(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """
        Оценивает соответствие кандидата вакансии, вызывая соответствующий эндпоинт вашего API.
        """
        from ml.prompt_templates import PromptTemplates # Импорт шаблонов
        prompter = PromptTemplates()
        prompt = prompter.format_prompt(
            "evaluate_suitability",
            resume_text=resume_text,
            job_description=job_description
        )
        
        endpoint = "evaluate-suitability" # Эндпоинт в вашем API
        payload = {
            "prompt": prompt,
            "max_tokens": 500,
            "temperature": 0.5,
            "model": "local_llm_evaluator"
        }
        
        try:
            response_data = self._call_api(endpoint, payload)
            score = response_data.get("suitability_score")
            explanation = response_data.get("explanation", "No explanation provided by API.")
            
            if score is not None and not (isinstance(score, int) and 0 <= score <= 100):
                logger.warning(f"Received invalid suitability_score from API: {score}. Treating as None.")
                score = None
                
            return {"suitability_score": score, "explanation": explanation}
        except (ConnectionError, ValueError) as e:
            return {"suitability_score": None, "explanation": f"API Error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error calling API for evaluate_suitability: {e}", exc_info=True)
            return {"suitability_score": None, "explanation": f"Unexpected API Error: {e}"}

    def generate_interview_questions(self, resume_text: str) -> List[str]:
        """
        Генерирует вопросы для интервью, вызывая соответствующий эндпоинт вашего API.
        """
        from ml.prompt_templates import PromptTemplates
        prompter = PromptTemplates()
        prompt = prompter.format_prompt("generate_interview_questions", resume_text=resume_text)
        
        endpoint = "generate-interview-questions" # Эндпоинт в вашем API
        payload = {
            "prompt": prompt,
            "max_tokens": 300,
            "temperature": 0.7,
            "model": "local_llm_question_generator"
        }
        
        try:
            response_data = self._call_api(endpoint, payload)
            questions = response_data.get("questions", [])
            
            if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
                 logger.warning("API returned questions in an invalid format. Expected list of strings.")
                 return ["Error: Invalid format of generated questions from API."]
                 
            return questions[:5]
        except (ConnectionError, ValueError) as e:
            return [f"API Error generating questions: {e}"]
        except Exception as e:
            logger.error(f"Unexpected error calling API for generate_interview_questions: {e}", exc_info=True)
            return [f"Unexpected API Error: {e}"]

    def structure_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Структурирует текст резюме в JSON-формат, вызывая соответствующий эндпоинт вашего API.
        """
        from ml.prompt_templates import PromptTemplates
        prompter = PromptTemplates()
        prompt = prompter.format_prompt("structure_resume", resume_text=resume_text)
        
        endpoint = "structure-resume" # Эндпоинт в вашем API
        payload = {
            "prompt": prompt,
            "max_tokens": 1000,
            "temperature": 0.3,
            "model": "local_llm_structurer"
        }
        
        try:
            response_data = self._call_api(endpoint, payload)
            if isinstance(response_data, dict) and "error" in response_data:
                logger.error(f"Local API returned an error during resume structuring: {response_data.get('error')}")
                return {"error": f"API Error: {response_data.get('error')}", "raw_response": json.dumps(response_data)}
            
            return response_data 
            
        except (ConnectionError, ValueError) as e:
            return {"error": f"API Error: {e}", "raw_response": ""}
        except Exception as e:
            logger.error(f"Unexpected error calling API for structure_resume: {e}", exc_info=True)
            return {"error": f"Unexpected API Error: {e}", "raw_response": ""}

class BaselineEmbeddingModel:
    """
    Клиентская модель, которая взаимодействует с вашим локальным AI API
    для получения векторных представлений (эмбеддингов).
    """
    def __init__(self, api_base_url: str = LOCAL_API_URL):
        self.api_base_url = api_base_url
        logger.info(f"BaselineEmbeddingModel initialized. Connecting to local API at: {self.api_base_url}")

    def _call_api(self, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        """
        Общая функция для отправки HTTP POST запросов к локальному API.
        """
        url = f"{self.api_base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling local API {url}: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to local AI API at {url}: {e}")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON response from {url}. Response text: {response.text}", exc_info=True)
            raise ValueError(f"Invalid JSON response from local AI API at {url}.")

    def get_embedding(self, text: str, model_name: str = "local_embedding_model") -> List[float]:
        """
        Получает векторное представление (эмбеддинг) для заданного текста, вызывая ваш API.
        """
        endpoint = "get-embedding" # Эндпоинт в вашем API
        payload = {
            "text": text,
            "model": model_name # Название модели, которое ожидает ваш API
        }
        
        try:
            result = self._call_api(endpoint, payload)
            embedding = result.get("embedding", [])
            if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
                logger.warning("API returned embedding in an invalid format. Expected list of numbers.")
                return []
            return embedding
        except (ConnectionError, ValueError) as e:
            logger.error(f"API Error getting embedding: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error calling API for get_embedding: {e}", exc_info=True)
            return []

# --- Пример использования ---
if __name__ == "__main__":
    logger.info("--- Testing Baseline Models (as API Clients) ---")
    
    try:
        llm_client = BaselineLLMModel()
        embedding_client = BaselineEmbeddingModel()

        print("\n--- Testing LLM Client with Local API ---")
        sample_resume_text = "Иван Иванов, Python разработчик с 3 годами опыта. Навыки: Python, Django, SQL."
        sample_job_description = "Требуется Python разработчик для веб-приложений. Знание Django и SQL."
        
        print("Evaluating suitability...")
        suitability_result = llm_client.evaluate_suitability(sample_resume_text, sample_job_description)
        print(f"Suitability Evaluation:\n{json.dumps(suitability_result, indent=2, ensure_ascii=False)}")

        print("\nGenerating interview questions...")
        questions = llm_client.generate_interview_questions(sample_resume_text)
        print(f"Generated Interview Questions:\n{json.dumps(questions, indent=2, ensure_ascii=False)}")
        
        print("\nStructuring resume...")
        structured_resume = llm_client.structure_resume(sample_resume_text)
        print(f"Structured Resume:\n{json.dumps(structured_resume, indent=2, ensure_ascii=False)}")
        
        print("\nGetting embedding...")
        embedding = embedding_client.get_embedding("This is a test sentence for local API.")
        print(f"Embedding:\n{embedding[:10]}... (total length: {len(embedding)})")

    except ConnectionError as ce:
        print(f"\nERROR: Could not connect to the local AI API. Please ensure it is running. Details: {ce}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during testing: {e}")
