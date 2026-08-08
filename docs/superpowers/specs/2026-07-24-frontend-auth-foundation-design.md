# Frontend Foundation — Auth & Infrastructure (Car Garage Tracker)

**Date:** 2026-07-24
**Status:** Approved

## Purpose

Создать стартовую заготовку frontend-проекта на Nuxt 4 для "Car Garage Tracker". Только
фундамент: авторизация (login/register/logout, защищённые роуты) и инфраструктура (store,
API-composable, layouts). Никаких страниц про машины/сервисы/фото — они добавляются отдельно.

## Scope

In scope:
- Nuxt 4 + TypeScript + Pinia + Tailwind CSS проект в `frontend/`
- Layouts: `default` (заглушка-навигация), `auth` (для login/register)
- `authStore` (Pinia): token, user, login/register/logout/fetchCurrentUser
- `useApi` composable — обёртка над `$fetch` с `runtimeConfig` baseURL и авто-подстановкой JWT
- Middleware `auth` для защищённых роутов (redirect на `/login`)
- Страницы: `/login`, `/register`, `/dashboard` (защищённая заглушка)
- `types/user.ts`

Out of scope:
- Любые страницы/компоненты про cars, service records, photos
- Refresh-токены, восстановление пароля, роли
- Production-ready UI/дизайн-система, тесты, CI

## Repository Layout

`frontend/` в корне монорепо, рядом с `backend/`.

```
frontend/
├── app/
│   ├── layouts/
│   │   ├── default.vue
│   │   └── auth.vue
│   ├── middleware/
│   │   └── auth.ts
│   ├── pages/
│   │   ├── login.vue
│   │   ├── register.vue
│   │   └── dashboard.vue
│   ├── stores/
│   │   └── auth.ts
│   ├── composables/
│   │   └── useApi.ts
│   ├── types/
│   │   └── user.ts
│   └── app.vue
├── nuxt.config.ts
├── .env.example
└── package.json
```

## Key Decisions

1. **Пакетный менеджер: npm** — без дополнительных зависимостей окружения.
2. **Tailwind через модуль `@nuxtjs/tailwindcss`**, не ручной PostCSS-конфиг — идиоматично
   для Nuxt.
3. **Хранение JWT: `useCookie('auth_token')`, не `localStorage`.** Бэкенд отдаёт токен в JSON
   (не `Set-Cookie`), поэтому `httpOnly` недоступен в любом случае — но `useCookie` читается
   и на сервере при SSR, и на клиенте, что позволяет `middleware/auth.ts` редиректить уже во
   время SSR-рендера, без "мигания" защищённой страницы после гидратации.
4. **`useApi`** — обёртка над `$fetch` (не `useFetch`): типизированные `apiGet`/`apiPost`/
   `apiPut`/`apiDelete`, каждый вызов подставляет `baseURL` из
   `runtimeConfig.public.apiBaseUrl` и `Authorization: Bearer <token>`, если токен есть.
   Ошибки `$fetch` (`FetchError`) приводятся к единому виду `{ statusCode, message }` и
   выбрасываются дальше — единый `try/catch` во всех вызывающих местах.
5. **`authStore` (Pinia, setup-синтаксис):** `token` (источник — cookie), `user: User | null`,
   `isAuthenticated` (computed), методы `login`, `register`, `logout`, `fetchCurrentUser`
   (вызывает `/auth/me` для восстановления `user` по токену, например при обновлении страницы).
6. **Middleware `auth.ts`** — named (не global), навешивается через
   `definePageMeta({ middleware: 'auth' })` на защищённых страницах; редирект на `/login` при
   отсутствии токена.
7. **Layouts:** `default.vue` — шапка-заглушка (название приложения + logout, если
   авторизован); `auth.vue` — центрированная карточка без навигации.
8. **Страницы:** `/login`, `/register` (layout `auth`), `/dashboard` (layout `default`,
   `middleware: 'auth'`, "Привет, {email}" + кнопка logout).
9. **`types/user.ts`** — `User { id, email, created_at }`, зеркалит backend `UserRead`
   (см. `backend/app/schemas/user.py`).

## Error Handling

- `useApi`: любая ошибка `$fetch` (сеть, 4xx/5xx) нормализуется в `{ statusCode, message }`
  и пробрасывается как исключение — страницы login/register ловят его и показывают
  сообщение пользователю.
- Middleware: отсутствие токена → редирект на `/login`, без обращения к API.
- `fetchCurrentUser`: если `/auth/me` вернул 401 (невалидный/просроченный токен) — стор
  очищает `token`/`user`, пользователь считается разлогиненным.

## Testing

Тесты не запрошены — фундамент проверяется вручную в браузере (запуск dev-сервера,
прогон login → dashboard → logout, попытка открыть `/dashboard` без токена).

## Implementation Blocks (с паузой после каждого)

1. Инициализация Nuxt 4 проекта (non-interactive) + модули (`@pinia/nuxt`,
   `@nuxtjs/tailwindcss`) + `runtimeConfig` + `.env.example`
2. `types/user.ts` + `composables/useApi.ts`
3. `stores/auth.ts` (Pinia)
4. `layouts/default.vue`, `layouts/auth.vue`, `middleware/auth.ts`
5. Страницы `/login`, `/register`, `/dashboard` + ручная проверка в браузере
