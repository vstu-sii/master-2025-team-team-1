# 3 лаба

- Docker контейнеры:
1. Dockerfile для backend: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/backend/Dockerfile
2. Dockerfile для frontend: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/frontend/Dockerfile

- Docker Compose docker-compose.dev.yml, в котором все сервисы, выполнена настройка health checks, сети и volumes, в том числе driver: bridge для того, чтобы настроить связь этих сервисов с сервисами мониторинга из других docker-compose файлов (Grafana+Prometheus, Langfuse) https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/docker-compose.dev.yml

- Langfuse:
1. Выполнено развертывание Langfuse в Docker docker-compose.langfuse.yml: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/docker-compose.langfuse.yml
2. В веб-интерфейса Langfuse создан пользователь, проект и получены secret и public keys, которые помогли дальше связать backend с Langfuse 
3. Настроено подключение из backend: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/backend/main.py
4. Тестирование трассировки - по этому адресу создаётся тестовая трассировка /api/langfuse-test и она появляется в списке traces в веб-интерфейса Langfuse
5. Просмотр дашбордов и traces в веб-интерфейсе Langfuse

- GitHub Actions
1. Workflow для lint и format базовые unit тесты, build проверка Docker образов ci.yml: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/.github/workflows/ci.yml
2. deploy-dev.yml https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/.github/workflows/deploy-dev.yml

# 4 лаба
- Grafana мониторинг:
1. В docker-compose для мониторинга добавлено подключение к сервисам приложения через сеть из docker-compose.dev (с использованием driver: bridge) https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/monitoring/docker-compose.yml
2. В backend с помощью библиотеки prometheus_client добавлена работа с Prometheus, реализован сбор основных метрик -  количества и длительности HTTP-запросов, числа активных запросов и ошибок, а также использования памяти и загрузки CPU процесса: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/backend/main.py
3. В backend сделан маршрут @app.get("/metrics") для сбора метрик Prometheus и @app.get("/api/metrics/summary") для сводки метрик в JSON формате: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/backend/main.py
4. Протестирована работа по сбору метрик, в веб-интерфейсе Prometheus показано, что связь между backend и Prometheus работает (статус "Up")
5. В Grafana Prometheus выбран как источник, создан тестовый дашборд с графиками которые выводят данные, посчитанные с помощью PromQL запросов: сколько HTTP запросов обрабатывает backend каждую секунду, среднее время (в секундах), за которое backend обрабатывает один запрос, время ответа для 95% самых быстрых запросов.

- Улучшена документация инфраструктуры: добавлена информация по Grafana и Prometheus, а также по Langfuse: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/docs/infrastructure.md

- CI/CD Pipeline: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/.github/, https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/.github/workflows/deploy-dev.yml

- Docker Compose финальный: https://github.com/vstu-sii/master-2025-team-team-1/blob/feedback/docker-compose.dev.yml