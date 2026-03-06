# Feature: Учёт ресурсов через Webhook API

**Phase**: 3
**PRD Requirement**: — (Phase 3)
**Status**: Planned
**Dependencies**: T-050 (hookah preorder), T-031 (tobacco catalog)
**Date**: 2026-03-07

---

## 1. Overview / Обзор

Каждый заказ кальяна расходует конкретное количество табака. Сейчас HookahBook не интегрируется с системой учёта складских остатков — кальянщик вручную вносит списания в отдельную программу. Это порождает рассинхронизацию: статусы "в наличии" в приложении расходятся с реальными остатками.

Данная фича добавляет Webhook API: при ключевых событиях (заказ выполнен, бронь закрыта) HookahBook посылает HTTP POST с payload на зарегистрированные внешние URL. Внешняя система учёта (ERP, Google Sheets, 1С) подписывается на эти события и сама обрабатывает списание.

Подход "push webhooks" выбран как наиболее универсальный — не требует от внешней системы постоянного опроса API.

---

## 2. User Stories

- **US-120-1**: Как владелец заведения, я хочу, чтобы при каждом выполненном заказе кальяна автоматически отправлялась информация о расходе табака в мою систему учёта.
- **US-120-2**: Как владелец, я хочу зарегистрировать несколько webhook URL (для разных систем: учёт + аналитика) через admin-панель.
- **US-120-3**: Как владелец, я хочу видеть историю доставок webhooks: статус, код ответа, время, payload.
- **US-120-4**: Как владелец, я хочу получить повторную попытку отправки при временном сбое внешнего сервиса.
- **US-120-5**: Как разработчик внешней системы, я хочу верифицировать подпись webhook, чтобы удостовериться, что запрос пришёл от HookahBook.

---

## 3. Functional Requirements / Функциональные требования

### 3.1 Регистрация подписок (Webhook Subscriptions)
- **FR-120-01**: Admin может создать webhook подписку с полями: URL, secret, список событий, активность
- **FR-120-02**: Поддерживаемые события: `order.served`, `order.cancelled`, `booking.completed`, `booking.cancelled`, `tobacco.low_stock`
- **FR-120-03**: Один webhook URL может быть подписан на несколько событий одновременно
- **FR-120-04**: Максимум 10 webhook подписок на заведение
- **FR-120-05**: Secret хранится в зашифрованном виде (AES через `services/security.py`)
- **FR-120-06**: CRUD: создание, просмотр списка, обновление, удаление подписки

### 3.2 Доставка событий
- **FR-120-07**: При наступлении события — немедленная попытка доставки (BackgroundTask)
- **FR-120-08**: HTTP POST на webhook URL с заголовками:
  - `X-HookahBook-Event: order.served`
  - `X-HookahBook-Signature: sha256=<hmac-sha256>`
  - `X-HookahBook-Delivery: <delivery_uuid>`
  - `Content-Type: application/json`
- **FR-120-09**: HMAC-SHA256 подпись вычисляется от тела запроса с использованием secret подписки
- **FR-120-10**: Таймаут ожидания ответа — 10 секунд
- **FR-120-11**: Успешным считается ответ с HTTP 2xx
- **FR-120-12**: При неуспешном ответе — повторные попытки: 1 мин, 5 мин, 30 мин, 2 ч (до 4 попыток)
- **FR-120-13**: После 4 неудачных попыток — статус доставки `failed`, подписка деактивируется автоматически
- **FR-120-14**: Все попытки доставки записываются в `WebhookDelivery`

### 3.3 История доставок
- **FR-120-15**: Admin может просмотреть список доставок по подписке (`GET /api/webhooks/{id}/deliveries`)
- **FR-120-16**: Каждая запись: delivery_id, event, статус, HTTP-код ответа, количество попыток, время последней попытки
- **FR-120-17**: Хранить историю 90 дней, после — автоудаление (cron или SQLite TTL)
- **FR-120-18**: Admin может вручную запустить повторную доставку (`POST /api/webhooks/{id}/deliveries/{d_id}/retry`)

### 3.4 Payload событий

**`order.served`** — кальян отдан гостю (основное событие для списания):
```json
{
  "event": "order.served",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T15:30:00Z",
  "venue_id": 1,
  "data": {
    "order_id": 42,
    "table_id": 7,
    "guest_name": "Иван",
    "strength": 3,
    "items": [
      {"tobacco_id": 5, "tobacco_name": "Fumari Blueberry", "weight_grams": 25},
      {"tobacco_id": 8, "tobacco_name": "Tangiers Noir Melon", "weight_grams": 15}
    ],
    "total_tobacco_grams": 40,
    "served_at": "2026-03-07T15:28:00Z"
  }
}
```

