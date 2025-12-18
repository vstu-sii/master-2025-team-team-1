# ml/evaluation/evaluation_framework.py

import json
import os
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import numpy as np
import logging
import requests # Для вызова API
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from rouge_score import rouge_scorer
import nltk
from nltk.translate.bleu_score import sentence_bleu # Может потребоваться pip install nltk

# Настройка логирования
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# --- Импорт клиентских моделей ---
try:
    from ml.models.baseline import BaselineLLMModel, BaselineEmbeddingModel
    # Клиенты обращаются к вашему локальному API
    llm_client = BaselineLLMModel(api_base_url="http://localhost:8000")
    embedding_client = BaselineEmbeddingModel(api_base_url="http://localhost:8000")
    logger.info("AI model clients initialized for evaluation.")
    
    def call_ner_api(text: str) -> List[Dict[str, Any]]:
        try:
            response = requests.post(
                "http://localhost:8000/extract-entities",
                json={"resume_text": text},
                timeout=20
            )
            response.raise_for_status()
            result = response.json()
            return result.get("entities", [])
        except Exception as e:
            logger.error(f"Error calling /extract-entities API: {e}", exc_info=True)
            return [{"error": f"API call failed: {e}"}]
    
except (ImportError, ConnectionError) as e:
    logger.error(f"Could not import AI model clients or connect to local API: {e}. Using mock services.", exc_info=True)
    # --- Mock Services ---
    class MockLLMClient:
        def evaluate_suitability(self, **kwargs) -> Dict[str, Any]: return {"suitability_score": np.random.randint(50, 95), "explanation": "Mock: API connection failed."}
        def generate_interview_questions(self, **kwargs) -> List[str]: return ["Mock question (API unavailable)"]
        def structure_resume(self, **kwargs) -> Dict[str, Any]: return {"error": "Mock error: API connection failed."}
    class MockEmbeddingClient:
        def get_embedding(self, **kwargs) -> List[float]: return [0.0] * 768
    llm_client = MockLLMClient()
    embedding_client = MockEmbeddingModel()
    call_ner_api = lambda text: [{"error": "NER API unavailable."}]
    # --- End Mock Services ---

# --- Вспомогательные функции для метрик ---
def calculate_suitability_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    scores = [r.get("model_output", {}).get("suitability_score") for r in results if r.get("matched_ground_truth")]
    ground_truths = [r.get("sample", {}).get("ground_truth_score") for r in results if r.get("matched_ground_truth")]
    metrics = { "mean_absolute_error": None, "mean_squared_error": None, "r2_score": None }
    if len(scores) > 0 and len(ground_truths) > 0 and len(scores) == len(ground_truths):
        scores_np, ground_truths_np = np.array(scores), np.array(ground_truths)
        metrics["mean_absolute_error"] = mean_absolute_error(ground_truths_np, scores_np)
        metrics["mean_squared_error"] = mean_squared_error(ground_truths_np, scores_np)
        metrics["r2_score"] = r2_score(ground_truths_np, scores_np)
    return metrics

def calculate_question_generation_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    total_rouge1_f, total_rouge2_f, total_rougeL_f = 0, 0, 0
    num_valid_samples = 0
    
    for r in results:
        generated_qs = r.get("generated_questions", [])
        ground_truth_qs = r.get("ground_truth_questions", [])
        if not generated_qs or not ground_truth_qs: continue
        num_valid_samples += 1
        
        rouge_scores_for_sample = []
        for gen_q in generated_qs:
            max_rouge_for_gen_q = {'rouge1': 0, 'rouge2': 0, 'rougeL': 0}
            for gt_q in ground_truth_qs:
                try:
                    scores = scorer.score(gt_q, gen_q)
                    max_rouge_for_gen_q['rouge1'] = max(max_rouge_for_gen_q['rouge1'], scores['rouge1'].fmeasure)
                    max_rouge_for_gen_q['rouge2'] = max(max_rouge_for_gen_q['rouge2'], scores['rouge2'].fmeasure)
                    max_rouge_for_gen_q['rougeL'] = max(max_rouge_for_gen_q['rougeL'], scores['rougeL'].fmeasure)
                except Exception as e: logger.warning(f"ROUGE calculation error: {e}")
            rouge_scores_for_sample.append(max_rouge_for_gen_q)

        if rouge_scores_for_sample:
            total_rouge1_f += np.mean([qs['rouge1'] for qs in rouge_scores_for_sample])
            total_rouge2_f += np.mean([qs['rouge2'] for qs in rouge_scores_for_sample])
            total_rougeL_f += np.mean([qs['rougeL'] for qs in rouge_scores_for_sample])

    if num_valid_samples > 0:
        return {
            "avg_rouge1_fmeasure": total_rouge1_f / num_valid_samples,
            "avg_rouge2_fmeasure": total_rouge2_f / num_valid_samples,
            "avg_rougeL_fmeasure": total_rougeL_f / num_valid_samples,
        }
    else: return {}

