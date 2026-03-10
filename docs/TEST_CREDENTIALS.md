# Тестовые учётные данные HookahBook (DEV)

> **Только для локальной разработки.** Не использовать в production.

## Бэкенд (API / Панель управления)

Логин через `POST /api/auth/login` с JSON `{"login": "...", "password": "..."}`.
Аутентификация — httpOnly-куки (`access_token`).

| Роль        | login    | password   | Примечание                        |
|-------------|----------|------------|-----------------------------------|
| Owner/Admin | `admin`  | `admin123` | Полный доступ. Запись в реальной БД (`data/hookahbook.db`) |

Тестовые фикстуры в `backend/tests/conftest.py` создают пользователей в изолированной тестовой БД:

| Роль            | login     | password     |
|-----------------|-----------|--------------|
| Owner           | `owner`   | `owner123`   |
| Admin           | `admin`   | `admin123`   |
| Hookah master   | `master`  | `master123`  |

## Фронтенд (Панель управления)

Адрес: `http://localhost:5173/admin/login`

Форма принимает те же `login` / `password`, что и API.
Для ручного тестирования используй учётку `admin` / `admin123`.

## Guest (QR-flow)

Гостевая аутентификация не требует пароля:
- `GET /api/tables/{table_id}/info` — публичный эндпоинт для QR-лендинга
- `POST /api/guest/token` — создаёт гостевую сессию для конкретного стола
- Гостевой токен хранится в `sessionStorage` (ключ `guest_token`)

Для ручного тестирования QR-flow:
1. Открыть `http://localhost:5173/table/1` (стол №1)
2. Нажать «Сделать заказ»
3. Готово — гостевая сессия создаётся автоматически

## Полезные ссылки в dev-режиме

| Страница                   | URL                                          |
|----------------------------|----------------------------------------------|
| Главная                    | http://localhost:5173/                       |
| Бронирование               | http://localhost:5173/booking                |
| Панель управления          | http://localhost:5173/admin                  |
| QR-коды столов             | http://localhost:5173/admin/qr-codes         |
| Каталог табаков            | http://localhost:5173/admin/tobaccos         |
| QR-лендинг (стол 1)        | http://localhost:5173/table/1                |
| Статус заказа (пример)     | http://localhost:5173/order/{publicId}       |
| API docs (Swagger)         | http://localhost:8000/docs                   |
| API docs (ReDoc)           | http://localhost:8000/redoc                  |
