
Описание метрик, которые используются для оценки качества и поведения
baseline-модели сопоставления резюме и вакансии (FLAN-T5 и Mistral),
а также эвристического fallback-а по ключевым словам.

Модели сравниваются на одном и том же мини-датасете из 5 кейсов
(вакансия–резюме–ручная оценка HR), а результаты собираются в `pandas.DataFrame`.

Структура:

1. Метрики качества предсказаний  
2. Метрики производительности  
3. Метрики устойчивости формата / fallback-а  
4. Метрики эвристики по ключевым словам  
5. Реализация метрик в Colab-ноутбуке


---

## 1. Метрики качества предсказаний

### 1.1. MAE — Mean Absolute Error

**Что измеряет**  
Насколько в среднем предсказанный скор модели отличается от «ручной» оценки HR.

**Обозначения:**

*   $y_i$ — ground truth (ручной скор HR) для кейса $i$;
*   $\hat{y}_i$ — предсказанный скор модели для кейса $i$;
*   $N$ — число кейсов в тестовом наборе.

**Формула:**

$$
\mathrm{MAE} = \frac{1}{N} \sum_{i=1}^{N} \left| \hat{y}_i - y_i \right|
$$

**Пример кода (ноутбук)**

В `DataFrame df` есть столбцы `ground_truth_score`, `pred_score` и `abs_error`:

```python
# При формировании df для каждого кейса и модели
rows.append({
    "case_name": case_name,
    "model": res_flan.model_name,  # или Mistral
    "ground_truth_score": gt,
    "pred_score": res_flan.score,
    "abs_error": abs(res_flan.score - gt),
    "used_heuristics": res_flan.used_heuristics,
    "latency_sec": res_flan.latency_sec,
    "prompt_tokens": res_flan.prompt_tokens,
})

df = pd.DataFrame(rows)
```

### 1.2. Корреляция `corr_gt_pred` (Пирсон)

Что измеряет
Насколько линейно согласованы предсказания и ручные оценки: если модель даёт высокие оценки там, где HR тоже ставит высокие — корреляция близка к 1.

**Обозначения**

*   $y_i$ — ground truth;
*   $\hat{y}_i$ — предсказание модели;
*   $\overline{y}$ — среднее ground truth;
*   $\overline{\hat{y}}$ — среднее предсказаний.

**Формула**

$$
\mathrm{corr}(y, \hat{y}) = \frac{\sum_{i=1}^{N} (y_i - \overline{y})(\hat{y}_i - \overline{\hat{y}})}{\sqrt{\sum_{i=1}^{N} (y_i - \overline{y})^2} \cdot \sqrt{\sum_{i=1}^{N} (\hat{y}_i - \overline{\hat{y}})^2}}
$$

**Пример кода**

```python
from math import isnan

extra_rows = []

for model_name, group in df.groupby("model"):
    gt = group["ground_truth_score"]
    pred = group["pred_score"]

    if len(group) > 1:
        corr = gt.corr(pred)  # pandas считает корреляцию Пирсона
    else:
        corr = float("nan")

    extra_rows.append({
        "model": model_name,
        "corr_gt_pred": None if isnan(corr) else round(corr, 3),
        # bucket_accuracy добавляется ниже
    })

extra_metrics_df = pd.DataFrame(extra_rows)
```

### 1.3. Bucket accuracy — точность по категориям совпадения

Мы не только смотрим на точные числа, но и на категории совпадения:
*   `high_match`: score $\ge 70$
*   `medium_match`: $40 \le$ score $< 70$
*   `low_match`: score $< 40$

**Функция bucket'a**

```python
def bucketize(score: float) -> str:
    if score >= 70:
        return "high_match"
    elif score >= 40:
        return "medium_match"
    else:
        return "low_match"
```

**Bucket Accuracy**

**Обозначения**

- $b_i$ — bucket для ground truth (по $y_i$);
- $\hat{b}_i$ — bucket для предсказания (по $\hat{y}_i$);
- $\mathbf{1}\{\cdot\}$ — индикатор (1, если условие выполняется, иначе 0).

**Формула**

$$
\text{BucketAccuracy} = \frac{1}{N} \sum_{i=1}^{N} \mathbf{1}\{b_i = \hat{b}_i\}
$$
```python
for model_name, group in df.groupby("model"):
    gt = group["ground_truth_score"]
    pred = group["pred_score"]

    gt_buckets = gt.map(bucketize)
    pred_buckets = pred.map(bucketize)
    bucket_acc = (gt_buckets == pred_buckets).mean()

    extra_rows.append({
        "model": model_name,
        "corr_gt_pred": None if isnan(corr) else round(corr, 3),
        "bucket_accuracy": round(bucket_acc, 2),
    })

extra_metrics_df = pd.DataFrame(extra_rows)
```
## 2. Метрики производительности
### 2.1 Latency (задержка ответа модели)