def calculate_structuring_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    total_samples = len(results)
    valid_json_count = sum(1 for r in results if r.get("is_valid_json", False))
    error_parsing_count = sum(1 for r in results if "parsing_error" in r)
    metrics = {
        "valid_json_percentage": (valid_json_count / total_samples) * 100 if total_samples > 0 else 0,
        "parsing_error_percentage": (error_parsing_count / total_samples) * 100 if total_samples > 0 else 0,
        "total_samples": total_samples, "successfully_parsed": valid_json_count, "failed_to_parse": total_samples - valid_json_count
    }
    return metrics

def save_evaluation_results(results: Dict, filename: str = "evaluation_report.json"):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f: json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Evaluation results saved to: {filename}")
    except Exception as e: logger.error(f"Error saving results to {filename}: {e}", exc_info=True)

def load_test_samples(filepath: str) -> List[Any]:
    if not os.path.exists(filepath): logger.error(f"Test samples file not found at {filepath}"); return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list): logger.error(f"File {filepath} does not contain a list."); return []
            return data
    except json.JSONDecodeError: logger.error(f"Could not decode JSON from {filepath}"); return []
    except Exception as e: logger.error(f"Error loading test samples from {filepath}: {e}", exc_info=True); return []

# --- Основные функции оценки ---
def evaluate_suitability(test_samples: List[Any], model: Any, report_filename: str = "reports/suitability_evaluation_report.json") -> Dict:
    logger.info(f"Starting suitability evaluation for {len(test_samples)} samples.")
    results = []; total_samples = len(test_samples); error_count = 0
    
    for i, sample in enumerate(test_samples):
        resume = sample.get("resume_text"); job = sample.get("job_description"); ground_truth = sample.get("ground_truth_score")
        if not resume or not job: logger.warning(f"Skipping sample {i+1}/{total_samples} due to missing data."); results.append({"sample": sample, "error": "Missing resume or job data."}); error_count += 1; continue
        try:
            model_output = model.evaluate_suitability(resume_text=resume, job_description=job)
            model_score = model_output.get("suitability_score")
            evaluation_entry = {"sample": sample, "model_output": model_output, "matched_ground_truth": False}
            if ground_truth is not None and model_score is not None: evaluation_entry["matched_ground_truth"] = True
            results.append(evaluation_entry)
        except Exception as e: logger.error(f"Error evaluating sample {i+1}/{total_samples}: {e}", exc_info=True); results.append({"sample": sample, "error": str(e)}); error_count += 1
    
    eval_metrics = {"total_samples": total_samples, "successfully_evaluated": len(results) - error_count, "errors": error_count, "with_ground_truth_available": sum(1 for r in results if r.get("matched_ground_truth"))}
    eval_metrics.update(calculate_suitability_metrics(results))
    report_data = {"description": "Suitability Evaluation Report", "timestamp": datetime.now().isoformat(), "model_used": getattr(model, '__class__', 'Unknown Model Client'), "metrics": eval_metrics, "detailed_results": results}
    save_evaluation_results(report_data, filename=report_filename)
    logger.info(f"Suitability evaluation finished. Metrics: {eval_metrics}. Report saved to {report_filename}")
    return report_data

