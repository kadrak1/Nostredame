# Feature: Уведомления (Telegram + Web Push)

**Phase**: 3
**PRD Requirement**: — (Phase 3)
**Status**: Planned
**Dependencies**: T-070 (telegram bot), T-080 (guest auth — `get_current_guest()` dependency)
**Date**: 2026-03-07

---

## 1. Overview / Обзор

Гость бронирует стол или заказывает кальян — и уходит от стойки или ставит телефон в карман. Без уведомлений он не знает, подтверждена ли бронь и готов ли кальян. Это приводит к лишним вопросам персоналу и снижает удовлетворённость.

Данная фича добавляет push-уведомления по двум каналам:

1. **Telegram** — для гостей, у которых привязан Telegram (через бот T-070)
2. **Web Push** — для гостей, согласившихся на уведомления в браузере (PWA)

Ключевые события для уведомлений:
- Бронь подтверждена / отменена / напоминание за 2 часа
- Заказ кальяна принят / готов

---

## 2. User Stories

- **US-110-1**: Как гость, сделавший бронь, я хочу получить уведомление в Telegram, когда администратор подтвердил или отменил мою бронь.
- **US-110-2**: Как гость, заказавший кальян, я хочу получить уведомление, когда кальян готов и несут ко мне.
- **US-110-3**: Как гость с активной бронью, я хочу получить напоминание за 2 часа до начала, чтобы не забыть.
- **US-110-4**: Как гость, я хочу управлять своими предпочтениями по каналам уведомлений (Telegram, Web Push, или отключить).
- **US-110-5**: Как гость без Telegram, я хочу подписаться на Web Push прямо в браузере, чтобы получать уведомления.

---

## 3. Functional Requirements / Функциональные требования

### 3.1 Канал: Telegram
- **FR-110-01**: При подтверждении брони (`BookingStatus.confirmed`) — отправить Telegram-сообщение гостю с деталями (дата, время, стол)
- **FR-110-02**: При отмене брони (`BookingStatus.cancelled`) — отправить Telegram-сообщение с причиной (если есть)
- **FR-110-03**: За 2 часа до `booking.time_from` — отправить напоминание (cron-задача каждые 15 минут)
- **FR-110-04**: При смене статуса заказа на `served` — отправить уведомление "Ваш кальян готов!"
- **FR-110-05**: При смене статуса заказа на `accepted` — отправить "Заказ принят, готовим"
- **FR-110-06**: Telegram-уведомление отправляется только если `Guest.telegram_id IS NOT NULL` (поле `telegram_id` типа `String(50)` в модели `Guest`)
- **FR-110-06a**: Статус `preparing` — намеренно без уведомлений (промежуточный технический статус, не значимый для гостя)
- **FR-110-07**: Отправка через прямой HTTP-запрос к Telegram Bot API (`httpx`, без экземпляра бота)

### 3.2 Канал: Web Push
- **FR-110-08**: Сервис регистрирует подписку браузера (`PushSubscription`) через `POST /api/push/subscribe`
- **FR-110-09**: При тех же событиях (FR-110-01...FR-110-05) — отправить Web Push всем активным подпискам гостя
- **FR-110-10**: Если доставка Web Push завершилась ошибкой 410 Gone — удалить подписку из БД (устаревший endpoint)
- **FR-110-11**: Сервис использует библиотеку `pywebpush` с VAPID-ключами из `.env`
- **FR-110-12**: Push-payload: `{ "title": "HookahBook", "body": "...", "url": "/guest/bookings/{id}" }`

### 3.3 Управление предпочтениями
- **FR-110-13**: `Guest.notification_preference` — JSON-поле `{"telegram": true, "web_push": true}`
- **FR-110-14**: `PUT /api/guest/notifications` — обновить предпочтения (требует guest JWT)
- **FR-110-15**: Если `notification_preference.telegram = false` — не отправлять Telegram-сообщения гостю
- **FR-110-16**: Если `notification_preference.web_push = false` — не отправлять Web Push гостю
- **FR-110-17**: По умолчанию при регистрации: оба канала `true`

### 3.4 Сервисный слой
- **FR-110-18**: `services/notifications.py` — единая точка входа `notify_guest(guest_id, event, context)` с роутингом по каналам
- **FR-110-19**: `services/webpush.py` — отправка Web Push через pywebpush
- **FR-110-20**: Уведомления отправляются асинхронно (FastAPI BackgroundTasks или Celery) — не блокируют основной запрос
- **FR-110-21**: Ошибки доставки логируются через structlog (уровень WARNING), не propagate в ответ API

