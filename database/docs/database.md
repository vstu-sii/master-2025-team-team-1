# Проектирование схемы базы данных для HR AI Assistant

## Введение

В данном документе представлено проектирование схемы базы данных для проекта **HR AI Assistant**, который включает в себе структуру для хранения данных о пользователях, вакансиях, кандидатах, результатах анализа и взаимодействиях с LLM.

---

## 1. Реляционная схема базы данных (PostgreSQL)

Реляционная модель обеспечивает строгую согласованность и целостность данных благодаря использованию нормализации и внешних ключей. Этот подход хорошо подходит для структурированных данных с четко определенными связями.

### 1.1. Описание таблиц

**Таблица `Users`**

Представляет HR-специалистов, использующих систему.

| Поле | Тип данных | Описание | Ограничения |
| :--- | :--- | :--- | :--- |
| `user_id` | UUID | Уникальный идентификатор пользователя | PRIMARY KEY |
| `username` | VARCHAR(255) | Имя пользователя | UNIQUE, NOT NULL |
| `email` | VARCHAR(255) | Электронная почта пользователя | UNIQUE, NOT NULL |
| `password_hash`| VARCHAR(255) | Хеш пароля пользователя | NOT NULL |
| `created_at` | TIMESTAMP | Дата и время создания записи | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Дата и время последнего обновления записи | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

**Таблица `Vacancies`**

Представляет вакансии, для которых производится анализ резюме.

| Поле | Тип данных | Описание | Ограничения |
| :--- | :--- | :--- | :--- |
| `vacancy_id` | UUID | Уникальный идентификатор вакансии | PRIMARY KEY |
| `user_id` | UUID | Идентификатор HR-специалиста, создавшего вакансию | FOREIGN KEY (`Users`) |
| `title` | VARCHAR(255) | Название вакансии | NOT NULL |
| `description` | TEXT | Полное описание вакансии | NOT NULL |
| `created_at` | TIMESTAMP | Дата и время создания записи | DEFAULT CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Дата и время последнего обновления записи | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP |

**Таблица `Candidates`**

Представляет спарсенные резюме кандидатов.

| Поле | Тип данных | Описание | Ограничения |
| :--- | :--- | :--- | :--- |
| `candidate_id` | UUID | Уникальный идентификатор кандидата | PRIMARY KEY |
| `user_id` | UUID | Идентификатор HR-специалиста, добавившего кандидата | FOREIGN KEY (`Users`) |
| `full_name` | VARCHAR(255) | Полное имя кандидата | NOT NULL |
| `resume_text` | TEXT | Полный текст резюме | NOT NULL |
| `source_url` | VARCHAR(2048) | URL источника резюме (hh.ru, Habr Career и др.) | |
| `parsed_at` | TIMESTAMP | Дата и время парсинга резюме | DEFAULT CURRENT_TIMESTAMP |

**Таблица `AnalysisResults`**

Содержит результаты анализа резюме кандидата по конкретной вакансии.

| Поле | Тип данных | Описание | Ограничения |
| :--- | :--- | :--- | :--- |
| `result_id` | UUID | Уникальный идентификатор результата | PRIMARY KEY |
| `candidate_id` | UUID | Идентификатор кандидата | FOREIGN KEY (`Candidates`) |
| `vacancy_id` | UUID | Идентификатор вакансии | FOREIGN KEY (`Vacancies`) |
| `score` | DECIMAL(5,2) | Скоринг соответствия (0-100%) | NOT NULL |
| `rating` | VARCHAR(50) | Рейтинг кандидата (Top, Medium, Low) | NOT NULL |
| `strengths` | TEXT | Выявленные сильные стороны | |
| `gaps` | TEXT | Выявленные пробелы | |
| `interview_questions` | JSONB | Сгенерированные вопросы для интервью (JSON массив) | |
| `analyzed_at` | TIMESTAMP | Дата и время проведения анализа | DEFAULT CURRENT_TIMESTAMP |

**Таблица `LLMData`**

Хранит промпты и ответы для взаимодействия с LLM.

| Поле | Тип данных | Описание | Ограничения |
| :--- | :--- | :--- | :--- |
| `llm_data_id` | UUID | Уникальный идентификатор записи LLM | PRIMARY KEY |
| `user_id` | UUID | Идентификатор пользователя, инициировавшего запрос | FOREIGN KEY (`Users`) |
| `candidate_id` | UUID | Идентификатор кандидата (если применимо) | FOREIGN KEY (`Candidates`) |
| `vacancy_id` | UUID | Идентификатор вакансии (если применимо) | FOREIGN KEY (`Vacancies`) |
| `prompt` | TEXT | Отправленный промпт к LLM | NOT NULL |
| `response` | TEXT | Полученный ответ от LLM | NOT NULL |
| `model_name` | VARCHAR(100) | Название используемой LLM модели | |
| `timestamp` | TIMESTAMP | Дата и время запроса/ответа | DEFAULT CURRENT_TIMESTAMP |

### 1.2. Индексы для производительности

*   `idx_users_email` ON `Users` (`email`)
*   `idx_users_username` ON `Users` (`username`)
*   `idx_vacancies_user_id` ON `Vacancies` (`user_id`)
*   `idx_candidates_user_id` ON `Candidates` (`user_id`)
*   `idx_analysisresults_candidate_id` ON `AnalysisResults` (`candidate_id`)
*   `idx_analysisresults_vacancy_id` ON `AnalysisResults` (`vacancy_id`)
*   `idx_llmdata_user_id` ON `LLMData` (`user_id`)

### 1.3. ER-диаграмма (PlantUML)

![Er-диаграмма](ER.jpg)

---

## 2. Схема для данных LLM (Промпты и ответы)


**Ключевые поля:**

*   **`prompt`**: Текст запроса, отправленного к LLM.
*   **`response`**: Текст ответа, полученного от LLM.
*   **`model_name`**: Идентификатор использованной модели (например, `gemini-2.5-flash`).
*   **Связи**: Ссылки на пользователя, кандидата и вакансию, к которым относится взаимодействие.