def evaluate_question_generation(test_samples: List[Any], model: Any, report_filename: str = "reports/question_generation_report.json") -> Dict:
    logger.info(f"Starting question generation evaluation for {len(test_samples)} samples.")
    results = []; total_samples = len(test_samples); error_count = 0
    
    for i, sample in enumerate(test_samples):
        resume = sample.get("resume_text"); ground_truth_qs = sample.get("ground_truth_questions", [])
        if not resume: logger.warning(f"Skipping sample {i+1}/{total_samples} due to missing resume text."); results.append({"sample": sample, "error": "Missing resume text."}); error_count += 1; continue
        try:
            generated_questions = model.generate_interview_questions(resume_text=resume)
            evaluation_entry = {"sample": sample, "generated_questions": generated_questions, "ground_truth_questions": ground_truth_qs}
            results.append(evaluation_entry)
        except Exception as e: logger.error(f"Error generating questions for sample {i+1}/{total_samples}: {e}", exc_info=True); results.append({"sample": sample, "error": str(e)}); error_count += 1
            
    gen_metrics = {"total_samples": total_samples, "successfully_evaluated": len(results) - error_count, "errors": error_count}
    gen_metrics.update(calculate_question_generation_metrics(results))
    report_data = {"description": "Question Generation Evaluation Report", "timestamp": datetime.now().isoformat(), "model_used": getattr(model, '__class__', 'Unknown Model Client'), "metrics": gen_metrics, "detailed_results": results}
    save_evaluation_results(report_data, filename=report_filename)
    logger.info(f"Question generation evaluation finished. Metrics: {report_data['metrics']}. Report saved to {report_filename}")
    return report_data

def evaluate_resume_structuring(test_samples: List[Any], model: Any, report_filename: str = "reports/resume_structuring_report.json") -> Dict:
    logger.info(f"Starting resume structuring evaluation for {len(test_samples)} samples.")
    results = []; total_samples = len(test_samples); error_count = 0
    
    for i, sample in enumerate(test_samples):
        resume = sample.get("resume_text"); ground_truth_json = sample.get("ground_truth_json")
        if not resume: logger.warning(f"Skipping sample {i+1}/{total_samples} due to missing resume text."); results.append({"sample": sample, "error": "Missing resume text."}); error_count += 1; continue
        try:
            structured_data = model.structure_resume(resume_text=resume)
            evaluation_entry = {"sample": sample, "structured_data": structured_data, "ground_truth_json": ground_truth_json}
            if isinstance(structured_data, dict) and "error" in structured_data:
                evaluation_entry["parsing_error"] = structured_data["error"]; logger.warning(f"Sample {i+1}/{total_samples}: Model returned error.")
            else:
                try: json.dumps(structured_data); evaluation_entry["is_valid_json"] = True
                except Exception: evaluation_entry["is_valid_json"] = False; logger.error(f"Sample {i+1}/{total_samples}: Structured data not valid JSON.")
            results.append(evaluation_entry)
        except Exception as e: logger.error(f"Error structuring resume for sample {i+1}/{total_samples}: {e}", exc_info=True); results.append({"sample": sample, "error": str(e)}); error_count += 1
            
    struct_metrics = calculate_structuring_metrics(results)
    report_data = {
        "description": "Resume Structuring Evaluation Report", "timestamp": datetime.now().isoformat(),
        "model_used": getattr(model, '__class__', 'Unknown Model Client'),
        "metrics": {"total_samples": total_samples, "errors_during_processing": error_count, **struct_metrics},
        "detailed_results": results
    }
    save_evaluation_results(report_data, filename=report_filename)
    logger.info(f"Resume structuring evaluation finished. Metrics: {report_data['metrics']}. Report saved to {report_filename}")
    return report_data

