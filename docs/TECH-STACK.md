# Выбор техстека — HookahBook MVP

## Ограничения

- **Raspberry Pi 5** (ARM64, 4-8 GB RAM)
- **Один разработчик, начинающий уровень**
- **Домен + статический IP** уже есть
- Нужен веб-интерфейс с интерактивным конструктором зала (canvas/drag-and-drop)
- Нужен Telegram-бот
- Минимум движущих частей, максимум обучаемости

---

## Рекомендуемый стек

### Backend: Python + FastAPI

**Почему:**
- Python — самый дружелюбный язык для начинающих
- FastAPI автоматически генерирует Swagger UI (документация API из коробки) — удобно для отладки
- Асинхронный, лёгкий — хорошо работает на RPi5
- Огромное количество туториалов и примеров
- Один язык для backend и Telegram-бота

**Альтернативы (отклонены):**
- Django — слишком тяжёлый и магический для MVP, избыток абстракций
- Node.js/Express — потребовал бы изучения JavaScript для бэкенда вдобавок к фронтенду; Python проще для старта

### База данных: SQLite

**Почему:**
- Нулевая настройка — это просто файл, никакого отдельного сервера
- Идеально для одного заведения и ожидаемой нагрузки (десятки, не тысячи пользователей)
- Экономит RAM на RPi5 (нет процесса PostgreSQL)
- Миграция на PostgreSQL потом — несложная задача через SQLAlchemy

**Когда перейти на PostgreSQL:**
- Если появится мультитенантность (несколько заведений)
- Если одновременных записей станет >50/сек (маловероятно для MVP)

### ORM: SQLAlchemy + Alembic

- SQLAlchemy — стандарт Python, работает одинаково с SQLite и PostgreSQL
- Alembic — миграции схемы БД (добавление/изменение таблиц без потери данных)

### Frontend: React + Vite

**Почему React, а не Vue/Svelte:**
- Самая большая экосистема — больше готовых компонентов и решений
- `react-konva` — зрелая обёртка для конструктора зала (canvas)
- Claude лучше всего помогает с React — больше примеров в обучении
- Vite вместо Next.js — проще, легче на RPi5 (нет SSR), быстрый dev-сервер

**Почему не Next.js:**
- SSR создаёт лишнюю нагрузку на RPi5
- Для MVP SEO не критичен (кальянные находят через соцсети/сарафан)
- Vite + React SPA проще для начинающего

### Конструктор зала: react-konva (Konva.js)

- Canvas-based — плавный drag-and-drop для столов и стен
- Хорошая документация, много примеров
- Поддерживает touch-события (мобильные устройства)
- Экспорт в JSON для сохранения плана зала

### Telegram Bot: python-telegram-bot (v20+)

**Почему:**
- Тот же Python, что и backend — один язык
- Зрелая библиотека, async-first
- ConversationHandler для пошаговых диалогов (бронирование)
- Поддержка Telegram Login Widget для авторизации на сайте

### Авторизация

- **Telegram Login Widget** — основной (бесплатный, через Telegram OAuth)
- **SMS OTP (fallback)** — через SMS.ru (~0.5-2₽/SMS, дешевле Twilio для РФ)
- **JWT токены** — для сессий (библиотека `python-jose`)

### Reverse Proxy + HTTPS: Caddy

**Почему Caddy, а не Nginx:**
- Автоматический HTTPS через Let's Encrypt — **нулевая конфигурация сертификатов**
- Конфигурация в 5 строк vs 30+ у Nginx
- Встроенный HTTP/2 и HTTP/3
- Один бинарник, легче на RPi5

### Контейнеризация: Docker + docker-compose

- Единая команда `docker-compose up` для запуска всего
- Воспроизводимая среда на RPi5
- Легко обновлять и откатывать
- ARM64-образы доступны для всех выбранных технологий

---

## Итоговая архитектура