**`order.cancelled`**:
```json
{
  "event": "order.cancelled",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T15:30:00Z",
  "venue_id": 1,
  "data": {
    "order_id": 42,
    "cancelled_at": "2026-03-07T15:10:00Z"
  }
}
```

**`booking.completed`**:
```json
{
  "event": "booking.completed",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T22:00:00Z",
  "venue_id": 1,
  "data": {
    "booking_id": 15,
    "table_id": 3,
    "guest_count": 4,
    "date": "2026-03-07",
    "time_from": "18:00",
    "time_to": "22:00"
  }
}
```

**`tobacco.low_stock`** — когда количество пачек табака опускается ниже порога:
```json
{
  "event": "tobacco.low_stock",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T15:31:00Z",
  "venue_id": 1,
  "data": {
    "tobacco_id": 5,
    "tobacco_name": "Fumari Blueberry",
    "weight_in_stock": 150,
    "threshold": 200
  }
}
```

---

## 4. Non-Functional Requirements / Нефункциональные требования

- **NFR-120-01**: Webhook-вызов не блокирует основной запрос (BackgroundTasks / очередь)
- **NFR-120-02**: HMAC-SHA256 подпись вычисляется для каждой доставки
- **NFR-120-03**: Secret хранится зашифрованным, не возвращается в API после создания (только маскированный вид)
- **NFR-120-04**: Retry реализован с экспоненциальным backoff (1 / 5 / 30 / 120 минут)
- **NFR-120-05**: Delivery payload ≤ 100 KB (с учётом состава заказа)
- **NFR-120-06**: Rate limit admin API: 60 req/мин
- **NFR-120-07**: История доставок не нагружает БД — отдельная таблица с индексом по `created_at`

---

## 5. Database Changes / Изменения в БД

### 5.1 Новая таблица `webhook_subscriptions`

```sql
CREATE TABLE webhook_subscriptions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id      INTEGER NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    url           TEXT NOT NULL,
    secret_enc    TEXT NOT NULL,  -- зашифрованный secret
    events        TEXT NOT NULL,  -- JSON array: ["order.served", "booking.completed"]
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_webhook_subscriptions_venue_id ON webhook_subscriptions(venue_id);
```

### 5.2 Новая таблица `webhook_deliveries`

```sql
CREATE TABLE webhook_deliveries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL REFERENCES webhook_subscriptions(id) ON DELETE CASCADE,
    delivery_uuid   TEXT NOT NULL UNIQUE,
    event           TEXT NOT NULL,        -- "order.served"
    payload         TEXT NOT NULL,        -- JSON payload (полная копия)
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|success|failed|retrying
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    last_http_code  INTEGER,
    last_error      TEXT,
    next_retry_at   DATETIME,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at    DATETIME             -- время успешной доставки
);
CREATE INDEX ix_webhook_deliveries_subscription_id ON webhook_deliveries(subscription_id);
CREATE INDEX ix_webhook_deliveries_created_at ON webhook_deliveries(created_at);
CREATE INDEX ix_webhook_deliveries_status ON webhook_deliveries(status);
```

### 5.3 SQLAlchemy-модели

```python
# backend/app/models/webhook.py
class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id          = Column(Integer, primary_key=True)
    venue_id    = Column(Integer, ForeignKey("venues.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    url         = Column(Text, nullable=False)
    secret_enc  = Column(Text, nullable=False)
    events      = Column(Text, nullable=False)      # JSON list
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now(), nullable=False)

    deliveries  = relationship("WebhookDelivery", back_populates="subscription",
                               cascade="all, delete-orphan")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id              = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("webhook_subscriptions.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    delivery_uuid   = Column(Text, nullable=False, unique=True)
    event           = Column(Text, nullable=False)
    payload         = Column(Text, nullable=False)
    status          = Column(Text, nullable=False, default="pending")
    attempt_count   = Column(Integer, nullable=False, default=0)
    last_http_code  = Column(Integer)
    last_error      = Column(Text)
    next_retry_at   = Column(DateTime(timezone=True))
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at    = Column(DateTime(timezone=True))

    subscription    = relationship("WebhookSubscription", back_populates="deliveries")
```

### 5.4 Миграции Alembic

