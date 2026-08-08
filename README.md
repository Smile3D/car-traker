# Car Garage Tracker

Монорепо: `backend/` (FastAPI + PostgreSQL + SQLAlchemy 2.0 + Alembic) и `frontend/`
(Nuxt 4 + TypeScript + Pinia + Tailwind CSS). На старте реализован только фундамент —
авторизация (JWT) и инфраструктура; бизнес-логика про машины/сервисы/фото добавляется отдельно.

## Запуск (docker-compose)

Единственная команда:

```bash
docker compose up
```

Поднимает три сервиса:
- **db** — Postgres 16, данные персистентны в volume `pg_data`
- **backend** — FastAPI на http://localhost:8000 (Swagger: http://localhost:8000/docs),
  накатывает миграции автоматически при старте; health: http://localhost:8000/health
- **frontend** — Nuxt dev-сервер на http://localhost:3000;
  health: http://localhost:3000/health

Код `backend/` и `frontend/` подключён через bind mount — правки в коде подхватываются
на лету (hot-reload / `uvicorn --reload`), без пересборки образов.

Переменные окружения — в корневом `.env` (пример значений в `.env.example`). Обязательно
смени `SECRET_KEY` на случайную строку перед чем-то, кроме локальной разработки.

Остановить: `docker compose down` (данные Postgres сохранятся в volume).
Остановить и удалить данные Postgres: `docker compose down -v`.

## Тестовые данные (seed)

Чтобы не наполнять CRM вручную через UI после каждого сброса БД:

```bash
docker compose exec backend python -m scripts.seed_demo_data
```

Создаёт компанию с владельцем, 3 сотрудников (с разными позициями), 13 лотов во всех
статусах (черновик/активный/забронирован/продано/снято с продажи) и покупателей — всё
через реальные эндпоинты API (`POST /listings`, `POST /listings/{id}/mark-sold` и т.д.),
чтобы производные поля (`net_profit`, `date_added`, `DealHistory`-снапшот) заполнялись
той же бизнес-логикой, что и в реальном приложении, а не пустыми/нулевыми значениями.

Данные логина владельца печатаются в конце вывода скрипта (email/пароль — прямо в коде
скрипта, `backend/scripts/seed_demo_data.py`).

Повторный запуск без флагов при уже существующих seed-данных завершится ошибкой (не
плодит дубликаты). Чтобы пересоздать данные:

```bash
docker compose exec backend python -m scripts.seed_demo_data --reset   # удаляет только seed-компанию
docker compose exec backend python -m scripts.seed_demo_data           # создаёт заново
```

`--reset` трогает только данные компании, созданной этим скриптом — данные других
компаний/пользователей не затрагиваются.

## Запуск без Docker

Для локальной разработки без Docker — см. `backend/README.md` и `frontend/README.md`.

## Стек

- Backend: FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT (pyjwt + passlib)
- Frontend: Nuxt 4, TypeScript, Pinia, Tailwind CSS

## Что уже есть

- Модель `User` + `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- Health: `GET /health` (backend) и страница `/health` (frontend) — оба отвечают `{"status":"ok"}`
- Frontend: `/login`, `/register`, защищённая `/dashboard`, `authStore`, middleware для
  защищённых роутов

## Дальнейшие шаги

Модели/страницы про cars, service records, photos — вне рамок текущего фундамента,
добавляются отдельно.