**Что измеряет**

Сколько секунд проходит от отправки запроса до получения ответа LLM.

**Обозначения**

- $t_i$ — latency (в секундах) для кейса $i$;
- $N$ — число кейсов.

**Средняя задержка**

$$
\mathrm{avg\_latency} = \frac{1}{N} \sum_{i=1}^{N} t_i
$$

**Минимум и максимум**

$$
\mathrm{min\_latency} = \min_{1 \le i \le N} t_i, \quad \mathrm{max\_latency} = \max_{1 \le i \le N} t_i
$$


```python
# FLAN
def call_flan(prompt: str,
              max_new_tokens: int = 256,
              temperature: float = 0.1) -> Tuple[str, float]:
    inputs = tokenizer_flan(prompt, return_tensors="pt", truncation=True)
    input_ids = inputs["input_ids"].to(device)

    t0 = time.time()
    outputs = model_flan.generate(
        input_ids,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
    )
    latency = time.time() - t0

    text = tokenizer_flan.decode(outputs[0], skip_special_tokens=True)
    return text, latency
```

```python
# Mistral
def call_mistral_chat(prompt: str,
                      model: str = MISTRAL_MODEL,
                      max_tokens: int = 512,
                      temperature: float = 0.1,
                      timeout: int = 30,
                      max_retries: int = 3) -> Tuple[str, float]:
    ...
    while attempt < max_retries:
        attempt += 1
        try:
            t0 = time.time()
            resp = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=timeout)
            latency = time.time() - t0
            
            return text, latency
        
```
** Агрегация по моделям: **
```python
for model_name, group in df.groupby("model"):
    avg_latency = group["latency_sec"].mean()
    min_latency = group["latency_sec"].min()
    max_latency = group["latency_sec"].max()

    metrics_rows.append({
        "model": model_name,
        "MAE": round(mae, 2),
        "avg_latency_sec": round(avg_latency, 3) if avg_latency is not None else None,
        "min_latency_sec": round(min_latency, 3) if min_latency is not None else None,
        "max_latency_sec": round(max_latency, 3) if max_latency is not None else None,
        ...
    })

```


### 2.2 Token count / длина промпта

**Что измеряет**

Приблизительный размер входа в модель (нагрузка по токенам).

Для baseline мы считаем количество «слов» в промпте, как простую оценку.

**Обозначения**

- $\mathrm{prompt\_tokens}_i$ — количество токенов/слов в промпте для кейса $i$;
- $N$ — число кейсов.

**Средняя длина промпта**

$$
\text{avg prompt tokens} = \frac{1}{N} \sum_{i=1}^{N} \text{prompt tokens}_i
$$

```python

def evaluate_resume_flan(job_description: str, resume_text: str) -> SuitabilityResult:
    prompt = build_suitability_prompt(job_description, resume_text)
    prompt_tokens = len(prompt.split())
    ...
    return SuitabilityResult(
        model_name=FLAN_MODEL_NAME,
        score=score,
        explanation=explanation,
        raw_text=raw_text,
        used_heuristics=used_heuristics,
        latency_sec=latency,
        prompt_tokens=prompt_tokens,
    )
```

## 3. Метрики устойчивости формата / fallback-а

**Задача**

Оценить, насколько модель:
- соблюдает формат ответа `SCORE: ... / EXPLANATION: ...`,
- и как часто требуется fallback-эвристика.

В DataFrame `df` есть булевый флаг:

- `used_heuristics`:
  - `False` — LLM вернула корректный формат, парсер успешно извлёк `SCORE` и `EXPLANATION`;
  - `True` — ответ пустой / не в формате, и результат взят из эвристики.

**Обозначим**

- $h_i = 1$, если эвристика использована (used\_heuristics=True);
- $h_i = 0$, если формат корректный.

---

### 3.1 Heuristic fallback rate

**Что измеряет**

Долю кейсов, в которых пришлось использовать эвристический baseline.

**Формула**

$$
\text{heuristic fallback rate} = \frac{1}{N} \sum_{i=1}^{N} h_i
$$

```python

for model_name, group in df.groupby("model"):
    heuristic_rate = group["used_heuristics"].mean()
    format_ok_rate = 1.0 - heuristic_rate

    metrics_rows.append({
        "model": model_name,
        ...
        "format_ok_rate": round(format_ok_rate, 2),
        "heuristic_fallback_rate": round(heuristic_rate, 2),
    })
```

### 3.2 Format ok rate

**Что измеряет**