- `backend/alembic/versions/xxxx_add_webhook_subscriptions.py`
- `backend/alembic/versions/xxxx_add_webhook_deliveries.py`

---

## 6. API Endpoints / API-эндпоинты

### 6.1 `GET /api/webhooks`
**Описание**: Список webhook-подписок заведения
**Auth**: Admin JWT
**Rate limit**: 60 req/мин

```json
// Response 200
[
  {
    "id": 1,
    "url": "https://my-erp.ru/hookah-webhook",
    "events": ["order.served", "booking.completed"],
    "is_active": true,
    "created_at": "2026-03-07T10:00:00Z"
  }
]
```

---

### 6.2 `POST /api/webhooks`
**Описание**: Создать webhook-подписку
**Auth**: Admin JWT (owner/admin)

```json
// Request
{
  "url": "https://my-erp.ru/hookah-webhook",
  "secret": "my-super-secret-key",
  "events": ["order.served", "booking.completed"]
}

// Response 201
{
  "id": 1,
  "url": "https://my-erp.ru/hookah-webhook",
  "secret_masked": "my-su****",
  "events": ["order.served", "booking.completed"],
  "is_active": true,
  "created_at": "2026-03-07T10:00:00Z"
}
```

**Errors**:
- `400` — невалидный URL или неизвестное событие
- `409` — достигнут лимит 10 подписок на заведение

---

### 6.3 `GET /api/webhooks/{id}`
**Auth**: Admin JWT

```json
// Response 200
{
  "id": 1,
  "url": "https://my-erp.ru/hookah-webhook",
  "secret_masked": "my-su****",
  "events": ["order.served"],
  "is_active": true,
  "created_at": "2026-03-07T10:00:00Z",
  "updated_at": "2026-03-07T10:00:00Z"
}
```

---

### 6.4 `PUT /api/webhooks/{id}`
**Описание**: Обновить подписку (URL, события, активность)
**Auth**: Admin JWT (owner/admin)

```json
// Request (все поля опциональны)
{
  "url": "https://new-erp.ru/hook",
  "secret": "new-secret",
  "events": ["order.served"],
  "is_active": false
}

// Response 200 — обновлённый объект
```

---

### 6.5 `DELETE /api/webhooks/{id}`
**Auth**: Admin JWT (owner/admin)
**Response**: `204 No Content`

---

### 6.6 `GET /api/webhooks/{id}/deliveries`
**Описание**: История доставок по подписке
**Auth**: Admin JWT
**Query params**: `?page=1&per_page=20&status=failed`