### 3.5 Service Worker (PWA)
- **FR-110-22**: `frontend/public/sw.js` — Service Worker обрабатывает push-события и показывает уведомление через `self.registration.showNotification()`
- **FR-110-23**: Клик по уведомлению открывает URL из payload (или `/`)
- **FR-110-24**: Регистрация Service Worker — при первом входе авторизованного гостя

---

## 4. Non-Functional Requirements / Нефункциональные требования

- **NFR-110-01**: Уведомление должно уйти не позже чем через 5 секунд после триггерного события
- **NFR-110-02**: Retry при ошибке сети: до 3 попыток с backoff 1s / 5s / 30s
- **NFR-110-03**: VAPID-ключи хранятся только в `.env`, не коммитятся в репозиторий
- **NFR-110-04**: Telegram Bot Token не передаётся за пределы backend-сервиса
- **NFR-110-05**: Web Push работает только по HTTPS (Caddy обеспечивает TLS в prod)
- **NFR-110-06**: Подписки пагинированы при массовой рассылке (не более 50 за раз)

---

## 5. Database Changes / Изменения в БД

### 5.1 Новая таблица `push_subscriptions`

```sql
CREATE TABLE push_subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id    INTEGER NOT NULL REFERENCES guests(id) ON DELETE CASCADE,
    endpoint    TEXT NOT NULL UNIQUE,
    p256dh      TEXT NOT NULL,   -- public key
    auth        TEXT NOT NULL,   -- auth secret
    user_agent  TEXT,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at DATETIME
);
CREATE INDEX ix_push_subscriptions_guest_id ON push_subscriptions(guest_id);
```

### 5.2 Изменение таблицы `guests`

```sql
ALTER TABLE guests ADD COLUMN notification_preference JSON NOT NULL
    DEFAULT '{"telegram": true, "web_push": true}';
ALTER TABLE guests ADD COLUMN reminder_sent_at DATETIME;  -- для дедупликации напоминаний
```

### 5.3 SQLAlchemy-модель `PushSubscription`

Максимум 5 подписок на гостя — проверяется в сервисном слое перед INSERT через `SELECT COUNT ... FOR UPDATE`, а не только на уровне HTTP (защита от race condition).

```python
# backend/app/models/push_subscription.py
class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id           = Column(Integer, primary_key=True)
    guest_id     = Column(Integer, ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint     = Column(Text, nullable=False, unique=True)
    p256dh       = Column(Text, nullable=False)
    auth         = Column(Text, nullable=False)
    user_agent   = Column(Text)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True))

    guest = relationship("Guest", back_populates="push_subscriptions")
```

### 5.4 Изменение модели `Guest`

Используем `JSON` (как в `venues.working_hours`) для автоматической сериализации:

```python
# Добавить в backend/app/models/guest.py
notification_preference = Column(
    JSON,
    nullable=False,
    default=lambda: {"telegram": True, "web_push": True}
)
reminder_sent_at = Column(DateTime(timezone=True))  # последняя отправленная напоминалка
push_subscriptions = relationship("PushSubscription", back_populates="guest",
                                  cascade="all, delete-orphan")
```

### 5.5 Миграции Alembic

Файлы:
- `backend/alembic/versions/xxxx_add_push_subscriptions.py`
- `backend/alembic/versions/xxxx_add_guest_notification_preference.py`

---

## 6. API Endpoints / API-эндпоинты

### 6.1 `POST /api/push/subscribe`
**Описание**: Зарегистрировать Web Push подписку
**Auth**: Guest JWT (cookie `guest_token`)
**Rate limit**: 10 req/мин

```json
// Request
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": {
    "p256dh": "BNcR...",
    "auth": "tB3Q..."
  }
}

// Response 201 Created (upsert: если endpoint уже существует — вернуть 200 с тем же id)
{
  "id": 42,
  "created_at": "2026-03-07T12:00:00Z"
}
```

**Errors**:
- `401` — не авторизован
- `409` — достигнут лимит 5 подписок на гостя
- `422` — невалидный endpoint/ключи

---

### 6.2 `DELETE /api/push/subscribe/{subscription_id}`
**Описание**: Удалить Web Push подписку по ID (отписка). Использовать `id` из ответа `POST /subscribe`.
**Auth**: Guest JWT (гость может удалять только свои подписки — проверять `guest_id`)

