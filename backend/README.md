# Car Garage Tracker — Backend

Фундамент FastAPI-бэкенда: авторизация (JWT) и инфраструктура (Postgres, SQLAlchemy 2.0, Alembic).
Бизнес-логика (машины, сервисные записи, фото) сюда пока не входит.

## Стек

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- JWT (pyjwt) + passlib[bcrypt]

## 1. Поднять PostgreSQL (разовый контейнер)

```bash
docker run -d \
  --name car-garage-tracker-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=car_garage_tracker \
  -p 5432:5432 \
  postgres:16
```

Остановить/удалить позже: `docker stop car-garage-tracker-postgres && docker rm car-garage-tracker-postgres`.

## 2. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Переменные окружения

```bash
cp .env.example .env
```

Значения по умолчанию в `.env.example` соответствуют команде `docker run` выше. Обязательно
смени `SECRET_KEY` на случайную строку перед чем-то, кроме локальной разработки.

## 4. Применить миграции

```bash
alembic upgrade head
```

## 5. Запустить сервер

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

## Эндпоинты на старте

- `POST /auth/register` — регистрация (email, password)
- `POST /auth/login` — логин (form-data: `username`, `password`), возвращает JWT
- `GET /auth/me` — текущий пользователь (требует `Authorization: Bearer <token>`)
- `GET /health` — проверка, что сервер жив

## Дальнейшие шаги

Модели `Car`, `ServiceRecord`, `Photo` и соответствующие роутеры/эндпоинты — вне рамок этого
фундамента, добавляются отдельно.
