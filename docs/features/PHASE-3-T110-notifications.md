# Feature: Уведомления (Telegram + Web Push)

**Phase**: 3
**PRD Requirement**: — (Phase 3)
**Status**: Planned
**Dependencies**: T-070 (telegram bot), T-080 (guest auth)
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
- **FR-110-06**: Telegram-уведомление отправляется только если `Guest.telegram_chat_id IS NOT NULL`
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
ALTER TABLE guests ADD COLUMN notification_preference TEXT NOT NULL
    DEFAULT '{"telegram": true, "web_push": true}';
```

### 5.3 SQLAlchemy-модель `PushSubscription`

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

```python
# Добавить в backend/app/models/guest.py
notification_preference = Column(
    Text,
    nullable=False,
    default='{"telegram": true, "web_push": true}'
)
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

// Response 200
{
  "id": 42,
  "created_at": "2026-03-07T12:00:00Z"
}
```

**Errors**:
- `401` — не авторизован
- `422` — невалидный endpoint/ключи

---

### 6.2 `DELETE /api/push/subscribe`
**Описание**: Удалить Web Push подписку (отписка)
**Auth**: Guest JWT

```json
// Request
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/..."
}

// Response 204 No Content
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
  "has_telegram": true,      // telegram_chat_id != null
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
- **Отображение**: кнопка с иконкой колокольчика, состояние `subscribed/unsubscribed/unsupported/loading`

### 7.2 `frontend/src/pages/GuestNotifications.tsx`
- **Маршрут**: `/guest/notifications`
- **Назначение**: Страница управления уведомлениями
- **Секции**:
  - Переключатель "Уведомления в Telegram" (disabled если нет telegram_chat_id)
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

| Файл | Изменение |
|------|-----------|
| `backend/app/models/guest.py` | Добавить `notification_preference` (Text), `push_subscriptions` relationship |
| `backend/app/routers/bookings.py` | После `admin PATCH /bookings/{id}/status` → вызов `notifications.notify_guest(...)` |
| `backend/app/routers/orders.py` | После `PUT /master/orders/{id}/status` → вызов `notifications.notify_guest(...)` |
| `backend/app/schemas/guest.py` | Добавить `NotificationPreference`, `NotificationSettings` schemas |
| `docker-compose.yml` | Добавить env-переменные `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` |
| `frontend/src/main.tsx` | Регистрация Service Worker при старте приложения |

### 8.2 Новые файлы

| Файл | Назначение |
|------|-----------|
| `backend/app/models/push_subscription.py` | SQLAlchemy-модель `PushSubscription` |
| `backend/app/routers/push.py` | Эндпоинты `/api/push/subscribe`, `/api/push/unsubscribe` |
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
# Web Push (VAPID)
VAPID_PRIVATE_KEY=...
VAPID_PUBLIC_KEY=...
VAPID_CLAIMS_EMAIL=admin@hookahbook.ru

# Telegram (уже есть из T-070, переиспользуем)
TELEGRAM_BOT_TOKEN=...
```

### 8.4 `telegram_notify.py` — механизм отправки

```python
# backend/app/services/telegram_notify.py
import httpx

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

async def send_telegram_message(chat_id: int | str, text: str) -> None:
    """Send message directly via Telegram Bot API (no bot instance)."""
    async with httpx.AsyncClient() as client:
        await client.post(
            TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN),
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5.0
        )
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

async def notify_guest(guest_id: int, event: NotificationEvent, context: dict) -> None:
    """Route notification to enabled channels for the guest."""
    # 1. Load guest + preferences
    # 2. If telegram enabled and telegram_chat_id set → send via telegram_notify
    # 3. If web_push enabled → send via webpush to all active subscriptions
    # Errors are caught and logged, not raised
```

---

## 9. Acceptance Criteria / Критерии приёмки

- [ ] При подтверждении брони через admin-панель гость с telegram_chat_id получает Telegram-сообщение в течение 5 секунд
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
- Добавить `notification_preference` и `push_subscriptions` в модель `Guest`
- Написать и применить две миграции Alembic
- Добавить VAPID env-vars в `.env.example` и `docker-compose.yml`

**T-111** (M, ~6 ч):
- `telegram_notify.py` — async httpx-вызов к Telegram Bot API, тест с mock
- `webpush.py` — pywebpush отправка, обработка 410, тест с mock
- `notifications.py` — роутер событий `notify_guest()`, retry-логика (3 попытки)
- Интеграция вызовов в `routers/bookings.py` и `routers/orders.py` (BackgroundTasks)
- Cron-задача для напоминаний (APScheduler или отдельный скрипт)

**T-112** (S, ~3 ч):
- Router `push.py`: `POST /api/push/subscribe`, `DELETE /api/push/subscribe`
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

1. **Cron-задача для напоминаний**: использовать APScheduler (уже в зависимостях?) или отдельный скрипт, запускаемый через `cron` в Docker? APScheduler предпочтительнее — не требует отдельного контейнера.

2. **Массовые уведомления**: если у гостя 5 активных Web Push подписок (разные браузеры) — отправлять на все? Предлагается: да, до 5 подписок на гостя (ограничить в `POST /subscribe`).

3. **Telegram: что если гость заблокировал бота?** — Telegram вернёт 403 Forbidden. Предлагается: поставить `telegram_chat_id = NULL` и логировать, чтобы не пытаться снова.

4. **VAPID-ключи**: кто генерирует при деплое? Предлагается: добавить в `scripts/generate-vapid.py` и документировать в `README.md`.

5. **Связь гостя с Telegram**: как именно `telegram_chat_id` появляется в Guest? Через бота T-070 (команда `/start` с phone_hash deep link). Этот механизм нужно явно задокументировать в T-070.