```json
// Response 200
{
  "items": [
    {
      "id": 101,
      "delivery_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "event": "order.served",
      "status": "success",
      "attempt_count": 1,
      "last_http_code": 200,
      "created_at": "2026-03-07T15:30:00Z",
      "delivered_at": "2026-03-07T15:30:02Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

### 6.7 `POST /api/webhooks/{id}/deliveries/{d_id}/retry`
**Описание**: Принудительная повторная доставка
**Auth**: Admin JWT (owner/admin)

```json
// Response 202
{
  "delivery_id": 101,
  "status": "retrying",
  "message": "Повторная доставка поставлена в очередь"
}
```

---

### 6.8 `POST /api/webhooks/{id}/test`
**Описание**: Отправить тестовый webhook с заглушкой payload
**Auth**: Admin JWT (owner/admin)

```json
// Response 200
{
  "http_code": 200,
  "response_time_ms": 143,
  "success": true
}
// или
{
  "http_code": 500,
  "error": "Connection refused",
  "success": false
}
```

---

## 7. Frontend Components / Компоненты фронтенда

### 7.1 `frontend/src/pages/admin/Webhooks.tsx`
- **Маршрут**: `/admin/webhooks`
- **Назначение**: Страница управления webhook-подписками
- **Элементы**:
  - Список подписок с индикатором активности
  - Кнопка "Добавить webhook" → открывает `WebhookForm`
  - Кнопка "Тест" → вызывает `POST /api/webhooks/{id}/test`, показывает результат
  - Кнопка "История" → переход на `WebhookDeliveries`

### 7.2 `frontend/src/components/admin/WebhookForm.tsx`
- **Назначение**: Модальная форма создания/редактирования webhook
- **Поля**:
  - URL (text input с валидацией URL)
  - Secret (password input, при редактировании — опциональный)
  - Events (multi-select чекбоксы: order.served, order.cancelled, booking.completed, booking.cancelled, tobacco.low_stock)
  - Is Active (toggle)
- **Логика**: POST/PUT запрос, показывает secret только при создании

### 7.3 `frontend/src/pages/admin/WebhookDeliveries.tsx`
- **Маршрут**: `/admin/webhooks/:id/deliveries`
- **Назначение**: История доставок конкретного webhook
- **Элементы**:
  - Таблица с колонками: ID, Event, Status, HTTP Code, Attempts, Time, Actions
  - Фильтр по статусу (all / success / failed / retrying)
  - Кнопка "Retry" для неудавшихся доставок
  - Кнопка "Просмотр payload" → показывает JSON в модале

---

## 8. Integration Points / Точки интеграции

### 8.1 Существующие файлы для изменения

| Файл | Изменение |
|------|-----------|
| `backend/app/routers/orders.py` | После смены статуса `served` → `webhook_service.emit("order.served", ...)` |
| `backend/app/routers/orders.py` | После смены статуса `cancelled` → `webhook_service.emit("order.cancelled", ...)` |
| `backend/app/routers/bookings.py` | После смены статуса `completed` → `webhook_service.emit("booking.completed", ...)` |
| `backend/app/routers/bookings.py` | После смены статуса `cancelled` → `webhook_service.emit("booking.cancelled", ...)` |
| `backend/app/routers/tobaccos.py` | После уменьшения in_stock ниже порога → `webhook_service.emit("tobacco.low_stock", ...)` |
| `backend/app/main.py` | Регистрация роутера `webhooks.py` |
| `frontend/src/pages/admin/AdminLayout.tsx` | Добавить пункт "Webhooks" в навигацию |

### 8.2 Новые файлы

| Файл | Назначение |
|------|-----------|
| `backend/app/models/webhook.py` | SQLAlchemy-модели `WebhookSubscription`, `WebhookDelivery` |
| `backend/app/routers/webhooks.py` | CRUD + deliveries + retry + test эндпоинты |
| `backend/app/schemas/webhook.py` | Pydantic schemas |
| `backend/app/services/webhook.py` | `WebhookService`: `emit()`, `deliver()`, retry-логика |
| `backend/alembic/versions/xxxx_add_webhooks.py` | Миграции для обеих таблиц |
| `frontend/src/pages/admin/Webhooks.tsx` | Страница управления |
| `frontend/src/components/admin/WebhookForm.tsx` | Форма создания/редактирования |
| `frontend/src/pages/admin/WebhookDeliveries.tsx` | История доставок |

### 8.3 `webhook.py` — сервисный слой

```python
# backend/app/services/webhook.py
import hashlib, hmac, uuid
import httpx
from app.models.webhook import WebhookSubscription, WebhookDelivery

RETRY_DELAYS = [60, 300, 1800, 7200]  # секунды: 1 мин, 5 мин, 30 мин, 2 ч

