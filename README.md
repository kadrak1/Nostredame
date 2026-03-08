# HookahBook

Система онлайн-бронирования столов и заказа кальянов для кальянных заведений. Веб-интерфейс + Telegram-бот, хостинг на Raspberry Pi 5.

---

## Содержание

- [Обзор](#обзор)
- [Стек технологий](#стек-технологий)
- [Быстрый старт](#быстрый-старт)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)
- [Деплой](#деплой)
- [Документация](#документация)
- [Переменные окружения](#переменные-окружения)

---

## Обзор

**Проблема**: посетители кальянных ждут кальянщика для заказа, бронирование происходит по телефону, постоянные клиенты заново описывают свои предпочтения.

**Решение**: единая платформа с визуальным выбором стола, предзаказом кальяна и уведомлениями — доступная через веб и Telegram.

### Роли пользователей

| Роль | Возможности |
|------|------------|
| **Гость** | Бронирование стола, конструктор кальяна, история заказов |
| **Владелец / Администратор** | Конструктор зала, управление бронями и каталогом табаков |
| **Кальянщик** | Очередь заказов, смена статусов |

---

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend API | Python 3.12 + FastAPI + SQLAlchemy |
| База данных | SQLite (Alembic для миграций) |
| Frontend | React 18 + TypeScript + Vite |
| Конструктор зала | react-konva (Canvas) |
| Telegram Bot | python-telegram-bot v20+ |
| Reverse Proxy + HTTPS | Caddy (автоматический Let's Encrypt) |
| Контейнеризация | Docker + docker-compose |
| Логирование | structlog + audit log |

Подробнее: [`docs/TECH-STACK.md`](docs/TECH-STACK.md)

---

## Быстрый старт

### Требования

- Docker и docker-compose
- Git

### Локальный запуск

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd hookahbook

# 2. Настроить окружение
cp .env.example .env
# Отредактировать .env — обязательно поменять JWT_SECRET_KEY и ENCRYPTION_KEY

# 3. Запустить все сервисы
docker-compose up --build

# 4. Применить миграции БД
docker-compose exec backend alembic upgrade head

# 5. Создать администратора
docker-compose exec backend python scripts/create_admin.py
```

После запуска:
- Frontend: http://localhost:5173
- Backend API + Swagger: http://localhost:8000/docs
- Adminer / Health: http://localhost:8000/api/health

---

## Структура проекта

```
hookahbook/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI приложение, подключение роутеров
│   │   ├── config.py            # Настройки через Pydantic Settings
│   │   ├── database.py          # SQLAlchemy async engine + сессии
│   │   ├── dependencies.py      # FastAPI dependencies (auth, db)
│   │   ├── limiter.py           # Rate limiting (slowapi)
│   │   ├── logging_config.py    # structlog + audit log конфигурация
│   │   ├── models/              # SQLAlchemy ORM-модели
│   │   ├── routers/             # FastAPI роутеры (REST endpoints)
│   │   ├── schemas/             # Pydantic схемы (валидация)
│   │   ├── services/            # Бизнес-логика
│   │   └── middleware/          # Кастомные middleware
│   ├── bot/                     # Telegram-бот
│   │   ├── handlers/            # Обработчики команд и колбэков
│   │   └── keyboards/           # Inline-клавиатуры
│   ├── alembic/                 # Миграции БД
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                 # API-клиент (axios + react-query)
│   │   ├── pages/               # Страницы приложения
│   │   ├── layouts/             # Layout-компоненты
│   │   └── App.tsx
│   ├── public/                  # Статические файлы (иконки, sw.js)
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   ├── create_admin.py          # Создание первого администратора
│   └── generate_secrets.py      # Генерация JWT secret и encryption key
├── docs/                        # Проектная документация
├── docker-compose.yml
├── Caddyfile                    # Конфигурация Caddy (dev)
├── Caddyfile.production         # Конфигурация Caddy (prod)
└── .env.example
```

---

## Разработка

### Backend

```bash
cd backend

# Установить зависимости (локально, без Docker)
pip install -r requirements.txt

# Запустить с hot-reload
uvicorn app.main:app --reload --port 8000

# Применить миграции
alembic upgrade head

# Создать новую миграцию
alembic revision --autogenerate -m "описание изменений"

# Линтинг
ruff check .

# Проверка типов
mypy app --ignore-missing-imports

# Тесты
pytest tests/ -v
```

### Frontend

```bash
cd frontend

# Установить зависимости
npm install

# Запустить dev-сервер (с проксированием API на localhost:8000)
npm run dev

# Сборка для production
npm run build

# Линтинг
npm run lint

# Проверка типов
npx tsc --noEmit
```

### Полезные команды Docker

```bash
# Запустить только backend и пересобрать
docker-compose up --build backend

# Посмотреть логи backend
docker-compose logs -f backend

# Открыть shell в контейнере backend
docker-compose exec backend bash

# Остановить все сервисы
docker-compose down
```

---

## Деплой

Деплой на Raspberry Pi 5 (ARM64). Продакшн-конфигурация использует `Caddyfile.production` с автоматическим HTTPS.

```bash
# На RPi5:
git pull origin main
docker-compose -f docker-compose.yml up --build -d
docker-compose exec backend alembic upgrade head
```

**Требования к серверу:**
- Docker + docker-compose
- Открытые порты: 80, 443 (HTTP/HTTPS), 22 (SSH)
- SSD для данных (БД, логи) — не SD-карта
- Белый статический IP или Cloudflare Tunnel

Подробнее о защите сервера: [`docs/PHASE1-TICKETS.md`](docs/PHASE1-TICKETS.md) → T-041.

---

## Документация

| Документ | Описание |
|---------|---------|
| [`docs/PRD-HookahBook-MVP.md`](docs/PRD-HookahBook-MVP.md) | Product Requirements Document — цели, user stories, требования |
| [`docs/TECH-STACK.md`](docs/TECH-STACK.md) | Выбор технологий с обоснованием |
| [`docs/DESIGN-BRIEF.md`](docs/DESIGN-BRIEF.md) | Дизайн-бриф: UX-флоу, цвета, компоненты |
| [`docs/PHASE1-TICKETS.md`](docs/PHASE1-TICKETS.md) | Инженерные тикеты Фазы 1 и прогресс |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Роадмап фаз разработки |
| [`docs/features/`](docs/features/) | Детальные спецификации фич |

---

## Переменные окружения

Все конфигурационные переменные описаны в [`.env.example`](.env.example). Скопируйте файл в `.env` и заполните реальными значениями.

**Генерация секретов:**

```bash
# JWT Secret (256-bit)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Encryption Key (Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# VAPID Keys для Web Push
python scripts/generate_secrets.py --vapid
```

> Никогда не коммитьте `.env` в репозиторий!

---

## CI/CD

GitHub Actions запускается при пуше в `main` и `develop`, а также на все PR:

- **Frontend**: lint (ESLint) + type check (tsc) + build
- **Backend**: lint (ruff) + type check (mypy) + tests (pytest)
- **Docker**: проверка сборки образов

Статус CI: см. вкладку Actions в GitHub.
