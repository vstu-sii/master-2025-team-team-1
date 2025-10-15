# My AI App

Проект с использованием Docker Compose для локальной разработки.

## Состав

- **Frontend**: Next.js (порт 3000)
- **Backend**: FastAPI (порт 8000)
- **Database**: PostgreSQL (порт 5432)
- **LLM Service**: Jupyter Notebook для экспериментов (порт 8888)

## Как запустить

1. Убедись, что установлены [Docker](https://www.docker.com/products/docker-desktop) и Docker Compose.
2. В корне проекта выполни:

```bash
docker-compose -f docker-compose.dev.yml up --build```

3. Открой в браузере:
Frontend: http://localhost:3000
Backend API: http://localhost:8000/api/hello
Jupyter: http://localhost:8888

4. Проверяй, делай изменения в коде.

5. Для остановки приложения нажми Ctrl+C в терминале, или выполни:

```docker-compose -f docker-compose.dev.yml down```

##Если есть ошибка (500 Internal Server Error for API route and version): 

🐳 Перезапусти Docker через системный трей:

1. **Найди иконку Docker** в правом нижнем углу экрана (в системном трее)
   - 🐳 Белый кит на синем фоне

2. **Нажми правой кнопкой мыши** на иконку Docker

3. **В контекстном меню выбери: Restart**
