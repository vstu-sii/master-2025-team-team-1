# C4 Architecture Documentation
## AI HR Assistant

## 1. Введение

### 1.1 Цель документа

Этот документ описывает архитектуру системы **AI HR Assistant** с использованием модели C4 (Context, Container, Component, Code). 

### 1.2 Scope системы

**AI HR Assistant** — это браузерное расширение и веб-приложение для автоматизации процесса отбора кандидатов, включающее:
- Парсинг резюме с job-порталов (hh.ru, Habr Career и др.)
- AI-анализ соответствия вакансии
- Ранжирование кандидатов
- Генерация персонализированных вопросов для интервью
- Экспорт результатов

### 1.3 Архитектурные принципы

1. **Microservices-ready**: модульная архитектура с возможностью разделения на микросервисы
2. **Privacy-first**: минимизация хранения PII, поддержка on-premise deployment
3. **Hybrid ML approach**: self-hosted модели + cloud LLM fallback
4. **API-first**: все функции доступны через REST API
5. **Observability**: встроенный мониторинг и трассировка

---

## 2. Level 1: System Context

### 2.1 Context Diagram
<img width="1114" height="781" alt="С1" src="https://github.com/user-attachments/assets/4da39e9d-a76f-4e69-972c-13440f68602f" />


### 2.2 Users and External Systems

#### Users (Пользователи)

| Пользователь | Описание | Основные действия |
|--------------|----------|-------------------|
| **HR-специалист** | Рекрутер в агентстве или HR-отделе компании | Парсинг резюме, анализ кандидатов, экспорт результатов |
| **Менеджер по найму** | Руководитель команды, проводит собеседования | Просмотр результатов анализа, получение вопросов для интервью |

#### External Systems (Внешние системы)

| Система | Описание | Протокол/API |
|---------|----------|--------------|
| **Job Порталы** | hh.ru, Habr Career, LinkedIn | HTTPS, HTML parsing |
| **LLM Service** | Генерация текста: вопросы, объяснения | HTTPS (REST), gRPC (self-hosted) |
| **Embedding Service** | Векторизация текста резюме и вакансий | HTTPS (REST), gRPC (self-hosted) |
| **Export Services** | Google Sheets API, Telegram Bot API | HTTPS, REST API |
| **Auth Provider** | Google OAuth, Microsoft Entra ID | OAuth 2.0, OpenID Connect |

---

## 3. Level 2: Container

### 3.1 Container Diagram

<img width="1336" height="1548" alt="C2" src="https://github.com/user-attachments/assets/57da75c5-a751-485e-94df-860e1aebf2ca" />


### 3.2 Container Descriptions

#### Frontend Containers

##### Browser Extension
- **Technology**: React 18, TypeScript, Webpack
- **Purpose**: Парсинг резюме непосредственно с job-порталов, локальный UI
- **Key Features**:
  - Content scripts для извлечения данных с hh.ru, Habr Career
  - Popup UI для быстрого анализа
  - Local storage для кэширования
  - Real-time communication с Core API

##### Web Dashboard
- **Technology**: Next.js 14, React 18, TypeScript, TailwindCSS
- **Purpose**: Полнофункциональный веб-интерфейс для управления
- **Key Features**:
  - Управление вакансиями
  - Просмотр и фильтрация результатов
  - Экспорт в различные форматы
  - Analytics dashboard

#### Backend Containers

##### API Gateway
- **Technology**: Nginx (MVP) / Kong (Scale)
- **Purpose**: Единая точка входа, security, rate limiting
- **Key Features**:
  - Request routing
  - JWT validation
  - Rate limiting (100 req/hour per user)
  - CORS handling
  - Request/response logging

##### Core API
- **Technology**: FastAPI 0.104+, Python 3.11+, Pydantic v2
- **Purpose**: Основная бизнес-логика приложения
- **Key Responsibilities**:
  - Resume parsing orchestration
  - Vacancy management (CRUD)
  - User management
  - Export coordination
  - Authentication/Authorization
- **Endpoints**: `/api/v1/resumes`, `/api/v1/vacancies`, `/api/v1/analysis`, `/api/v1/export`

##### ML Service
- **Technology**: FastAPI, Python 3.11+, LangChain, Sentence-Transformers
- **Purpose**: ML-операции: embeddings, scoring, RAG
- **Key Responsibilities**:
  - Resume embedding generation
  - Semantic search (RAG)
  - Candidate scoring
  - Skills extraction (NER)
  - LLM orchestration через LangChain
- **Models**:
  - `all-mpnet-base-v2` для embeddings (768 dim)
  - Custom NER model для извлечения навыков

##### LLM Service
- **Technology**: vLLM, Python 3.11+, Mistral-7B-Instruct
- **Purpose**: Генерация текста (вопросы, объяснения)
- **Key Features**:
  - Self-hosted Mistral-7B inference
  - Prompt templating
  - Response streaming
  - Fallback на OpenAI API при сложных запросах