```
DELETE /api/push/subscribe/42

// Response 204 No Content
// 404 — подписка не найдена
// 403 — чужая подписка
```

---

### 6.3 `GET /api/guest/notifications`
**Описание**: Получить настройки уведомлений текущего гостя
**Auth**: Guest JWT

```json
// Response 200
{
  "telegram": true,
  "web_push": false,
  "has_telegram": true,      // telegram_id != null (поле Guest.telegram_id)
  "push_subscriptions": 2    // кол-во активных подписок
}
```

---

### 6.4 `PUT /api/guest/notifications`
**Описание**: Обновить предпочтения уведомлений
**Auth**: Guest JWT

```json
// Request
{
  "telegram": false,
  "web_push": true
}

// Response 200
{
  "telegram": false,
  "web_push": true
}
```

---

## 7. Frontend Components / Компоненты фронтенда

### 7.1 `frontend/src/components/PushSubscribeButton.tsx`
- **Назначение**: Кнопка "Включить уведомления" / "Отключить уведомления" для Web Push
- **Логика**:
  1. Проверяет поддержку `serviceWorker` и `PushManager` в браузере
  2. Запрашивает разрешение через `Notification.requestPermission()`
  3. Подписывается через `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: VAPID_PUBLIC_KEY })`
  4. Отправляет подписку на `POST /api/push/subscribe`
- **Props**:
  ```typescript
  interface PushSubscribeButtonProps {
    onSuccess?: () => void;
    onError?: (err: Error) => void;
  }
  ```
- **Отображение**: кнопка с иконкой колокольчика, состояние `subscribed/unsubscribed/unsupported/loading/denied`
  - `denied` — пользователь ранее отказал в разрешении (`Notification.permission === 'denied'`). В этом состоянии кнопка показывает: "Уведомления заблокированы. Разрешите их в настройках браузера."
- **Передача VAPID_PUBLIC_KEY**: из переменной окружения Vite `VITE_VAPID_PUBLIC_KEY` (публичный ключ безопасен для клиента). Добавить в `.env.example` и `frontend/.env.example`.

### 7.2 `frontend/src/pages/GuestNotifications.tsx`
- **Маршрут**: `/guest/notifications`
- **Назначение**: Страница управления уведомлениями
- **Секции**:
  - Переключатель "Уведомления в Telegram" (disabled если нет `telegram_id`)
  - `PushSubscribeButton` — управление Web Push
  - Список активных подписок с кнопкой "Удалить"
- **Использует**: `GET /api/guest/notifications`, `PUT /api/guest/notifications`

### 7.3 `frontend/public/sw.js` — Service Worker
```javascript
self.addEventListener('push', event => {
  const data = event.data.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192.png',
      badge: '/icons/badge-72.png',
      data: { url: data.url }
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/'));
});
```

### 7.4 Интеграция в `frontend/src/pages/GuestProfile.tsx`
- Добавить ссылку/кнопку "Настройки уведомлений" → `/guest/notifications`
- При первом входе — показать ненавязчивый banner "Хотите получать уведомления?"

---

## 8. Integration Points / Точки интеграции

### 8.1 Существующие файлы, которые необходимо изменить

> **Внимание**: T-112 и T-113 требуют завершённого T-080 (guest auth). Все эндпоинты `/api/push/*` и `/api/guest/notifications` используют `get_current_guest` dependency из T-080 (`backend/app/dependencies.py`).

| Файл | Изменение |
|------|-----------|
| `backend/app/models/guest.py` | Добавить `notification_preference` (JSON), `reminder_sent_at` (DateTime), `telegram_blocked` (Boolean, default False), `push_subscriptions` relationship |
| `backend/app/routers/bookings.py` | После `admin PATCH /bookings/{id}/status` → вызов `notifications.notify_guest(...)` через `BackgroundTasks` (с отдельной DB-сессией) |
| `backend/app/routers/orders.py` | После `PUT /master/orders/{id}/status` → вызов `notifications.notify_guest(...)` через `BackgroundTasks` (с отдельной DB-сессией) |
| `backend/app/schemas/guest.py` | Добавить `NotificationPreference`, `NotificationSettings` schemas |
| `docker-compose.yml` | Добавить env-переменные `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` |
| `frontend/src/main.tsx` | Регистрация Service Worker при старте приложения |

### 8.2 Новые файлы

