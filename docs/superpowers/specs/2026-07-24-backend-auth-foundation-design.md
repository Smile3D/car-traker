# Backend Foundation — Auth & Infrastructure (Car Garage Tracker)

**Date:** 2026-07-24
**Status:** Approved

## Purpose

Создать стартовую заготовку backend-проекта на FastAPI для "Car Garage Tracker". Это только
фундамент: авторизация (User-модель + JWT) и инфраструктура (БД, миграции, конфиг, CORS).
Никакой бизнес-логики про машины/сервисы/фото — она будет добавляться отдельно, по шагам,
за пределами этого спека.

## Scope

In scope:
- Модель `User` (id, email, hashed_password, created_at)
- Auth-роутер: `register`, `login`, `me`
- Инфраструктура: конфиг, подключение к БД, зависимости, Alembic-миграции, CORS
- Локальный Postgres через разовый `docker run`
- `.env.example`, `README.md`

Out of scope (сознательно не делается сейчас):
- Модели Car, ServiceRecord, Photo и любые связанные эндпоинты
- Refresh-токены, роли/permissions, восстановление пароля
- Docker-compose, CI/CD, тесты (не запрошены на этом этапе)
- Async SQLAlchemy (оставлен sync-движок для простоты старта)

## Repository Layout

Проект — монорепо (`fs-nuxt-car-garage-tracker`): backend и будущий Nuxt-frontend — соседние
директории в корне.

```
backend/
├── app/
│   ├── main.py              # создание FastAPI app, подключение роутеров, CORS
│   ├── config.py            # Settings (pydantic-settings) — читает .env
│   ├── database.py          # engine, SessionLocal, Base, get_db-зависимость
│   ├── dependencies.py      # get_current_user и прочие FastAPI Depends
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # SQLAlchemy 2.0 модель User
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py          # UserCreate, UserRead
│   │   └── token.py         # Token, TokenPayload
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py          # /register, /login, /me
│   └── services/
│       ├── __init__.py
│       └── security.py      # хэширование пароля, создание/декод JWT
├── alembic/
│   ├── versions/
│   └── env.py                # настроен на чтение DATABASE_URL из Settings
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

## Key Decisions

1. **JWT: `pyjwt`** вместо `python-jose` — активнее поддерживается, меньше известных CVE,
   более простой API. Хэширование пароля — `passlib[bcrypt]`.
2. **Конфиг: `pydantic-settings`** (`BaseSettings`) — типизированный доступ к `DATABASE_URL`,
   `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` из `.env`.
3. **DB-слой:** sync SQLAlchemy 2.0 engine (`create_engine`), `Base` через `DeclarativeBase`,
   `get_db()` — generator-зависимость с закрытием сессии в `finally`. Async оставлен на будущее
   как возможный шаг рефакторинга, не нужен на этом этапе.
4. **User-модель:** `id: int` (PK), `email: str` (unique, indexed), `hashed_password: str`,
   `created_at: datetime` (`server_default=func.now()`). Только поля, нужные для auth.
5. **Auth-роутер:**
   - `POST /auth/register` — `UserCreate` (email, password) → проверка уникальности email →
     хэширование пароля → создание пользователя → `UserRead`.
   - `POST /auth/login` — `OAuth2PasswordRequestForm` (чтобы сразу работало со Swagger
     "Authorize") → проверка пароля → `Token` (access_token, token_type).
   - `GET /auth/me` — защищён через `Depends(get_current_user)`, возвращает текущего юзера.
6. **CORS:** разрешён `http://localhost:3000` (дефолтный порт Nuxt dev-сервера).
7. **Alembic:** инициализация non-interactive (`alembic init alembic`), `env.py` переопределён
   на `Base.metadata` и `DATABASE_URL` из `Settings`; первая миграция — автогенерация по
   модели `User`.
8. **Postgres:** разовый контейнер `docker run` (без docker-compose) с фиксированным портом,
   паролем и именем БД — достаточно для локальной разработки и применения первой миграции.

## Error Handling

- Register: `400` если email уже зарегистрирован.
- Login: `401` при неверном email/пароле (единое сообщение, без уточнения что именно неверно).
- `/me` и любые защищённые эндпоинты: `401` при отсутствующем/невалидном/просроченном токене
  (через `Depends(get_current_user)`, единая точка обработки).
- Валидация входных данных (формат email, длина пароля) — на уровне Pydantic-схем.

## Testing

Тесты не запрошены на этом этапе — фундамент проверяется вручную (регистрация → логин →
обращение к `/me` с полученным токеном).

## Implementation Blocks (с паузой после каждого)

1. Структура проекта + конфиг (`config.py`) + БД (`database.py`) + зависимости (`requirements.txt`)
2. Модель `User`
3. Security-сервис (хэширование, JWT) + `dependencies.py` (`get_current_user`)
4. Auth-роутер (`register`, `login`, `me`) + подключение в `main.py` + CORS
5. Alembic: инициализация, настройка `env.py`, первая миграция + команда `docker run` для Postgres
6. `.env.example`, `README.md`
