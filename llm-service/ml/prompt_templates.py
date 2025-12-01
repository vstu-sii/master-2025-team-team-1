class PromptTemplates:
    """
    Реестр промпт-шаблонов для LLM-задач:
    - генерация вопросов для интервью
    - оценка соответствия резюме вакансии
    - структурирование резюме в JSON
    - краткое summary-карточка кандидата
    """

    def __init__(self) -> None:
        pass

    def get_template(self, template_name: str):
        templates = {
            "generate_interview_questions": self._generate_interview_questions,
            "evaluate_suitability": self._evaluate_suitability,
            "structure_resume": self._structure_resume,
            "generate_summary_card": self._generate_summary_card,
        }
        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found.")
        return templates[template_name]

    def format_prompt(self, template_name: str, **kwargs) -> str:
        """
        Возвращает уже отформатированный промпт по имени шаблона.
        """
        template_func = self.get_template(template_name)
        return template_func(**kwargs)

    # --------- Конкретные шаблоны ---------

    def _generate_interview_questions(self, resume_text: str) -> str:
        return f"""
Ты — технический интервьюер.

На основе следующего резюме сформулируй 5 уточняющих вопросов для собеседования.
Вопросы должны быть конкретными, помогать раскрыть опыт, стек технологий и реальные достижения кандидата.
Не отвечай за кандидата, только вопросы.

Резюме:
{resume_text}

Выведи только список вопросов, по одному вопросу в строке, без нумерации и дополнительного текста.
"""

    def _evaluate_suitability(self, resume_text: str, job_description: str) -> str:
        return f"""
Ты — опытный HR-аналитик в сфере IT.

Тебе даны:
1) текст резюме кандидата;
2) текст описания ваканссии.

Нужно:
- оценить соответствие резюме ваканссии по шкале от 0 до 100 (целое число);
- кратко объяснить своё решение (1–3 предложения);
- не придумывать факты, которых нет в резюме.

Резюме кандидата:
{resume_text}

Описание ваканссии:
{job_description}

Верни ответ строго в формате JSON:
{{
  "suitability_score": <целое число от 0 до 100>,
  "explanation": "<краткое объяснение на русском>"
}}

Никакого текста вне JSON, без комментариев и без ```json.
"""

    def _structure_resume(self, resume_text: str) -> str:
        return f"""
Преобразуй следующий текст резюме в структурированный JSON-объект кандидата.

Требуемая структура JSON:

{{
  "candidate_name": string | null,
  "contact_info": {{
    "email": string | null,
    "phone": string | null,
    "linkedin": string | null,
    "github": string | null
  }},
  "summary": string | null,
  "experience": [
    {{
      "company": string | null,
      "role": string | null,
      "start_date": string | null,
      "end_date": string | null,
      "description": string | null
    }}
  ],
  "education": [
    {{
      "institution": string | null,
      "degree": string | null,
      "major": string | null,
      "start_date": string | null,
      "end_date": string | null
    }}
  ],
  "skills": [string]
}}

Если какой-либо информации нет в тексте, ставь null или пустой массив.
Не придумывай данные.

Текст резюме:
{resume_text}

Верни строго валидный JSON без пояснений и текста вне JSON.
"""

    def _generate_summary_card(self, resume_text: str) -> str:
        return f"""
Составь краткое резюме (summary) кандидата в 2–3 предложениях на основе текста резюме.
Цель — быстро передать:
- общий профиль / должность,
- ключевой стек и навыки,
- общий уровень и опыт.

Текст резюме:
{resume_text}

Выведи только краткое резюме одним блоком текста.
"""
