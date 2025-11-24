-- SQL DDL (Data Definition Language) Script for HR AI Assistant Database (PostgreSQL)

-- Расширение для работы с UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Таблица Users (Пользователи - HR-специалисты)
CREATE TABLE Users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для производительности
CREATE INDEX idx_users_email ON Users (email);
CREATE INDEX idx_users_username ON Users (username);

-- Триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON Users
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();


-- 2. Таблица Vacancies (Вакансии)
CREATE TABLE Vacancies (
    vacancy_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user
        FOREIGN KEY(user_id) 
        REFERENCES Users(user_id)
        ON DELETE CASCADE
);

-- Индексы для производительности
CREATE INDEX idx_vacancies_user_id ON Vacancies (user_id);
CREATE INDEX idx_vacancies_title ON Vacancies (title);

CREATE TRIGGER update_vacancies_updated_at
BEFORE UPDATE ON Vacancies
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();


-- 3. Таблица Candidates (Кандидаты/Резюме)
CREATE TABLE Candidates (
    candidate_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    resume_text TEXT NOT NULL,
    source_url VARCHAR(2048),
    parsed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user
        FOREIGN KEY(user_id) 
        REFERENCES Users(user_id)
        ON DELETE CASCADE
);

-- Индексы для производительности
CREATE INDEX idx_candidates_user_id ON Candidates (user_id);
CREATE INDEX idx_candidates_full_name ON Candidates (full_name);


-- 4. Таблица AnalysisResults (Результаты анализа и скоринга)
CREATE TABLE AnalysisResults (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id UUID NOT NULL,
    vacancy_id UUID NOT NULL,
    score DECIMAL(5,2) NOT NULL, -- Скоринг соответствия (0.00 - 100.00)
    rating VARCHAR(50) NOT NULL, -- Рейтинг (Top, Medium, Low)
    strengths TEXT, -- Выявленные сильные стороны
    gaps TEXT, -- Выявленные пробелы
    interview_questions JSONB, -- Сгенерированные вопросы (JSON массив)
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_candidate
        FOREIGN KEY(candidate_id) 
        REFERENCES Candidates(candidate_id)
        ON DELETE CASCADE,
    
    CONSTRAINT fk_vacancy
        FOREIGN KEY(vacancy_id) 
        REFERENCES Vacancies(vacancy_id)
        ON DELETE CASCADE
);

-- Индексы для производительности
CREATE INDEX idx_analysisresults_candidate_id ON AnalysisResults (candidate_id);
CREATE INDEX idx_analysisresults_vacancy_id ON AnalysisResults (vacancy_id);
CREATE INDEX idx_analysisresults_score ON AnalysisResults (score);


-- 5. Таблица LLMData (История взаимодействия с LLM)
CREATE TABLE LLMData (
    llm_data_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    candidate_id UUID,
    vacancy_id UUID,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model_name VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_user
        FOREIGN KEY(user_id) 
        REFERENCES Users(user_id)
        ON DELETE CASCADE,
        
    CONSTRAINT fk_candidate
        FOREIGN KEY(candidate_id) 
        REFERENCES Candidates(candidate_id)
        ON DELETE SET NULL, -- Кандидат может быть удален, но история LLM остается
        
    CONSTRAINT fk_vacancy
        FOREIGN KEY(vacancy_id) 
        REFERENCES Vacancies(vacancy_id)
        ON DELETE SET NULL -- Вакансия может быть удалена, но история LLM остается
);

-- Индексы для производительности
CREATE INDEX idx_llmdata_user_id ON LLMData (user_id);
CREATE INDEX idx_llmdata_candidate_id ON LLMData (candidate_id);
CREATE INDEX idx_llmdata_vacancy_id ON LLMData (vacancy_id);
CREATE INDEX idx_llmdata_timestamp ON LLMData (timestamp);

