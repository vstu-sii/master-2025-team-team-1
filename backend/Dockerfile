FROM python:3.11-slim

WORKDIR /app

# Создаем директорию для prometheus multiprocess
RUN mkdir -p /tmp/prometheus && chmod 777 /tmp/prometheus

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создание директории для логов
RUN mkdir -p /tmp && chmod 777 /tmp

EXPOSE 8000 

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]