| Файл | Назначение |
|------|-----------|
| `backend/app/models/push_subscription.py` | SQLAlchemy-модель `PushSubscription` |
| `backend/app/routers/push.py` | Эндпоинты `POST /api/push/subscribe`, `DELETE /api/push/subscribe/{id}` |
| `backend/app/routers/guest_notifications.py` | Эндпоинты `/api/guest/notifications` (GET/PUT) |
| `backend/app/services/notifications.py` | Единая точка `notify_guest(guest_id, event, context)` |
| `backend/app/services/webpush.py` | Отправка Web Push через pywebpush |
| `backend/app/services/telegram_notify.py` | Отправка Telegram-уведомлений через httpx |
| `backend/app/schemas/push_subscription.py` | Pydantic schemas для push-эндпоинтов |
| `frontend/src/components/PushSubscribeButton.tsx` | UI-компонент управления подпиской |
| `frontend/src/pages/GuestNotifications.tsx` | Страница настроек уведомлений |
| `frontend/public/sw.js` | Service Worker для Web Push |

### 8.3 Переменные окружения (`.env`)

```dotenv
# Web Push (VAPID) — бэкенд
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_CLAIMS_EMAIL=admin@hookahbook.ru

# Telegram (уже есть из T-070, переиспользуем)
TELEGRAM_BOT_TOKEN=...
```

```dotenv
# frontend/.env  (публичный ключ безопасен для клиента)
VITE_VAPID_PUBLIC_KEY=...   # тот же VAPID_PUBLIC_KEY, без "PRIVATE"
```

Добавить `VITE_VAPID_PUBLIC_KEY` в `frontend/.env.example`.

### 8.4 `telegram_notify.py` — механизм отправки

```python
# backend/app/services/telegram_notify.py
import httpx

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

async def send_telegram_message(chat_id: str, text: str) -> None:
    """Send message directly via Telegram Bot API (no bot instance).

    chat_id matches Guest.telegram_id (String(50), not Integer).
    Telegram returns 200 OK with {"ok": false} on errors — must check both.
    On 403 Forbidden (bot blocked) — caller sets Guest.telegram_blocked=True (не обнуляет telegram_id).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5.0
        )
        response.raise_for_status()          # 4xx/5xx → HTTPStatusError
        result = response.json()
        if not result.get("ok"):
            raise ValueError(f"Telegram API error: {result.get('description')}")
```

### 8.5 `notifications.py` — роутер событий

```python
# backend/app/services/notifications.py
from enum import Enum

class NotificationEvent(Enum):
    BOOKING_CONFIRMED   = "booking_confirmed"
    BOOKING_CANCELLED   = "booking_cancelled"
    BOOKING_REMINDER    = "booking_reminder"
    ORDER_ACCEPTED      = "order_accepted"
    ORDER_SERVED        = "order_served"

async def notify_guest(guest_id: int, event: NotificationEvent, context: dict,
                       db: AsyncSession) -> None:
    """Route notification to enabled channels for the guest.

    IMPORTANT: Must be called with its own DB session (not the request session),
    since it runs inside BackgroundTasks after the response is sent.
    Uses Guest.telegram_id (String field, not telegram_chat_id).
    Skips Telegram if Guest.telegram_id is None.
    Errors are caught per-channel and logged via structlog (WARNING), never raised.
    """
    # 1. Load guest + preferences (own session)
    # 2. If preferences.telegram and guest.telegram_id → send via telegram_notify
    # 3. If preferences.web_push → send via webpush to all active subscriptions
    # Cron-task for reminders: uses Guest.reminder_sent_at to avoid duplicates —
    # only send if reminder_sent_at IS NULL or > 2.5 hours before booking.time_from
```

---

## 9. Acceptance Criteria / Критерии приёмки

- [ ] При подтверждении брони через admin-панель гость с `telegram_id` получает Telegram-сообщение в течение 5 секунд
- [ ] При отмене брони гость получает Telegram-сообщение с пометкой об отмене
- [ ] За 2 часа до брони гость получает Telegram-напоминание (cron-задача отрабатывает)
- [ ] При смене статуса заказа на `served` гость получает уведомление "Кальян готов" (Telegram и/или Web Push)
- [ ] Гость может подписаться на Web Push через страницу `/guest/notifications`
- [ ] Гость может отключить конкретный канал (telegram/web_push) — уведомления по нему прекращаются
- [ ] Устаревшая Web Push подписка (410) автоматически удаляется из БД
- [ ] Ошибка доставки уведомления не ломает основной бизнес-процесс (бронь остаётся подтверждённой)
- [ ] VAPID-ключи не попадают в код/репозиторий
- [ ] Service Worker корректно регистрируется, клик по уведомлению открывает нужный URL
- [ ] Unit-тесты: `telegram_notify.py` (mock httpx), `webpush.py` (mock pywebpush)

