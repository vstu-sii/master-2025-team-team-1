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
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

Для закрытия мониторинга:
```
cd monitoring
docker-compose down
```

## Запуск Langfuse
```
docker-compose -f docker-compose.langfuse.yml up --build
```
**Доступ к Langfuse UI**: http://localhost:3002
1. Откройте http://localhost:3002;
2. Введите электронную почту: admin@admin.com;
3. Введите пароль: adminadmin.

**Тестирование Langfuse UI**: http://localhost:3002
1. Откройте http://localhost:8000/api/langfuse-test;
2. Скопируйте trace_id из ответа;
3. Откройте Langfuse UI: http://localhost:3002;
4. Вставьте trace_id в поиск;
5. Нажмите на трассировку для просмотра деталей.

**Просмотр свежих трассировок в режиме реального времени**:
1. Откройте http://localhost:3002;
2. Перейдите в "Traces";
3. Используйте фильтры (timestamp: last 5 minutes, status: error (для поиска ошибок), name: contains "chat" (для конкретных эндпоинтов)).

**Просмотр дашбордов**:
1. В Langfuse UI нажмите "Dashboards";
2. Выберите промежуток времени и, если нужно, фильтры.

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