- **Hardware**: GPU с 16GB+ VRAM (A10, L4, RTX 4090)

##### Background Worker
- **Technology**: Celery, Redis broker, Python 3.11+
- **Purpose**: Асинхронная обработка длительных задач
- **Tasks**:
  - Batch analysis (100+ резюме)
  - Export to Google Sheets
  - Email notifications
  - Scheduled re-ranking

#### Data Containers

##### PostgreSQL
- **Technology**: PostgreSQL 16 with pgvector extension
- **Purpose**: Primary data storage
- **Schema**:
  - `users` - пользователи и аутентификация
  - `vacancies` - описания вакансий
  - `resumes` - спарсенные резюме
  - `analysis_results` - результаты анализа
  - `export_history` - история экспортов

##### Redis
- **Technology**: Redis 7 (with Redis Stack для JSON)
- **Purpose**: Кэширование и очереди
- **Use Cases**:
  - Embedding cache (TTL: 24h)
  - Session storage
  - Rate limiting counters
  - Celery task queue

##### Vector DB
- **Technology**: 
  - **MVP**: Pinecone (cloud, managed)
  - **On-Premise**: FAISS (in-memory, persistent)
- **Purpose**: Векторный поиск для RAG
- **Data**: Embeddings резюме и вакансий (768-dim vectors)
- **Index**: HNSW algorithm, cosine similarity

#### Monitoring Container

##### Monitoring Stack
- **Components**:
  - **Prometheus**: метрики системы и приложения
  - **Grafana**: визуализация метрик, дашборды
  - **Langfuse**: трассировка LLM запросов, prompt management
  - **Loki**: централизованные логи
- **Metrics**:
  - API latency (p50, p95, p99)
  - Throughput (req/sec)
  - ML model inference time
  - Error rates
  - LLM token usage

---

## 4. Level 3: Component (Core Services)

### 4.1 Core API Components

<img width="1584" height="1126" alt="С3" src="https://github.com/user-attachments/assets/62520283-e55c-4348-8120-a83d6e00241d" />


### 4.2 ML Service Components

<img width="1342" height="1115" alt="С3 2" src="https://github.com/user-attachments/assets/35bb61a1-fd52-48b0-b226-09e314e9d625" />


### 4.3 Component Descriptions

#### Core API Components

##### Controllers (API Routers)
| Component | Responsibility | Key Endpoints |
|-----------|----------------|---------------|
| **Auth Controller** | Аутентификация, JWT management | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| **Resume Controller** | CRUD резюме | `POST /resumes`, `GET /resumes/{id}`, `DELETE /resumes/{id}` |
| **Vacancy Controller** | CRUD вакансий | `POST /vacancies`, `GET /vacancies`, `PUT /vacancies/{id}` |
| **Analysis Controller** | Анализ кандидатов | `POST /analysis`, `GET /analysis/{id}`, `GET /analysis/results` |
| **Export Controller** | Экспорт данных | `POST /export/csv`, `POST /export/sheets`, `GET /export/history` |

##### Business Logic Modules
| Component | Responsibility | Key Methods |
|-----------|----------------|-------------|
| **Resume Parser** | Парсинг HTML/PDF резюме | `parse_html()`, `parse_pdf()`, `extract_fields()` |
| **Vacancy Matcher** | Сопоставление с вакансией | `match_resume()`, `calculate_fit_score()` |
| **Export Manager** | Генерация экспорта | `to_csv()`, `to_json()`, `to_google_sheets()` |
| **Auth Service** | JWT operations | `create_token()`, `verify_token()`, `refresh_token()` |
| **ML Client** | Обёртка для ML API | `embed_text()`, `score_candidate()`, `generate_questions()` |

#### ML Service Components

##### Controllers
| Component | Responsibility | Key Endpoints |
|-----------|----------------|---------------|
| **Embedding Controller** | Генерация embeddings | `POST /embeddings` |
| **Scoring Controller** | Скоринг кандидатов | `POST /score` |
| **RAG Controller** | RAG цепочки | `POST /rag/questions`, `POST /rag/explanation` |
| **NER Controller** | Извлечение сущностей | `POST /ner/skills` |

##### AI Engines
| Component | Responsibility | Technology |
|-----------|----------------|------------|
| **Embedding Engine** | Векторизация текста | Sentence-Transformers (all-mpnet-base-v2) |
| **Scoring Engine** | Алгоритм скоринга | Custom algorithm: cosine similarity + rule-based |
| **RAG Chain** | RAG orchestration | LangChain: RetrievalQA chain |
| **NER Engine** | Извлечение навыков | spaCy (ru_core_news_lg) + custom rules |

---

## 5. Technology Stack & Justification

### 5.1 Technology Selection Matrix