```
┌──────────────────────────────────────────────────────┐
│                   Raspberry Pi 5                      │
│                                                       │
│  ┌─────────┐    ┌──────────────────────────────────┐ │
│  │  Caddy   │───▶│  FastAPI Backend (Python)         │ │
│  │  :443    │    │  - REST API                       │ │
│  │  HTTPS   │    │  - WebSocket (статус заказов)     │ │
│  └─────────┘    │  - SQLite (файл БД)               │ │
│       │         └──────────────────────────────────┘ │
│       │                      │                        │
│       ▼                      ▼                        │
│  ┌─────────┐    ┌──────────────────────────────────┐ │
│  │  React   │    │  Telegram Bot (python-telegram-bot)│ │
│  │  SPA     │    │  - Long polling (не webhook)      │ │
│  │  (Vite)  │    │  - Deep links для QR              │ │
│  └─────────┘    └──────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### Компоненты:

| Компонент | Технология | Порт |
|-----------|-----------|------|
| Reverse proxy + HTTPS | Caddy | 443, 80 |
| Backend API | FastAPI (uvicorn) | 8000 |
| Frontend (dev) | Vite dev server | 5173 |
| Frontend (prod) | Статические файлы через Caddy | — |
| Telegram Bot | python-telegram-bot (long polling) | — |
| БД | SQLite | файл |

### Telegram Bot: Long Polling vs Webhook

Для RPi5 за NAT с белым IP — **webhook** был бы стандартным выбором, но **long polling** проще для старта:
- Не нужно настраивать SSL для Telegram
- Работает без проброса портов
- Для MVP достаточно

Позже можно переключить на webhook (FastAPI endpoint) для production.

---

## Структура проекта

```
hookahbook/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Настройки
│   │   ├── database.py          # SQLAlchemy + SQLite
│   │   ├── models/              # ORM-модели
│   │   │   ├── venue.py
│   │   │   ├── table.py
│   │   │   ├── tobacco.py
│   │   │   ├── booking.py
│   │   │   ├── order.py
│   │   │   └── guest.py
│   │   ├── routers/             # API endpoints
│   │   │   ├── bookings.py
│   │   │   ├── orders.py
│   │   │   ├── tobaccos.py
│   │   │   ├── venue.py
│   │   │   └── auth.py
│   │   ├── schemas/             # Pydantic-схемы (валидация)
│   │   └── services/            # Бизнес-логика
│   ├── bot/
│   │   ├── main.py              # Telegram bot
│   │   ├── handlers/            # Обработчики команд
│   │   └── keyboards/           # Inline-клавиатуры
│   ├── alembic/                 # Миграции БД
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FloorPlanEditor/ # Конструктор зала (react-konva)
│   │   │   ├── FloorPlanView/   # Просмотр зала (для гостей)
│   │   │   ├── HookahBuilder/   # Конструктор кальяна
│   │   │   └── BookingFlow/     # Флоу бронирования
│   │   ├── pages/
│   │   ├── api/                 # API-клиент
│   │   └── App.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── Caddyfile
└── docs/
    ├── PRD-HookahBook-MVP.md
    └── TECH-STACK.md
```

---

## Зависимости (Python)

```
fastapi>=0.109
uvicorn[standard]>=0.27
sqlalchemy>=2.0
alembic>=1.13
python-telegram-bot>=20.7
python-jose[cryptography]>=3.3  # JWT
httpx>=0.26                      # HTTP-клиент (SMS API)
pydantic>=2.5
python-multipart>=0.0.6         # Загрузка файлов
```

## Зависимости (Frontend)

```
react, react-dom
react-router-dom          # Маршрутизация
react-konva, konva        # Конструктор зала
@tanstack/react-query     # Кеширование API-запросов
axios                     # HTTP-клиент
typescript
```

---

## Caddyfile (пример)

```
yourdomain.com {
    # Frontend SPA
    handle /* {
        root * /srv/frontend
        try_files {path} /index.html
        file_server
    }

    # Backend API
    handle /api/* {
        reverse_proxy backend:8000
    }

    # WebSocket для статусов заказов
    handle /ws/* {
        reverse_proxy backend:8000
    }
}
```

---

## Что изучить перед стартом (в порядке приоритета)

1. **Python основы** — если ещё не знакомы (2-3 дня)
2. **FastAPI Tutorial** — официальный туториал (1-2 дня) → https://fastapi.tiangolo.com/tutorial/
3. **React основы** — компоненты, useState, useEffect (3-5 дней)
4. **Docker основы** — Dockerfile, docker-compose (1 день)
5. **SQL основы** — CREATE, SELECT, INSERT, JOIN (1-2 дня)
