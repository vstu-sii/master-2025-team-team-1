# C4 Architecture Documentation
## AI HR Assistant

## 1. Введение

### 1.1 Цель документа

Этот документ описывает архитектуру системы **AI HR Assistant** с использованием модели C4 (Context, Container, Component, Code). 

### 1.2 Scope системы

**AI HR Assistant** — это браузерное расширение и веб-приложение для автоматизации процесса отбора кандидатов, включающее:
- Парсинг резюме с job-порталов (HeadHunter, Rabota.ru и др.)
- AI-анализ соответствия вакансии
- Ранжирование кандидатов
- Генерация персонализированных вопросов для интервью
- Экспорт результатов в Google Sheets и Telegram

### 1.3 Архитектурные принципы

1. **Modular Architecture**: четкое разделение frontend и backend компонентов
2. **Browser-First**: использование браузерного расширения для парсинга в реальном времени
3. **AI-Powered**: интеграция с AI API для анализа и генерации контента
4. **Export Flexibility**: множественные каналы экспорта данных
5. **User-Centric**: фокус на удобстве HR-специалистов и менеджеров по найму

---

## 2. Level 1: System Context

### 2.1 Context Diagram
![Context Diagram](https://github.com/vstu-sii/master-2025-team-team-1/blob/e091cf3428bca239d043c1d945f994f51b1085e4/docs/architecture/C1.png)

### 2.2 Users and External Systems

#### Users (Пользователи)

| Пользователь | Описание | Основные действия |
|--------------|----------|-------------------|
| **HR-специалист** | Рекрутер в агентстве или HR-отделе компании | Создание вакансий, парсинг резюме, запуск анализа, экспорт данных |
| **Менеджер по найму** | Руководитель команды, проводит собеседования | Просмотр рейтингов кандидатов, получение вопросов для интервью |

#### External Systems (Внешние системы)

| Система | Описание | Протокол/API |
|---------|----------|--------------|
| **Job Sites** | HeadHunter, Rabota.ru и другие job-порталы | HTTPS, HTML/DOM parsing |
| **AI API** | OpenAI/Anthropic для анализа резюме и генерации вопросов | REST API, HTTPS |
| **Google Sheets** | Экспорт структурированных данных кандидатов | Google Sheets API, OAuth 2.0 |
| **Telegram** | Уведомления и быстрый экспорт результатов | Telegram Bot API, HTTPS |

---

## 3. Level 2: Container

### 3.1 Container Diagram

![Container Diagram](https://github.com/vstu-sii/master-2025-team-team-1/blob/e091cf3428bca239d043c1d945f994f51b1085e4/docs/architecture/C2.png)

### 3.2 Container Descriptions

#### Frontend Containers

##### Web Application
- **Technology**: React SPA (Single Page Application)
- **Purpose**: Основной интерфейс для управления вакансиями и просмотра аналитики
- **Key Features**:
  - Создание и редактирование вакансий
  - Настройка параметров парсинга и анализа
  - Просмотр данных кандидатов с фильтрацией и сортировкой
  - Визуализация рейтингов и статистики
  - Управление экспортом данных
- **Communication**: REST API calls к Backend API через HTTPS

##### Browser Extension
- **Technology**: Chrome Extension (JavaScript, React для UI)
- **Purpose**: Парсинг резюме непосредственно на job-сайтах
- **Key Features**:
  - **DOM Scraper**: Извлечение структурированных данных из HTML страниц
  - **Automation Engine**: Автоматическая прокрутка страниц и навигация
  - **Popup UI**: Интерфейс для запуска парсинга и выбора активной вакансии
  - Отправка собранных данных на Backend API
- **Communication**: 
  - DOM parsing для извлечения данных с job-сайтов
  - REST/JSON для отправки данных на Backend API

#### Backend Container

##### Backend API
- **Technology**: Node.js + Express
- **Purpose**: Центральная бизнес-логика приложения
- **Key Responsibilities**:
  - Управление пользователями и аутентификацией
  - CRUD операции для вакансий
  - Прием и обработка данных резюме от расширения
  - Интеграция с AI API для анализа
  - Управление экспортом данных
  - Хранение и извлечение данных из БД
- **Endpoints**: 
  - `/api/auth/*` - аутентификация
  - `/api/vacancies/*` - управление вакансиями
  - `/api/resumes/*` - прием и обработка резюме
  - `/api/candidates/*` - поиск и фильтрация кандидатов
  - `/api/export/*` - экспорт данных

#### Data Container

##### Database
- **Technology**: PostgreSQL
- **Purpose**: Persistent storage для всех данных системы
- **Schema**:
  - `users` - пользователи и аутентификация
  - `vacancies` - описания вакансий с параметрами
  - `candidates` - профили кандидатов с parsed данными
  - `analysis_results` - результаты AI-анализа и скоринг
  - `export_history` - история экспортов

---

## 4. Level 3: Component (Core Services)

### 4.1 Backend API Components

![Component Diagram](https://github.com/vstu-sii/master-2025-team-team-1/blob/e091cf3428bca239d043c1d945f994f51b1085e4/docs/architecture/C3.png)

### 4.2 Component Descriptions

#### Backend API Components

##### Controllers
| Component | Responsibility | Key Endpoints |
|-----------|----------------|---------------|
| **Auth Controller** | Регистрация, авторизация, управление сессиями | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout` |

##### Business Logic Modules
| Component | Responsibility | Key Methods |
|-----------|----------------|-------------|
| **Vacancy Service** | Управление жизненным циклом вакансий | `createVacancy()`, `updateVacancy()`, `getVacancies()`, `deleteVacancy()` |
| **Data Ingestion Handler** | Прием сырых данных резюме от расширения | `receiveResumeData()`, `validateData()`, `storeRawData()` |
| **AI Analysis Engine** | Ранжирование кандидатов и генерация инсайтов | `scoreCandidate()`, `identifySkillGaps()`, `generateInterviewQuestions()` |
| **Candidate Service** | Поиск, фильтрация и отображение данных кандидатов | `searchCandidates()`, `filterByScore()`, `getCandidateProfile()` |
| **Export Manager** | Формирование экспортов и интеграция с внешними API | `exportToCSV()`, `exportToGoogleSheets()`, `sendToTelegram()` |

#### Browser Extension Components

##### Content Scripts
| Component | Responsibility | Key Functions |
|-----------|----------------|---------------|
| **DOM Scraper** | Извлечение данных из HTML страниц job-сайтов | `extractResumeData()`, `parseContactInfo()`, `extractSkills()` |
| **Automation Engine** | Управление автопрокруткой и навигацией | `autoScroll()`, `navigateToNextPage()`, `detectPageEnd()` |

##### Extension UI
| Component | Responsibility | Key Features |
|-----------|----------------|---------------|
| **Popup UI** | Интерфейс управления расширением | Выбор вакансии, запуск парсинга, отображение прогресса |

---

## 5. Technology Stack & Justification

### 5.1 Technology Selection Matrix

| Layer | Technology | Alternative Considered | Decision Rationale |
|-------|-----------|------------------------|-------------------|
| **Frontend (Web)** | React SPA | Vue.js, Angular | Богатая экосистема, большое комьюнити, отличная документация |
| **Frontend (Extension)** | Chrome Extension + React | Vanilla JS | Единая кодовая база с Web App, переиспользование компонентов |
| **Backend Framework** | Node.js + Express | FastAPI, Django | JavaScript full-stack, простота разработки, высокая производительность для I/O операций |
| **Database** | PostgreSQL | MySQL, MongoDB | ACID compliance, rich query capabilities, JSON support для гибкого хранения parsed данных |
| **AI Provider** | OpenAI/Anthropic API | Self-hosted models | Быстрая интеграция, высокое качество анализа, отсутствие необходимости в GPU инфраструктуре |

### 5.2 Programming Languages

| Language | Usage | Version | Justification |
|----------|-------|---------|---------------|
| **JavaScript** | Frontend (React, Extension) | ES2022+ | Универсальный язык для web и browser extensions |
| **Node.js** | Backend | 18 LTS+ | JavaScript full-stack, async I/O, npm ecosystem |
| **SQL** | Database queries | PostgreSQL 14+ | Структурированные запросы, транзакции |

### 5.3 Key Libraries & Frameworks

#### Backend (Node.js)
```json
{
  "dependencies": {
    "express": "^4.18.0",
    "pg": "^8.11.0",
    "bcrypt": "^5.1.0",
    "jsonwebtoken": "^9.0.0",
    "axios": "^1.6.0",
    "dotenv": "^16.0.0"
  }
}
```

#### Frontend (React)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0"
  }
}
```

---

## 6. Component Interfaces

### 6.1 Backend API Interfaces

#### Authentication

```yaml
# POST /api/auth/register
Request:
  email: string
  password: string
  name: string

Response:
  user_id: uuid
  email: string
  name: string
  created_at: timestamp

# POST /api/auth/login
Request:
  email: string
  password: string

Response:
  access_token: string (JWT)
  user:
    id: uuid
    email: string
    name: string
    role: enum[hr_specialist, hiring_manager]
```

#### Vacancy Management

```yaml
# POST /api/vacancies
Headers:
  Authorization: Bearer <token>

Request:
  title: string
  description: string
  required_skills: string[]
  experience_years: integer
  parsing_parameters:
    max_resumes: integer
    auto_scroll: boolean

Response:
  id: uuid
  title: string
  status: enum[active, paused, closed]
  created_at: timestamp

# GET /api/vacancies
Response:
  vacancies: [
    {
      id: uuid
      title: string
      candidates_count: integer
      status: string
      created_at: timestamp
    }
  ]
```

#### Resume Data Ingestion

```yaml
# POST /api/resumes
Headers:
  Authorization: Bearer <token>

Request:
  vacancy_id: uuid
  source_url: string
  parsed_data:
    name: string
    contact:
      email: string
      phone: string
    skills: string[]
    experience: [
      {
        position: string
        company: string
        duration: string
        description: string
      }
    ]
    education: [
      {
        institution: string
        degree: string
        year: integer
      }
    ]

Response:
  candidate_id: uuid
  status: enum[received, analyzing, completed]
  created_at: timestamp
```

#### Candidate Analysis

```yaml
# GET /api/candidates?vacancy_id={uuid}
Headers:
  Authorization: Bearer <token>

Response:
  candidates: [
    {
      id: uuid
      name: string
      score: float (0-100)
      match_analysis:
        matched_skills: string[]
        missing_skills: string[]
        experience_match: string
      interview_questions: string[]
      source_url: string
    }
  ]
  total_count: integer
```

#### Export

```yaml
# POST /api/export/sheets
Headers:
  Authorization: Bearer <token>

Request:
  vacancy_id: uuid
  candidate_ids: uuid[] (optional, if empty - all candidates)
  spreadsheet_id: string (optional, creates new if not provided)

Response:
  spreadsheet_url: string
  rows_exported: integer
  export_id: uuid

# POST /api/export/telegram
Request:
  vacancy_id: uuid
  chat_id: string
  format: enum[summary, detailed]

Response:
  message_id: string
  sent_at: timestamp
```

### 6.2 Browser Extension Interfaces

#### Extension to Backend Communication

```javascript
// Extension sends parsed data to Backend API
const sendResumeData = async (resumeData) => {
  const response = await fetch('https://api.aihr.com/api/resumes', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      vacancy_id: currentVacancyId,
      source_url: window.location.href,
      parsed_data: resumeData
    })
  });
  
  return await response.json();
};
```

#### DOM Scraping Interface

```javascript
// DOM Scraper extracts resume data
const extractResumeData = () => {
  return {
    name: document.querySelector('.resume-header__name')?.textContent,
    contact: {
      email: document.querySelector('[data-qa="resume-contact-email"]')?.textContent,
      phone: document.querySelector('[data-qa="resume-contact-phone"]')?.textContent
    },
    skills: Array.from(document.querySelectorAll('.skills-list__item'))
      .map(el => el.textContent.trim()),
    experience: Array.from(document.querySelectorAll('.resume-block-item-gap'))
      .map(extractExperienceItem)
  };
};
```

---

## 7. Data Flow Examples

### 7.1 Resume Parsing Flow

```
1. HR opens job-site in browser with Extension installed
2. HR clicks Extension icon, selects vacancy, starts parsing
3. Extension (Automation Engine) scrolls through resume listings
4. Extension (DOM Scraper) extracts data from each resume page
5. Extension sends parsed data to Backend API (Data Ingestion Handler)
6. Backend stores raw data in Database
7. Backend sends data to AI API for analysis (AI Analysis Engine)
8. AI API returns scoring and insights
9. Backend stores analysis results in Database
10. Web App displays updated candidate list with scores
```

### 7.2 Export Flow

```
1. HR opens candidate list in Web App
2. HR clicks "Export to Google Sheets"
3. Web App sends request to Backend API (Export Manager)
4. Export Manager retrieves candidate data from Database
5. Export Manager formats data and calls Google Sheets API
6. Google Sheets API creates/updates spreadsheet
7. Export Manager returns spreadsheet URL to Web App
8. Web App displays success message with link
```

---

## 8. Security Considerations

### 8.1 Authentication & Authorization

- **JWT-based authentication** для stateless API
- **Role-based access control**: HR-specialist vs Hiring Manager
- **Token refresh mechanism** для продления сессий
- **Secure password storage**: bcrypt hashing

### 8.2 Data Protection

- **HTTPS only** для всех API коммуникаций
- **Input validation** на уровне API endpoints
- **SQL injection protection**: parameterized queries
- **Rate limiting** для предотвращения abuse

### 8.3 Privacy

- **Минимизация PII**: хранение только необходимых данных
- **Anonymization option** для экспорта данных
- **GDPR compliance**: right to deletion, data portability

---

## 9. Deployment Architecture

### 9.1 Infrastructure

```
┌─────────────────┐
│  Cloud Provider │
│  (AWS/GCP/Azure)│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│Web App│ │Backend│
│(Static)│ │  API  │
│Hosting│ │ (EC2) │
└───────┘ └───┬───┘
              │
         ┌────▼────┐
         │PostgreSQL│
         │   RDS    │
         └──────────┘
```

### 9.2 Scalability Considerations

- **Horizontal scaling**: Backend API за Load Balancer
- **Database read replicas** для высоких нагрузок на чтение
- **CDN** для статических файлов Web App
- **Caching layer** (Redis) для frequently accessed данных

---

## 10. Monitoring & Observability

### 10.1 Metrics

- **API performance**: request latency, throughput
- **Parsing success rate**: successful vs failed parses
- **AI API usage**: request count, cost tracking
- **Database performance**: query execution time, connection pool

### 10.2 Logging

- **Application logs**: structured JSON logging
- **Error tracking**: integration with Sentry/Rollbar
- **Audit logs**: user actions, data modifications

---

## 11. Future Enhancements

### 11.1 Planned Features

- **Multi-language support**: интерфейс на английском и русском
- **Advanced filtering**: более гибкие фильтры для кандидатов
- **Interview scheduling**: интеграция с календарями
- **Mobile app**: нативное приложение для iOS/Android
- **Self-hosted AI**: опция для on-premise AI deployment

### 11.2 Architecture Evolution

- **Microservices migration**: разделение Backend на отдельные сервисы
- **Event-driven architecture**: использование message queue (RabbitMQ/Kafka)
- **GraphQL API**: альтернатива REST для гибких запросов
- **Real-time updates**: WebSocket для live notifications