| Layer | Technology | Alternative Considered | Decision Rationale | ADR |
|-------|-----------|------------------------|-------------------|-----|
| **Frontend (Extension)** | React 18 + TypeScript | Vue.js, Svelte | Богатая экосистема, team expertise, лучшая поддержка для расширений | ADR-001 |
| **Frontend (Web)** | Next.js 14 | Create React App, Remix | SSR/SSG для SEO, API routes, production-ready | ADR-001 |
| **API Framework** | FastAPI | Flask, Django REST | Async support, автогенерация OpenAPI, Pydantic validation, высокая производительность | ADR-002 |
| **Database** | PostgreSQL 16 | MySQL, MongoDB | ACID, pgvector extension, JSON support, strong typing | ADR-003 |
| **Cache** | Redis 7 | Memcached | Persistence, pub/sub, Redis Stack (JSON, Search), Celery broker | ADR-004 |
| **Vector DB (MVP)** | Pinecone | Weaviate, Milvus | Managed service, быстрый старт, хорошая документация | ADR-005 |
| **Vector DB (On-Prem)** | FAISS | Annoy, Hnswlib | In-memory, высокая скорость, Facebook-backed | ADR-005 |
| **Embedding Model** | all-mpnet-base-v2 | all-MiniLM-L6-v2 | Баланс accuracy/speed, 768-dim, multilingual support | ADR-006 |
| **LLM (Primary)** | Mistral-7B-Instruct | Llama-2-7B, Falcon-7B | Лучший benchmark результат, коммерческая лицензия, русский язык | ADR-007 |
| **LLM (Fallback)** | OpenAI GPT-4o-mini | Anthropic Claude | Баланс cost/quality, низкая latency, API стабильность | ADR-007 |
| **LLM Serving** | vLLM | Text-Generation-Inference | Highest throughput, continuous batching, PagedAttention | ADR-008 |
| **Orchestration** | LangChain | LlamaIndex | Широкая поддержка LLM, rich ecosystem, RAG patterns | ADR-009 |
| **Task Queue** | Celery + Redis | RQ, Dramatiq | Production-proven, monitoring tools, distributed | ADR-010 |
| **Monitoring (Metrics)** | Prometheus + Grafana | Datadog, New Relic | Open-source, self-hosted, rich ecosystem | ADR-011 |
| **Monitoring (LLM)** | Langfuse | LangSmith, Weights & Biases | Open-source, prompt management, cost tracking | ADR-011 |
| **API Gateway** | Nginx (MVP) / Kong | Traefik, AWS API Gateway | Industry standard, high performance, extensible | ADR-012 |
| **Container Runtime** | Docker + Docker Compose | Kubernetes (overkill для MVP) | Simple deployment, team familiarity, достаточно для MVP | ADR-013 |

### 5.2 Programming Languages

| Language | Usage | Version | Justification |
|----------|-------|---------|---------------|
| **Python** | Backend, ML | 3.11+ | ML ecosystem, FastAPI, async support, type hints |
| **TypeScript** | Frontend | 5.0+ | Type safety, tooling, maintainability |
| **SQL** | Database | PostgreSQL 16 | ACID transactions, complex queries, pgvector |

### 5.3 Key Libraries & Frameworks

#### Backend (Python)
```python
# requirements.txt (core dependencies)
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.4

# ML/AI
langchain==0.1.0
sentence-transformers==2.2.2
transformers==4.36.0
torch==2.1.0
spacy==3.7.2
faiss-cpu==1.7.4  # or faiss-gpu
pinecone-client==2.2.4

# LLM
openai==1.3.0
vllm==0.2.6

# Monitoring
prometheus-client==0.19.0
langfuse==2.0.0

# Utilities
httpx==0.25.2
python-jose==3.3.0
passlib==1.7.4
python-multipart==0.0.6
```

#### Frontend (TypeScript)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "next": "^14.0.0",
    "typescript": "^5.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.0",
    "tailwindcss": "^3.3.0",
    "lucide-react": "^0.263.1",
    "axios": "^1.6.0",
    "recharts": "^2.10.0"
  }
}
```

---

## 6. Component Interfaces

### 6.1 Core API Interfaces

#### Authentication

```yaml
# POST /api/v1/auth/login
Request:
  email: string
  password: string

Response:
  access_token: string (JWT)
  refresh_token: string
  expires_in: integer (seconds)
  user:
    id: uuid
    email: string
    name: string
    role: enum[hr_specialist, hiring_manager, admin]

# POST /api/v1/auth/refresh
Request:
  refresh_token: string

Response:
  access_token: string
  expires_in: integer
```

#### Resume Management

```yaml
# POST /api/v1/resumes
Headers:
  Authorization: Bearer <token>

Request:
  source_url: string (optional)
  html_content: string (optional)
  pdf_base64: string (optional)
  candidate_name: string (optional)

Response:
  id: uuid
  parsed_data:
    name: string
    email: string
    phone: string
    skills: string[]
    experience: Experience[]
    education: Education[]
  created_at
```
