# ml/prompt_templates.py

import os

class PromptTemplates:
    def __init__(self):
        pass

    def get_template(self, template_name: str) -> str:
        templates = {
            "generate_interview_questions": self._generate_interview_questions,
            "evaluate_suitability": self._evaluate_suitability,
            "structure_resume": self._structure_resume,
            "generate_summary_card": self._generate_summary_card,
        }
        if template_name in templates: return templates[template_name]
        else: raise ValueError(f"Template '{template_name}' not found.")

    def format_prompt(self, template_name: str, **kwargs) -> str:
        template_func = self.get_template(template_name)
        return template_func(**kwargs)

    def _generate_interview_questions(self, resume_text: str) -> str:
        return f"""
        На основе следующего резюме, сформулируй 5 уточняющих вопросов для собеседования.
        Вопросы должны быть конкретными и направленными на прояснение опыта, навыков или достижений кандидата.
        Сконцентрируйся на тех аспектах, которые могут потребовать дополнительного раскрытия.

        Резюме:
        ---
        {resume_text}
        ---

        Сформулируй 5 вопросов:
        """

    def _evaluate_suitability(self, resume_text: str, job_description: str) -> str:
        return f"""
        Ты — HR-аналитик. Твоя задача — оценить, насколько резюме кандидата соответствует требованиям вакансии.
        Предоставь оценку по шкале от 0 до 100%, где 100% — полное соответствие.
        Также дай краткое объяснение своего решения, указав на сильные стороны кандидата и возможные пробелы.

        Резюме кандидата:
        ---
        {resume_text}
        ---

        Описание вакансии:
        ---
        {job_description}
        ---

        Оцени соответствие кандидата вакансии (0-100) и объясни свой вывод:
        """

    def _structure_resume(self, resume_text: str) -> str:
        return f"""
        Преобразуй следующий текст резюме в структурированный JSON объект.
        JSON должен содержать следующие обязательные поля:
        - "candidate_name": Имя кандидата (если известно, иначе null).
        - "contact_info": Объект с контактной информацией (email, phone, linkedin, github - если доступны).
        - "summary": Краткое описание кандидата (2-3 предложения).
        - "experience": Массив объектов, каждый содержащий "company", "role", "start_date", "end_date", "description".
        - "education": Массив объектов, каждый содержащий "institution", "degree", "major", "start_date", "end_date".
        - "skills": Массив строк с ключевыми навыками.
        
        Если какая-либо информация отсутствует в тексте, соответствующее поле в JSON должно быть пустым (null, пустой массив или пустая строка).
        Ответ должен быть ТОЛЬКО в формате JSON, без каких-либо дополнительных пояснений или оберток (например, ```json ... ```).

        Текст резюме:
        ---
        {resume_text}
        ---

        JSON:
        """

    def _generate_summary_card(self, resume_text: str) -> str:
        return f"""
        Составь краткое резюме кандидата в 2-3 предложениях на основе предоставленного текста.
        Цель — быстро передать ключевую информацию о кандидате (опыт, специализация, основные навыки).

        Текст резюме:
        ---
        {resume_text}
        ---

        Краткое резюме:
        """

# --- Пример использования ---
if __name__ == "__main__":
    prompter = PromptTemplates()
    sample_resume_text = "Иван Иванов, Python Developer с 5-летним опытом работы в ООО \"ТехноСофт\". Навыки: Python, Django, SQL."
    sample_job_description = "Ищем Junior Python Developer. Требования: Python, SQL. Опыт от 1 года."
    
    print("--- Prompt for Generating Interview Questions ---")
    print(prompter.format_prompt("generate_interview_questions", resume_text=sample_resume_text))
    print("-" * 50)

    print("--- Prompt for Evaluating Suitability ---")
    print(prompter.format_prompt("evaluate_suitability", resume_text=sample_resume_text, job_description=sample_job_description))
    print("-" * 50)

    print("--- Prompt for Structuring Resume ---")
    print(prompter.format_prompt("structure_resume", resume_text=sample_resume_text))
    print("-" * 50)
