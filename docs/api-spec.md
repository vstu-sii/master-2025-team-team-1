# API Спецификация

---

## Rate Limiting и защита API

| Endpoint      | Лимит      | Описание                  |
| ------------- | ---------- | ------------------------- |
| /auth/*       | 5 req/min  | защита от brute-force     |
| /vacancies/*  | 60 req/min | работа HR                 |
| /parse/start  | 5 req/min  | предотвращение перегрузки |
| /parse/status | 30 req/min | периодические проверки    |
| /data/export  | 3 req/min  | ограничение на экспорт    |
| /data         | 60 req/min | просмотр данных           |

---

## 4.2 Пример запросов

**Запрос HTTP**

```http
POST /vacancies HTTP/1.1
Host: api.resume-parser.app
Content-Type: application/json
Authorization: Bearer <token>

```

**Body**

```json
{
  "title": "Python Backend Developer",
  "description": "Разработка сервисов для автоматизации найма",
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "experience": "2-4 года",
  "location": "Remote"
}

```

**Ответ**

200/201 Created

```json
{
  "vacancy_id": "vac_00192",
  "title": "Python Backend Developer",
  "description": "Разработка сервисов для автоматизации найма",
  "skills": ["Python", "FastAPI", "PostgreSQL"],
  "experience": "2-4 года",
  "location": "Remote",
  "created_at": "2025-02-15T12:44:31Z",
  "status": "active"
}
```

**Ошибки**

| Код | Значение                |
| --- | ----------------------- |
| 400 | Некорректные данные     |
| 401 | Неавторизован           |
| 404 | Не найдено              |
| 429 | Превышен лимит запросов |
| 500 | Ошибка сервера          |

