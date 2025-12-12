# AI App

Использование Docker Compose

## Состав

- **Frontend**: Next.js (порт 3000)
- **Backend**: FastAPI (порт 8000)
- **Database**: PostgreSQL (порт 5432)
- **LLM Service**: Jupyter Notebook для экспериментов (порт 8888)

## Как запустить

1. Убедись, что установлены [Docker](https://www.docker.com/products/docker-desktop) и Docker Compose. Docker Desktop должен быть запущен.
2. В корне проекта выполни:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

🩺 Health checks (автоматическая проверка)
Сервисы автоматически проверяют своё состояние:

- **Backend**: http://localhost:8000/health
- **Frontend**: проверяется доступность порта 3000
- **База данных**: проверяется подключение

3. Открой в браузере:
Frontend: http://localhost:3000
Backend API: http://localhost:8000/api/hello
Jupyter: http://localhost:8888

4. Меняй код - изменения применяются автоматически!

5. Для остановки приложения нажми Ctrl+C в терминале и выполни:

```
docker-compose -f docker-compose.dev.yml down
```

## Запуск мониторинга
```
cd monitoring
docker-compose up -d
```
Открой в браузере:
- **Grafana**: http://localhost:3001 (логин: admin, пароль: admin)
- **Prometheus**: http://localhost:9090

**Для проверки, что метрики собираются можешь запустить**: 
- http://localhost:8000/metrics предоставляет метрики в формате Prometheus для сбора системой мониторинга, включая количество запросов, время ответа, использование памяти и CPU;
- http://localhost:8000/api/metrics/summary возвращает сводку этих метрик в удобном JSON формате для быстрой проверки состояния приложения;
- http://localhost:8000/api/health является эндпоинтом проверки работоспособности (health check), который показывает общий статус сервиса, доступность Langfuse и базовую системную информацию, используемый оркестраторами и системами мониторинга для определения доступности сервиса;
- http://localhost:9090/targets - Endpoint http://backend:8000/metrics должен находится в статусе "Up";

**Metrics Dashbord в Grafana**:
В http://localhost:3001/dashboards можно открыть созданный Metric Dashbord и посмотреть графики показателей: 

- Запросов в секунду (Requests per second): сколько HTTP запросов обрабатывает ваш backend каждую секунду, это основная метрика нагрузки на приложение;
- Среднее время ответа (Average response time): среднее время в секундах, за которое backend обрабатывает один запрос, показывает общую производительность API;
- 95-й перцентиль времени ответа (95th percentile latency): время ответа для 95% самых быстрых запросов. Например, если значение равно 0.8 секунды, это значит что 95% запросов обрабатываются быстрее 0.8 секунды.

**Для закрытия мониторинга**:
```
cd monitoring
docker-compose down
```

## Запуск Langfuse
```
docker-compose -f docker-compose.langfuse.yml up --build
```
**Доступ к Langfuse UI**: http://localhost:3002
1. Открой http://localhost:3002;
2. Введи электронную почту: admin@admin.com, пароль: adminadmin.

**Тестирование Langfuse UI**: http://localhost:3002
1. Открой http://localhost:8000/api/langfuse-test;
2. Скопируй trace_id из ответа;
3. Открой Langfuse UI: http://localhost:3002;
4. Вставь trace_id в поиск;
5. Нажми на трассировку для просмотра деталей.

**Просмотр свежих трассировок в режиме реального времени**:
1. Открой http://localhost:3002;
2. Перейди в "Traces";
3. Используй фильтры (timestamp: last 5 minutes, status: error (для поиска ошибок), name: contains "chat" (для конкретных эндпоинтов)).

**Просмотр дашбордов**:
1. В Langfuse UI нажми "Dashboards";
2. Выбери промежуток времени и, если нужно, фильтры.

- Для остановки Langfuse нажми Ctrl+C в терминале и выполни:
```
docker-compose -f docker-compose.langfuse.yml down
```

## Если есть ошибка (500 Internal Server Error for API route and version): 

🐳 Перезапусти Docker через системный трей:

1. **Найди иконку Docker** в правом нижнем углу экрана 
   - 🐳 Белый кит на синем фоне

2. **Нажми правой кнопкой мыши** на иконку Docker

3. **В контекстном меню выбери: Restart**