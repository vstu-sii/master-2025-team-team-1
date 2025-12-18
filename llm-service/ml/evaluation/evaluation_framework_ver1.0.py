import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

try:
    # Боевой клиент, если локальный API запущен
    from ml.models.baseline import BaselineLLMModel, BaselineEmbeddingModel

    llm_client = BaselineLLMModel(api_base_url="http://localhost:8000")
    embedding_client = BaselineEmbeddingModel(api_base_url="http://localhost:8000")
    USING_MOCKS = False
except Exception:
    # Фоллбэк: мок-клиенты, чтобы evaluation не падал
    USING_MOCKS = True

    class MockLLMClient:
        def evaluate_suitability(
            self, job_description: str, resume: str
        ) -> Dict[str, Any]:
            """
            Простейший мок: всегда возвращает 50 и заглушку объяснения.
            """
            return {
                "suitability_score": 50,
                "explanation": "Mock LLM client (API is not available).",
                "raw_output": "mock",
            }

    class MockEmbeddingClient:
        def get_embedding(self, text: str) -> List[float]:
            """
            Мок-эмбеддинги фиксированной длины.
            """
            return [0.0] * 768

    llm_client = MockLLMClient()
    embedding_client = MockEmbeddingClient()


@dataclass
class SampleResult:
    sample_id: int
    job_description: str
    resume: str
    ground_truth_score: Optional[float]
    model_score: float
    explanation: str
    similarity_embedding: Optional[float]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(a.dot(b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def evaluate_single_sample(sample: Dict[str, Any], idx: int) -> SampleResult:
    job_description = sample.get("job_description", "")
    resume = sample.get("resume", "")
    gt_score = sample.get("ground_truth_score")

    # Вызов LLM-клиента
    llm_resp = llm_client.evaluate_suitability(
        job_description=job_description,
        resume=resume,
    )

    score = llm_resp.get("suitability_score")
    if score is None:
        score = llm_resp.get("score", 0)
    try:
        model_score = float(score)
    except Exception:
        model_score = 0.0

    explanation = str(llm_resp.get("explanation", ""))

    # Эмбеддинги и similarity
    try:
        jd_emb = embedding_client.get_embedding(text=job_description)
        cv_emb = embedding_client.get_embedding(text=resume)
        sim = _cosine_similarity(jd_emb, cv_emb)
    except Exception:
        sim = None

    return SampleResult(
        sample_id=idx,
        job_description=job_description,
        resume=resume,
        ground_truth_score=gt_score,
        model_score=model_score,
        explanation=explanation,
        similarity_embedding=sim,
    )


def load_test_samples() -> List[Dict[str, Any]]:
    """
    Загружает тестовые примеры из ml/evaluation/test_samples.json
    """
    here = Path(__file__).resolve()
    root = here.parents[1]  # .../ml
    data_path = root / "evaluation" / "test_samples.json"
    if not data_path.exists():
        raise FileNotFoundError(f"test_samples.json not found at {data_path}")
    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("test_samples.json must contain a list of samples")
    return data


def run_evaluation() -> Dict[str, Any]:
    samples = load_test_samples()
    results: List[SampleResult] = []

    for idx, sample in enumerate(samples):
        res = evaluate_single_sample(sample, idx)
        results.append(res)

    # Считаем метрики, если есть ground_truth_score
    gt_scores = [
        r.ground_truth_score
        for r in results
        if r.ground_truth_score is not None
    ]
    model_scores = [
        r.model_score
        for r in results
        if r.ground_truth_score is not None
    ]

    metrics: Dict[str, Any] = {}
    if gt_scores and model_scores and len(gt_scores) == len(model_scores):
        mae = mean_absolute_error(gt_scores, model_scores)
        mse = mean_squared_error(gt_scores, model_scores)
        metrics["mae"] = float(mae)
        metrics["mse"] = float(mse)
    else:
        metrics["mae"] = None
        metrics["mse"] = None

    return {
        "using_mocks": USING_MOCKS,
        "num_samples": len(samples),
        "metrics": metrics,
        "results": results,
    }


def print_report():
    info = run_evaluation()

    print("=== Evaluation report ===")
    print(f"Using mocks: {info['using_mocks']}")
    print(f"Num samples: {info['num_samples']}")
    print(f"MAE: {info['metrics']['mae']}")
    print(f"MSE: {info['metrics']['mse']}")
    print()

    for r in info["results"]:
        print(f"--- Sample #{r.sample_id} ---")
        print("Ground truth score:", r.ground_truth_score)
        print("Model score:", r.model_score)
        print("Embedding similarity:", r.similarity_embedding)
        print("Explanation:", r.explanation)
        print()

if __name__ == "__main__":
    print_report()