def evaluate_embedding_similarity(test_samples: List[Any], model: Any, report_filename: str = "reports/embedding_similarity_report.json") -> Dict:
    logger.info(f"Starting embedding similarity evaluation for {len(test_samples)} samples.")
    results = []; total_samples = len(test_samples); error_count = 0
    
    for i, sample in enumerate(test_samples):
        text1 = sample.get("text1"); text2 = sample.get("text2"); ground_truth_similarity = sample.get("ground_truth_similarity")
        if not text1 or not text2: logger.warning(f"Skipping sample {i+1}/{total_samples} due to missing text."); results.append({"sample": sample, "error": "Missing text."}); error_count += 1; continue
        try:
            embedding1 = model.get_embedding(text1); embedding2 = model.get_embedding(text2)
            if not embedding1 or not embedding2: logger.warning(f"Could not get embeddings for sample {i+1}/{total_samples}."); results.append({"sample": sample, "error": "Failed to generate embeddings."}); error_count += 1; continue
                
            dot_product = np.dot(embedding1, embedding2); norm_a = np.linalg.norm(embedding1); norm_b = np.linalg.norm(embedding2)
            cosine_similarity = dot_product / (norm_a * norm_b) if norm_a * norm_b != 0 else 0
            
            evaluation_entry = {"sample": sample, "embeddings_generated": True, "cosine_similarity": cosine_similarity, "ground_truth_similarity": ground_truth_similarity}
            results.append(evaluation_entry)
        except Exception as e: logger.error(f"Embedding similarity error for sample {i+1}/{total_samples}: {e}", exc_info=True); results.append({"sample": sample, "error": str(e)}); error_count += 1
            
    similarities = [r.get("cosine_similarity") for r in results if r.get("ground_truth_similarity") is not None and r.get("embeddings_generated", False)]
    ground_truths = [r.get("ground_truth_similarity") for r in results if r.get("ground_truth_similarity") is not None and r.get("embeddings_generated", False)]
    similarity_metrics = {}
    if len(similarities) > 0 and len(ground_truths) > 0 and len(similarities) == len(ground_truths):
        sim_np, gt_np = np.array(similarities), np.array(ground_truths)
        similarity_metrics["mae_similarity"] = mean_absolute_error(gt_np, sim_np)
        similarity_metrics["r2_similarity"] = r2_score(gt_np, sim_np)

    report_data = {"description": "Embedding Similarity Evaluation Report", "timestamp": datetime.now().isoformat(), "model_used": getattr(model, '__class__', 'Unknown Model Client'), "metrics": {"total_samples": total_samples, "successfully_evaluated": len(results) - error_count, "errors": error_count, "samples_with_ground_truth": len(similarities), **similarity_metrics}, "detailed_results": results}
    save_evaluation_results(report_data, filename=report_filename)
    logger.info(f"Embedding similarity evaluation finished. Metrics: {report_data['metrics']}. Report saved to {report_filename}")
    return report_data

# --- Пример использования ---
if __name__ == "__main__":
    logger.info("--- Starting Evaluation Framework Demonstration ---")
    
    test_data_filepath = "ml/evaluation/test_samples.json"
    if not os.path.exists(test_data_filepath):
        logger.warning(f"'{test_data_filepath}' not found. Creating dummy file.")
        dummy_test_data = [
            {"resume_text": "Иван Иванов, Python разработчик с 3 годами опыта. Навыки: Python, Django, SQL.", "job_description": "Требуется Python разработчик для веб-приложений. Знание Django и SQL.", "ground_truth_score": 90, "ground_truth_questions": ["Опыт с Django?", "SQL запросы?"], "ground_truth_json": {"candidate_name": "Иван Иванов"}},
            {"resume_text": "Мария Петрова, ML Engineer. Опыт: 5 лет. Навыки: Python, TensorFlow, PyTorch, NLP.", "job_description": "ML Engineer. NLP, глубокое обучение.", "ground_truth_score": 75, "ground_truth_questions": ["NLP задачи?", "TensorFlow опыт?"], "ground_truth_json": {"candidate_name": "Мария Петрова"}},
            {"text1": "A cat sat on the mat.", "text2": "A feline rested on the rug.", "ground_truth_similarity": 0.8},
            {"text1": "A cat sat on the mat.", "text2": "A dog chased a ball.", "ground_truth_similarity": 0.2},
            {"resume_text": "", "job_description": "Описание вакансии."}
        ]
        save_evaluation_results(dummy_test_data, filename=test_data_filepath)
    
    test_samples = load_test_samples(test_data_filepath)
    
    if not test_samples: logger.error("No test samples loaded. Exiting."); exit()
    else:
        logger.info("\n--- Evaluating Suitability ---")
        suitability_results = evaluate_suitability(test_samples, llm_client)
        print(f"\nSuitability Evaluation Metrics: {suitability_results.get('metrics')}")
        
        logger.info("\n--- Evaluating Question Generation ---")
        questions_results = evaluate_question_generation(test_samples, llm_client)
        print(f"\nQuestion Generation Evaluation Metrics: {questions_results.get('metrics')}")
        
        logger.info("\n--- Evaluating Resume Structuring ---")
        structuring_results = evaluate_resume_structuring(test_samples, llm_client)
        print(f"\nResume Structuring Evaluation Metrics: {structuring_results.get('metrics')}")
        
        logger.info("\n--- Evaluating Embedding Similarity ---")
        embedding_test_samples = [s for s in test_samples if "text1" in s and "text2" in s and "ground_truth_similarity" in s]
        if embedding_test_samples:
            embedding_results = evaluate_embedding_similarity(embedding_test_samples, embedding_client)
            print(f"\nEmbedding Similarity Evaluation Metrics: {embedding_results.get('metrics')}")
        else: logger.warning("No samples for embedding similarity evaluation.")