Долю кейсов, где формат ответа LLM был корректен, и fallback не понадобился.

**Формула**

$$
\text{format ok rate} = 1 - \text{heuristic fallback rate}
$$

**Интерпретация**

- Для FLAN-T5: $\text{heuristic fallback rate}$ может быть выше → модель чаще «ломает» формат.
- Для Mistral: ожидается более высокий $\text{format ok rate}$ → модель лучше подходит для продакшн-пайплайна, где формат важен.


## 4. Метрики эвристики по ключевым словам (fallback baseline)

Когда LLM не может выдать корректный ответ, используется эвристический baseline, который сам опирается на две метрики:

- `skill_overlap` — совпадение по ключевым технологиям;
- `token_overlap` — совпадение по всем смысловым токенам.

---

### 4.1 Skill overlap

**Пусть:**

- $TECH(\text{vacancy})$ — множество тех-токенов в вакансии  
  (пересечение токенов вакансии с заранее заданным множеством $\text{TECH KEYWORDS}$);
- $TECH(\text{resume})$ — множество тех-токенов в резюме.

**Формула**

$$
\text{skill overlap} = \frac{|TECH(\text{vacancy}) \cap TECH(\text{resume})|}{|TECH(\text{vacancy})|}
$$

> Это доля «ключевых технологий» из вакансии, которые встречаются в резюме.

### 4.2 Token overlap

**Пусть:**

- $TOKENS(\text{vacancy})$ — множество смысловых токенов в вакансии  
  (после нормализации и удаления стоп-слов);
- $TOKENS(\text{resume})$ — то же самое для резюме.

**Формула**

$$
\text{token overlap} = \frac{|TOKENS(\text{vacancy}) \cap TOKENS(\text{resume})|}{|TOKENS(\text{vacancy})|}
$$

---

### 4.3 Итоговый эвристический скор

Итоговый скор вычисляется как взвешенная сумма двух overlap-ов:

$$
\text{score} = 100 \cdot \left( 0.7 \cdot \text{skill overlap} + 0.3 \cdot \text{token overlap} \right)
$$

> где:
> - $0.7$ — вес совпадения по технологиям,
> - $0.3$ — вес совпадения по всем токенам.

```python

def compute_overlap(vacancy: str, resume: str) -> Tuple[float, float]:
    vac_tokens = set(normalize_text(vacancy))
    cv_tokens = set(normalize_text(resume))

    tech_vac = {t for t in vac_tokens if t in TECH_KEYWORDS}
    tech_cv = {t for t in cv_tokens if t in TECH_KEYWORDS}

    if tech_vac:
        skill_overlap = len(tech_vac & tech_cv) / len(tech_vac)
    else:
        skill_overlap = 0.0

    if vac_tokens:
        token_overlap = len(vac_tokens & cv_tokens) / len(vac_tokens)
    else:
        token_overlap = 0.0

    return skill_overlap, token_overlap

```

```python

def heuristic_score(vacancy: str, resume: str) -> Tuple[float, str]:
    skill_overlap, token_overlap = compute_overlap(vacancy, resume)
    score = 100.0 * (0.7 * skill_overlap + 0.3 * token_overlap)
    score = max(0.0, min(100.0, round(score, 1)))

    explanation = (
        "Оценка рассчитана автоматически на основе совпадения ключевых технологий "
        "и содержательных терминов между резюме и описанием ваканссии. "
        f"Совпадение по технологиям: {round(skill_overlap * 100, 1)}%, "
        f"по общим токенам: {round(token_overlap * 100, 1)}%. "
        "Чем больше общих технологий (Python, фреймворки, БД, Docker и т.п.), тем выше балл."
    )
    return score, explanation

```

## Итог 

## 5. Какие метрики считаются в Colab-ноутбуке

В итоговом Colab-ноутбуке для спринта считаются:

### 1. Метрики качества предсказаний

- `MAE` (`metrics_df["MAE"]`)
- `corr_gt_pred` (`extra_metrics_df["corr_gt_pred"]`)
- `bucket_accuracy` (`extra_metrics_df["bucket_accuracy"]`)

### 2. Метрики производительности

- `avg_latency_sec`, `min_latency_sec`, `max_latency_sec`
- `avg_prompt_tokens`

### 3. Метрики устойчивости формата

- `heuristic_fallback_rate`
- `format_ok_rate`

### 4. Эвристика по ключевым словам

- `skill_overlap`, `token_overlap` и итоговый `heuristic_score(...)`
  
  → используются **внутри** `heuristic_score(...)` как fallback, когда LLM не смог выдать корректный ответ.

---

## Интерпретация результатов сравнения моделей

## 1. Агрегированные метрики по моделям

