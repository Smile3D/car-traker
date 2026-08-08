# Dockerize Car Garage Tracker (db + backend + frontend)

**Date:** 2026-07-24
**Status:** Approved

## Purpose

Докеризировать существующий проект (`backend/` — FastAPI+Postgres+Alembic auth-фундамент,
`frontend/` — Nuxt 4+Pinia auth-фундамент) так, чтобы единственная команда `docker-compose up`
из корня поднимала всю связку: Postgres с персистентным volume, backend и frontend в dev-режиме
с hot-reload через bind mount.

## Scope

In scope:
- `backend/Dockerfile`, `backend/.dockerignore`, `backend/entrypoint.sh`
- `frontend/Dockerfile`, `frontend/.dockerignore`
- `docker-compose.yml` в корне (db, backend, frontend)
- `.env` в корне (переменные для всех трёх сервисов)
- Bind mounts для backend/frontend кода (hot-reload без пересборки образа)
- Правки `frontend/nuxt.config.ts` и `frontend/app/composables/useApi.ts` — раздельные
  публичный (browser) и внутренний (SSR/server) базовые URL API
- Обновление корневого `README.md`

Out of scope:
- Production-сборка (multi-stage build, `nuxt build`/`nitro` prod-режим)
- CI/CD, docker registry, оркестрация за пределами compose
- Любые изменения бизнес-логики backend/frontend

## Key Decisions

1. **Сеть:** default bridge-сеть docker-compose, сервисы обращаются друг к другу по имени
   сервиса (`db`, `backend`, `frontend`).
2. **backend → db:** `DATABASE_URL=postgresql://...@db:5432/...` — hostname `db` резолвится
   только внутри compose-сети.
3. **frontend → backend — раздельные URL:**
   - `runtimeConfig.public.apiBaseUrl` (`http://localhost:8000`) — для запросов из браузера
     после гидратации, через проброшенный на хост порт.
   - `runtimeConfig.apiBaseUrlInternal` (`http://backend:8000` под docker,
     `http://localhost:8000` по умолчанию для локальной разработки без docker) — для
     SSR-запросов, выполняющихся внутри контейнера `frontend`.
   - `useApi.ts` выбирает между ними через `import.meta.server`.
4. **Backend в контейнере — без venv.** Зависимости ставятся в системный Python образа при
   сборке. Bind-mount всей директории `backend/` (включая локальный `venv/`) не мешает — он
   просто не используется внутри контейнера.
5. **Frontend — анонимный volume под `node_modules`:** `./frontend:/app` + `/app/node_modules`.
   Без этого bind-mount с хоста затирает `node_modules`, установленный в образе (native-бинарники
   собраны под Linux, хостовые — под macOS, упадёт на старте).
6. **Backend entrypoint:** `alembic upgrade head` перед `uvicorn ... --reload`, чтобы
   `docker-compose up` с нуля сразу давал рабочую схему БД. `depends_on: db: condition:
   service_healthy` (healthcheck `pg_isready`) — backend стартует не раньше готовности Postgres.
7. **Dev-режим для обоих:** `uvicorn --reload` и `npm run dev -- --host 0.0.0.0` (нужен явный
   `--host`, иначе dev-сервер слушает только loopback внутри контейнера и порт снаружи не
   достучится).
8. **Персистентность Postgres:** именованный volume `pg_data:/var/lib/postgresql/data`.

## Repository Layout (добавляется)

```
car-garage-tracker/  (repo root)
├── docker-compose.yml
├── .env
├── .env.example
├── README.md                 # обновляется — docker-compose up как единственная команда
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── entrypoint.sh
└── frontend/
    ├── Dockerfile
    └── .dockerignore
```

## Error Handling

- Backend healthcheck на `db` не пропускает старт backend раньше готовности Postgres.
- `entrypoint.sh` использует `set -e` — если `alembic upgrade head` падает, контейнер backend
  не стартует с "тихо сломанной" схемой БД.

## Testing

Ручная проверка: `docker-compose up`, дождаться готовности всех трёх сервисов, пройти
register → login → dashboard через браузер/curl, убедиться что правка кода в
backend/frontend подхватывается без пересборки образа.

## Implementation Blocks

1. `backend/Dockerfile`, `backend/.dockerignore`, `backend/entrypoint.sh`
2. `frontend/Dockerfile`, `frontend/.dockerignore`
3. `docker-compose.yml` + корневой `.env`/`.env.example`
4. `nuxt.config.ts` + `useApi.ts` — dual base URL под SSR/browser
5. Корневой `README.md` + полная проверка через `docker-compose up`