class WebhookService:
    async def emit(self, event: str, venue_id: int, data: dict, db: AsyncSession) -> None:
        """Find active subscriptions for event and schedule deliveries."""
        subscriptions = await self._get_active_subscriptions(event, venue_id, db)
        payload = self._build_payload(event, venue_id, data)
        for sub in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=sub.id,
                delivery_uuid=str(uuid.uuid4()),
                event=event,
                payload=json.dumps(payload),
            )
            db.add(delivery)
        await db.commit()
        # Schedule actual HTTP delivery via BackgroundTasks

    def _sign_payload(self, payload_bytes: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
```

### 8.4 Порог для `tobacco.low_stock`

Добавить поле `low_stock_threshold` (Integer, default 200 граммов) в модель `Tobacco`. При каждом обновлении `weight_in_stock` проверять: `weight_in_stock < low_stock_threshold`.

---

## 9. Acceptance Criteria / Критерии приёмки

- [ ] Admin может создать webhook подписку через admin-панель (URL + secret + события)
- [ ] Secret хранится зашифрованным, в API возвращается только маскированная версия
- [ ] При переводе заказа в `served` — webhook с event `order.served` доставляется на все активные URL
- [ ] Payload содержит полный состав заказа (tobacco_id, название, вес)
- [ ] Подпись `X-HookahBook-Signature` верна (HMAC-SHA256 от тела запроса)
- [ ] При HTTP 5xx от внешнего сервиса — 4 retry с задержками 1/5/30/120 мин
- [ ] После 4 неудачных попыток подписка деактивируется, admin видит статус `failed`
- [ ] Admin может просмотреть историю доставок: статус, HTTP-код, количество попыток
- [ ] Admin может принудительно повторить доставку
- [ ] "Test" кнопка позволяет проверить доступность URL без реального события
- [ ] Webhook-вызов не блокирует ответ API клиенту
- [ ] История очищается через 90 дней
- [ ] Unit-тесты: `emit()`, `_sign_payload()`, retry-логика (mock httpx)

---

## 10. Engineering Tickets / Инженерные тикеты

| ID | Название | Тип | Зависимости | Оценка |
|----|----------|-----|-------------|--------|
| **T-120** | БД: `webhook_subscriptions`, `webhook_deliveries`, `Tobacco.low_stock_threshold`, миграции | backend | T-031 | S |
| **T-121** | Backend service: `webhook.py` — `emit()`, `deliver()`, HMAC-подпись, retry-логика | backend | T-120 | M |
| **T-122** | Backend API: CRUD `/api/webhooks`, deliveries, retry, test эндпоинты | backend | T-121 | M |
| **T-123** | Интеграция emit() в orders/bookings/tobaccos роутеры (все 5 событий) | backend | T-122 | S |
| **T-124** | Frontend: `Webhooks.tsx`, `WebhookForm.tsx`, `WebhookDeliveries.tsx` | frontend | T-122 | M |

### Описание тикетов

**T-120** (S, ~3 ч):
- SQLAlchemy-модели `WebhookSubscription` и `WebhookDelivery`
- Добавить `low_stock_threshold` (Integer, default 200) в модель `Tobacco`
- Две миграции Alembic
- Схемы Pydantic в `schemas/webhook.py`

**T-121** (M, ~6 ч):
- `services/webhook.py`: `WebhookService.emit()`, `WebhookService.deliver()`
- HMAC-SHA256 подпись с `services/security.py` для шифрования/дешифрования secret
- Retry-очередь: APScheduler или `asyncio.create_task` с delayed execution
- Логирование через structlog (event, delivery_id, attempt, http_code)
- Unit-тесты с mock httpx

**T-122** (M, ~5 ч):
- Router `webhooks.py`: GET list, POST create, GET one, PUT update, DELETE
- Endpoint `GET /api/webhooks/{id}/deliveries` с пагинацией и фильтром
- Endpoint `POST /api/webhooks/{id}/deliveries/{d_id}/retry`
- Endpoint `POST /api/webhooks/{id}/test`
- Ограничение 10 подписок на заведение (check в create)
- Rate limiting и регистрация в `main.py`

**T-123** (S, ~2 ч):
- Добавить вызов `webhook_service.emit(...)` в BackgroundTasks в 5 местах:
  - `orders.py`: смена на `served`, `cancelled`
  - `bookings.py`: смена на `completed`, `cancelled`
  - `tobaccos.py`: обновление stock ниже threshold
- Формирование payload для каждого типа события

**T-124** (M, ~5 ч):
- `Webhooks.tsx` — страница списка с кнопками Test, History, Edit, Delete
- `WebhookForm.tsx` — модальная форма (create/edit) с multi-select событий
- `WebhookDeliveries.tsx` — таблица истории с фильтром и Retry
- Добавить `/admin/webhooks` в `AdminLayout.tsx`
- Тест через Playwright: создание подписки, проверка в списке

---

## 11. Open Questions / Открытые вопросы

1. **Retry-механизм**: BackgroundTasks FastAPI не персистентен (при рестарте теряются). Для надёжности нужен APScheduler с SQLite backend или Celery. Рекомендуется APScheduler (уже может быть в зависимостях для T-110), хранит задачи в SQLite.

2. **`tobacco.low_stock` порог**: 200 грамм по умолчанию — реалистично? Рекомендуется сделать настраиваемым per-tobacco и добавить глобальный дефолт в настройки заведения.

3. **Размер payload**: при большом заказе (10+ табаков) payload может быть объёмным. Добавить ли ограничение на состав или отдельный endpoint для получения полных деталей по ID?

4. **Верификация URL**: проверять ли, что webhook URL не указывает на localhost/внутренние адреса (SSRF-защита)? Обязательно — добавить blocklist для RFC1918 адресов и loopback.

5. **Очистка истории доставок**: через 90 дней — реализовать как cron или SQLite TTL trigger? Рекомендуется cron-задача в APScheduler (раз в день).

6. **Tenant isolation**: убедиться, что `GET /api/webhooks` возвращает только подписки заведения текущего admin (по `venue_id` из JWT). Критично для безопасности.