---

## 10. Engineering Tickets / Инженерные тикеты

| ID | Название | Тип | Зависимости | Оценка |
|----|----------|-----|-------------|--------|
| **T-110** | БД: `push_subscriptions`, `Guest.notification_preference`, миграции | backend | T-080 | S |
| **T-111** | Backend: `services/notifications.py`, `telegram_notify.py`, `webpush.py` | backend | T-110, T-070 | M |
| **T-112** | Backend API: `/api/push/subscribe`, `/api/guest/notifications` (GET/PUT) | backend | T-111 | S |
| **T-113** | Frontend: `sw.js` (SW), `PushSubscribeButton`, `GuestNotifications` страница | frontend | T-112, T-080 | M |

### Описание тикетов

**T-110** (S, ~3 ч):
- Создать `PushSubscription` модель в `backend/app/models/push_subscription.py`
- Добавить `notification_preference` (JSON), `reminder_sent_at` (DateTime) и `push_subscriptions` в модель `Guest`
- Написать и применить две миграции Alembic
- Добавить `APScheduler` в `backend/requirements.txt`
- Добавить VAPID env-vars в `.env.example`, `docker-compose.yml` и `frontend/.env.example`

**T-111** (M, ~6 ч):
- `telegram_notify.py` — async httpx, проверка `response.json()["ok"]`, тест с mock
- `webpush.py` — pywebpush отправка, обработка 410, тест с mock
- `notifications.py` — роутер событий `notify_guest(db)` с отдельной сессией, retry 3 попытки
- Интеграция в `bookings.py` и `orders.py` через `BackgroundTasks` (отдельная DB-сессия)
- APScheduler: cron каждые 15 мин, дедупликация через `Guest.reminder_sent_at`
- Настройка APScheduler для single-worker (Uvicorn `--workers 1` в RPi5)

**T-112** (S, ~3 ч):
- Router `push.py`: `POST /api/push/subscribe`, `DELETE /api/push/subscribe/{id}`
- Router `guest_notifications.py`: `GET /api/guest/notifications`, `PUT /api/guest/notifications`
- Pydantic schemas в `schemas/push_subscription.py`
- Регистрация роутеров в `main.py`
- Rate limiting: 10 req/мин для subscribe-эндпоинтов

**T-113** (M, ~5 ч):
- `frontend/public/sw.js` — Service Worker с `push` и `notificationclick` обработчиками
- Регистрация SW в `frontend/src/main.tsx`
- `PushSubscribeButton.tsx` — запрос разрешений, subscribe/unsubscribe, состояния UI
- `GuestNotifications.tsx` — страница настроек с переключателями каналов
- Интеграция ссылки в `GuestProfile.tsx`
- Тест подписки через Playwright (вручную, т.к. push API требует HTTPS)

---

## 11. Open Questions / Открытые вопросы

1. **Cron-задача для напоминаний**: использовать APScheduler (добавить в T-110). RPi5 деплоится с `--workers 1`, поэтому двойных запусков не будет. Дедупликация через `Guest.reminder_sent_at` — не отправлять, если поле уже установлено для текущей брони. **Решено: APScheduler + поле `reminder_sent_at`.**

2. **Массовые уведомления**: отправлять на все подписки гостя (до 5). Ограничение 5 подписок проверяется на уровне сервиса через `SELECT COUNT ... FOR UPDATE`. **Решено: лимит 5 подписок.**

3. **Telegram 403 Forbidden**: при блокировке бота не обнулять `telegram_id` (деструктивно). Вместо этого — установить флаг `telegram_blocked: bool` (добавить в модель `Guest`). Уведомления пропускаются при `telegram_blocked=True`. **Решено: флаг `telegram_blocked`, без потери `telegram_id`.**

4. **VAPID-ключи**: добавить `scripts/generate-vapid.py` (pywebpush: `webpush.generate_vapid_keys()`), задокументировать в `README.md`. Публичный ключ → `VITE_VAPID_PUBLIC_KEY` во фронтенд. **Решено: скрипт генерации.**

5. **Связь гостя с Telegram**: `Guest.telegram_id` (String(50)) устанавливается ботом T-070 через команду `/start phone_{phone_hash}`. Механизм нужно явно задокументировать в спецификации T-070. **Решено: задача для T-070.**
