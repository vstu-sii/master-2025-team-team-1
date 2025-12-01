import os
import re
import json
import logging
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer

from natasha import Segmenter, NewsEmbedding, NewsNERTagger, Doc

# --- Langfuse (опционально) ---
try:
    from langfuse import observe
except ImportError:
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# ----------------- Логирование -----------------
logger = logging.getLogger("ml.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ----------------- Конфигурация моделей -----------------
LLM_MODEL_NAME = os.getenv("LOCAL_LLM_MODEL_NAME", "google/flan-t5-base")
EMBEDDING_MODEL_NAME = os.getenv(
    "LOCAL_EMBEDDING_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)
MAX_INPUT_TOKENS = int(os.getenv("LOCAL_LLM_MAX_INPUT_TOKENS", "1024"))

# ----------------- Инициализация моделей -----------------
logger.info(f"Loading LLM model: {LLM_MODEL_NAME}")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

llm_tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_NAME)
llm_model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL_NAME).to(device)

logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

logger.info("Loading Natasha NER models")
segmenter = Segmenter()
emb = NewsEmbedding()
ner_tagger = NewsNERTagger(emb)

# ----------------- Pydantic-схемы -----------------


class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    model: Optional[str] = None


class EmbeddingRequest(BaseModel):
    text: str
    model: Optional[str] = None


class NERRequest(BaseModel):
    resume_text: str


# ----------------- Вспомогательные функции -----------------


@observe(name="local-llm-generate", as_type="generation")
def generate_text(prompt: str, max_tokens: int, temperature: float) -> str:
    """
    Базовый генератор текста поверх локальной LLM.
    """
    logger.info("LLM generation started")
    inputs = llm_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
    ).to(device)

    generation_kwargs: Dict[str, Any] = {
        "max_new_tokens": max_tokens,
        "do_sample": temperature > 0,
    }
    if temperature > 0:
        generation_kwargs["temperature"] = float(temperature)

    with torch.no_grad():
        output_ids = llm_model.generate(**inputs, **generation_kwargs)
    text = llm_tokenizer.decode(output_ids[0], skip_special_tokens=True)
    logger.info("LLM generation finished")
    return text.strip()


def parse_suitability_output(raw_text: str) -> Dict[str, Any]:
    """
    Пытается распарсить результат оценки соответствия:
    1) Сначала пробуем как JSON.
    2) Если не получилось — вытаскиваем первую цифру 0–100 из текста.
    """
    raw_text = raw_text.strip()

    # 1. Попытка JSON
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "suitability_score" in data:
            score = int(data["suitability_score"])
            explanation = str(data.get("explanation", ""))
            return {
                "suitability_score": max(0, min(100, score)),
                "explanation": explanation,
                "raw_output": raw_text,
            }
    except Exception:
        pass

    # 2. Фоллбэк: поиск целого числа 0–100
    match = re.search(r"(\d{1,3})\s*(?:/100|%|процент|процента|процентов)?", raw_text)
    score = None
    if match:
        maybe = int(match.group(1))
        if 0 <= maybe <= 100:
            score = maybe

    return {
        "suitability_score": score,
        "explanation": raw_text,
        "raw_output": raw_text,
    }


def extract_questions(raw_text: str, max_questions: int = 5) -> List[str]:
    """
    Разбирает сырой текст LLM и пытается выделить из него список вопросов.
    """
    lines = [l.strip() for l in raw_text.splitlines()]
    questions: List[str] = []
    for line in lines:
        if not line:
            continue
        line = re.sub(r"^[\-\*\d\.\)\s]+", "", line)
        if not line:
            continue
        if not line.endswith("?"):
            if any(
                x in line.lower()
                for x in ["?", "как", "что", "какой", "какие", "когда", "почему"]
            ):
                line += "?"
        if "?" in line:
            questions.append(line)
    uniq = []
    for q in questions:
        if q not in uniq:
            uniq.append(q)
    return uniq[:max_questions]


def try_parse_json_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Пытается вытащить JSON-объект из ответа LLM.
    """
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = raw_text[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def get_embedding_vector(text: str) -> List[float]:
    vec = embedding_model.encode(text)
    return vec.tolist()


def extract_entities(text: str) -> List[Dict[str, Any]]:
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(ner_tagger)
    entities: List[Dict[str, Any]] = []
    for span in doc.spans:
        span.normalize(emb)
        entities.append(
            {
                "text": span.text,
                "type": span.type,
                "normalized": span.normal,
                "start": span.start,
                "stop": span.stop,
            }
        )
    return entities


# ----------------- FastAPI-приложение -----------------

app = FastAPI(title="AI HR Local LLM Service", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/generate-text")
def api_generate_text(req: LLMRequest) -> Dict[str, str]:
    try:
        text = generate_text(req.prompt, req.max_tokens, req.temperature)
        return {"text": text}
    except Exception as e:
        logger.exception("Error in /generate-text")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate-suitability")
def api_evaluate_suitability(req: LLMRequest) -> Dict[str, Any]:
    try:
        raw = generate_text(req.prompt, req.max_tokens, req.temperature)
        parsed = parse_suitability_output(raw)
        if parsed["suitability_score"] is None:
            logger.warning("Could not parse suitability_score from model output")
        return parsed
    except Exception as e:
        logger.exception("Error in /evaluate-suitability")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-interview-questions")
def api_generate_interview_questions(req: LLMRequest) -> Dict[str, Any]:
    try:
        raw = generate_text(req.prompt, req.max_tokens, req.temperature)
        questions = extract_questions(raw)
        return {"questions": questions, "raw_output": raw}
    except Exception as e:
        logger.exception("Error in /generate-interview-questions")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/structure-resume")
def api_structure_resume(req: LLMRequest) -> Dict[str, Any]:
    try:
        raw = generate_text(req.prompt, req.max_tokens, req.temperature)
        data = try_parse_json_from_text(raw)
        if data is None:
            logger.error("Could not parse JSON from LLM output in /structure-resume")
            return {"error": "Failed to parse JSON from LLM output", "raw_output": raw}
        return data
    except Exception as e:
        logger.exception("Error in /structure-resume")
        return {"error": str(e)}


@app.post("/get-embedding")
def api_get_embedding(req: EmbeddingRequest) -> Dict[str, Any]:
    try:
        embedding = get_embedding_vector(req.text)
        return {"embedding": embedding}
    except Exception as e:
        logger.exception("Error in /get-embedding")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-entities")
def api_extract_entities(req: NERRequest) -> Dict[str, Any]:
    try:
        entities = extract_entities(req.resume_text)
        return {"entities": entities}
    except Exception as e:
        logger.exception("Error in /extract-entities")
        raise HTTPException(status_code=500, detail=str(e))