Сравниваются две модели:

- `google/flan-t5-base`
- `mistral-small-latest`

**Результаты**
  
<img width="1345" height="127" alt="image" src="https://github.com/user-attachments/assets/9f12a178-3c7c-44e5-977a-d752b58173ce" />


| Метрика                     | `google/flan-t5-base` | `mistral-small-latest` |
|----------------------------|------------------------|-------------------------|
| MAE                        | 12.12                  | 6.00                    |
| avg_latency_sec            | 21.031                 | 0.813                   |
| min_latency_sec            | 8.895                  | 0.720                   |
| max_latency_sec            | 32.221                 | 0.971                   |
| avg_prompt_tokens          | 97.0                   | 97.0                    |
| format_ok_rate             | 0.0                    | 1.0                     |
| heuristic_fallback_rate    | 1.0                    | 0.0                     |

### Ключевые выводы

#### Качество предсказаний (MAE)
- **Mistral-small-latest** значительно точнее: MAE = **6.00** против **12.12** у FLAN-T5.
- Ошибка Mistral в среднем **вдвое меньше**.

#### Производительность (latency)
- **Mistral**: ~0.8 сек на запрос — **очень быстрая**.
- **FLAN-T5**: ~21 сек — **в ~25 раз медленнее**.
- Это делает Mistral пригодной для production, а FLAN-T5 — только для offline-анализа.

#### Длина промпта
- Обе модели получают **одинаковый вход (~97 токенов)** → разница в latency не связана с размером промпта.

#### Устойчивость формата
- **FLAN-T5**: `format_ok_rate = 0.0` → **никогда не выдаёт корректный формат**, всегда используется fallback.
- **Mistral**: `format_ok_rate = 1.0` → **всегда соблюдает формат**, fallback не требуется.

> **Вывод**: Mistral-small-latest превосходит FLAN-T5 по всем ключевым параметрам: точность, скорость и надёжность вывода.

---

## 2. Анализ результатов по кейсам

Рассматриваются разные типы пар «вакансия–резюме» — от сильного совпадения до полного несоответствия.

<img width="1388" height="438" alt="image" src="https://github.com/user-attachments/assets/eb8a6d2e-b322-4c62-a37b-8f4624c23da2" />

### Кейсы 0–1: `strong_match_python_backend`
- **FLAN-T5**: предсказывает 86.9 (ошибка 1.9), но **использует fallback** → формат нарушен.
- **Mistral**: предсказывает 90.0 (ошибка 5.0), **формат корректен**.

> Mistral жертвует небольшой точностью ради **надёжности формата** — что критично для автоматизированных систем.

### Кейсы 2–3: `medium_match_python_mixed_stack`
- **FLAN-T5**: 79.0 (ошибка 19.0) — большая ошибка + fallback.
- **Mistral**: 50.0 (ошибка 10.0) — менее точный, но **формат соблюдён**.

> Mistral стабильнее, даже если предсказание не идеально.

### Кейсы 4–5: `weak_match_frontend_for_backend_role`
- **FLAN-T5**: 23.5 (ошибка 1.5) — почти идеально, но **fallback**.
- **Mistral**: 20.0 (ошибка 5.0) — логичный ответ с корректным форматом.

> FLAN-T5 даёт точное число, но оно **недоступно для парсера** из-за нарушения формата.

### Кейсы 6–7: `almost_no_match_designer`
- **FLAN-T5**: 41.7 (ошибка 36.7) — **нелогично высокий score** при почти полном несовпадении.
- **Mistral**: 0.0 (ошибка 5.0) — **адекватная реакция** на отсутствие совпадений.

> Mistral демонстрирует лучшее понимание семантики задачи.

### Кейсы 8–9: `different_domain_data_scientist`
- **FLAN-T5**: 78.5 (ошибка 1.5) — точно, но **fallback**.
- **Mistral**: 85.0 (ошибка 5.0) — немного выше, но **формат соблюдён**, вывод пригоден к использованию.

---

##  Общий вывод

### Mistral-small-latest
- **Точная** (MAE = 6.0),
- **Быстрая** (~0.8 сек),
- **Надёжная** (всегда корректный формат),
- **Адекватная** в экстремальных кейсах (например, выдаёт 0 при отсутствии совпадений).

> **Рекомендуется для production-пайплайнов.**

### google/flan-t5-base
- **Медленная** (~21 сек),
- **Нестабильная** (всегда нарушает формат),
- **Непредсказуемая** (иногда выдаёт высокие баллы при отсутствии релевантности),
- **Требует fallback во всех случаях** → фактически не использует LLM для генерации финального ответа.

> **Не подходит для автоматизированной обработки в реальном времени.**

---
