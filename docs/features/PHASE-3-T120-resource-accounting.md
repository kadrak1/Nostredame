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
- **FR-120-01**: Admin может создать webhook подписку с полями: URL, secret (мин. 16 символов), список событий, активность
- **FR-120-02**: Поддерживаемые события: `order.served`, `order.cancelled`, `booking.completed`, `booking.cancelled`, `tobacco.low_stock`
- **FR-120-03**: Один webhook URL может быть подписан на несколько событий одновременно
- **FR-120-04**: Максимум 10 webhook подписок на заведение
- **FR-120-05**: Secret хранится зашифрованным через `services/security.py` (Fernet). В API возвращается только маскированная версия: последние 4 символа (`mask_secret()` в `security.py`)
- **FR-120-06**: CRUD: создание, просмотр списка, обновление, удаление подписки
- **FR-120-07a** (SSRF-защита): Перед сохранением и перед каждой доставкой URL проходит валидацию:
  - Разрешены только схемы `https://` (или `http://` с предупреждением в логе)
  - DNS-резолвинг + проверка IP непосредственно перед соединением (DNS rebinding protection)
  - Блокировать диапазоны: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (AWS metadata), `::1`, `fc00::/7`
  - Разрешены только порты 80 и 443
  - SSRF-валидация применяется также к `POST /api/webhooks/{id}/test`
- **FR-120-08a** (Tenant isolation): Все операции по `{id}` (GET, PUT, DELETE, deliveries, retry, test) проверяют `subscription.venue_id == current_user.venue_id`. При несоответствии — `404` (не `403`, не раскрывать существование). Реализовать через хелпер `_get_subscription_or_404(db, sub_id, venue_id)` по аналогии с `_get_admin_booking`.

### 3.2 Доставка событий
- **FR-120-09**: При наступлении события — первая попытка немедленно через `BackgroundTasks`; retry-попытки — через APScheduler (`apscheduler>=3.10`, SQLite job store)
- **FR-120-10**: HTTP POST на webhook URL с заголовками:
  - `X-HookahBook-Event: order.served`
  - `X-HookahBook-Signature: sha256=<hmac-sha256>`
  - `X-HookahBook-Delivery: <delivery_uuid>`
  - `X-HookahBook-Timestamp: <unix_timestamp>`
  - `X-HookahBook-Version: 1`
  - `Content-Type: application/json`
- **FR-120-11**: HMAC-SHA256 подпись: `HMAC-SHA256(plaintext_secret, "<timestamp>.<payload_bytes>")`. Перед вычислением HMAC — вызвать `security.decrypt_secret(sub.secret_enc)` (Fernet decrypt). Рекомендация получателю: отклонять события старше 5 минут по `X-HookahBook-Timestamp`.
- **FR-120-12**: Таймаут ожидания ответа — 10 секунд
- **FR-120-13**: Успешным считается ответ с HTTP 2xx
- **FR-120-14**: При неуспешном ответе — retry: 1 мин, 5 мин, 30 мин, 2 ч (4 попытки через APScheduler jobs)
- **FR-120-15**: После 4 неудачных попыток — статус `failed`, подписка деактивируется автоматически; pending APScheduler jobs для этой delivery отменяются
- **FR-120-16**: Все попытки записываются в `WebhookDelivery`. `attempt_count` обновляется атомарно (SELECT FOR UPDATE)
- **FR-120-17**: Ручной retry (`POST .../retry`) возвращает `409 Conflict`, если delivery уже в статусе `retrying` (защита от двойной доставки)

### 3.3 История доставок
- **FR-120-18**: Admin может просмотреть список доставок по подписке (`GET /api/webhooks/{id}/deliveries`), `per_page` максимум 100
- **FR-120-19**: Каждая запись: delivery_id, event, статус, HTTP-код ответа, количество попыток, время последней попытки
- **FR-120-20**: Хранить историю 90 дней, после — автоудаление APScheduler cron (раз в день). Перед удалением отменять APScheduler jobs с matching `delivery.id`
- **FR-120-21**: Admin может вручную запустить повторную доставку (`POST /api/webhooks/{id}/deliveries/{d_id}/retry`), если статус НЕ `retrying`

### 3.4 Payload событий

Все payloads содержат поле `"version": "1"` для версионирования схемы.

**`order.served`** — кальян отдан гостю (основное событие для списания):
```json
{
  "version": "1",
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

**`order.cancelled`** — включает полный состав, чтобы внешняя система могла отменить списание:
```json
{
  "version": "1",
  "event": "order.cancelled",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T15:30:00Z",
  "venue_id": 1,
  "data": {
    "order_id": 42,
    "table_id": 7,
    "items": [
      {"tobacco_id": 5, "tobacco_name": "Fumari Blueberry", "weight_grams": 25},
      {"tobacco_id": 8, "tobacco_name": "Tangiers Noir Melon", "weight_grams": 15}
    ],
    "total_tobacco_grams": 40,
    "cancelled_at": "2026-03-07T15:10:00Z"
  }
}
```

**`booking.completed`**:
```json
{
  "version": "1",
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

**`booking.cancelled`**:
```json
{
  "version": "1",
  "event": "booking.cancelled",
  "delivery_id": "uuid",
  "timestamp": "2026-03-07T12:00:00Z",
  "venue_id": 1,
  "data": {
    "booking_id": 15,
    "table_id": 3,
    "date": "2026-03-07",
    "time_from": "18:00",
    "time_to": "22:00",
    "cancelled_at": "2026-03-07T12:00:00Z"
  }
}
```

**`tobacco.low_stock`** — когда остаток опускается ниже порога (дебаунс: не чаще 1 раза в 4 часа на табак, контролируется через `Tobacco.last_low_stock_notified_at`):
```json
{
  "version": "1",
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
- **NFR-120-03**: Secret хранится зашифрованным (Fernet), в API возвращается только маскированная версия — последние 4 символа (`"****key"`). Минимальная длина secret — 16 символов.
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
  "secret_masked": "****cret",   // последние 4 символа (mask_secret() в security.py)
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
  "secret_masked": "****cret",   // последние 4 символа (mask_secret() в security.py)
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

APScheduler инициализируется один раз при старте FastAPI (lifespan), использует SQLite job store (`jobs.db`). Деплой на RPi5 — `--workers 1`, дублирование задач исключено.

```python
# backend/app/services/webhook.py
import hashlib, hmac as hmac_mod, uuid, time as time_mod
import httpx
from app.models.webhook import WebhookSubscription, WebhookDelivery
from app.services.security import decrypt_secret   # NEW: separate from decrypt_phone

RETRY_DELAYS = [60, 300, 1800, 7200]  # секунды: 1 мин, 5 мин, 30 мин, 2 ч

class WebhookService:
    async def emit(self, event: str, venue_id: int, data: dict, db: AsyncSession) -> None:
        """Find active subscriptions for event and schedule deliveries.

        Filters subscriptions by venue_id AND event (uses JSON_EACH SQLite function
        to avoid LIKE false positives: WHERE json_each.value = :event).
        """
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
        # First attempt via BackgroundTasks (immediate)
        # Retries scheduled via APScheduler with RETRY_DELAYS

    def _sign_payload(self, payload_bytes: bytes, timestamp: int, secret_enc: str) -> str:
        """Compute HMAC-SHA256 over '<timestamp>.<payload_bytes>'.

        CRITICAL: Must decrypt secret before use.
        secret_enc is Fernet-encrypted; decrypt_secret() returns plaintext.
        import as hmac_mod to avoid shadowing stdlib module name.
        """
        plain_secret = decrypt_secret(secret_enc)  # Fernet decrypt
        message = f"{timestamp}.".encode() + payload_bytes
        return "sha256=" + hmac_mod.new(
            plain_secret.encode(), message, hashlib.sha256
        ).hexdigest()
```

Добавить в `backend/app/services/security.py`:
```python
def decrypt_secret(encrypted: str) -> str:
    """Decrypt Fernet-encrypted webhook secret. Separate from decrypt_phone."""
    ...  # same Fernet key from settings
```

Добавить в `backend/requirements.txt`: `apscheduler>=3.10.0`.

### 8.4 Порог для `tobacco.low_stock` и дебаунс

Добавить поля в модель `Tobacco`:
- `low_stock_threshold` (Integer, default 200) — настраиваемый порог
- `last_low_stock_notified_at` (DateTime, nullable) — дебаунс: событие не генерируется чаще 1 раза в 4 часа

Логика: при обновлении `weight_in_stock` проверять `weight_in_stock < low_stock_threshold` И `(last_low_stock_notified_at IS NULL OR last_low_stock_notified_at < now() - 4 hours)`.

> **Зависимость T-123 от T-050**: `backend/app/routers/orders.py` не существует в текущей кодовой базе и будет создан в T-050. T-123 должен зависеть от T-050 (или T-060).

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
| **T-120** | БД: `webhook_subscriptions`, `webhook_deliveries`, `Tobacco.low_stock_threshold/last_low_stock_notified_at`, миграции; добавить `apscheduler>=3.10` в requirements.txt; `decrypt_secret()` в security.py | backend | T-031 | S |
| **T-121** | Backend service: `webhook.py` — `emit()`, `deliver()`, HMAC (decrypt → sign), APScheduler retry, SSRF validator | backend | T-120 | L |
| **T-122** | Backend API: CRUD `/api/webhooks`, deliveries (per_page≤100), retry (409 for retrying), test; tenant isolation via `_get_subscription_or_404` | backend | T-121 | M |
| **T-123** | Интеграция emit() в orders/bookings/tobaccos роутеры (все 5 событий), low_stock debounce | backend | T-122, T-050 | S |
| **T-124** | Frontend: `Webhooks.tsx`, `WebhookForm.tsx`, `WebhookDeliveries.tsx` | frontend | T-122 | M |

### Описание тикетов

**T-120** (S, ~3 ч):
- SQLAlchemy-модели `WebhookSubscription` и `WebhookDelivery`
- Добавить `low_stock_threshold` (Integer, default 200) в модель `Tobacco`
- Две миграции Alembic
- Схемы Pydantic в `schemas/webhook.py`

**T-121** (L, ~10 ч):
- `services/webhook.py`: `WebhookService.emit()`, `WebhookService.deliver()`
- HMAC: `decrypt_secret()` → `_sign_payload(payload_bytes, timestamp, secret_enc)` с `X-HookahBook-Timestamp`
- APScheduler с SQLite job store: init в `main.py` lifespan, graceful shutdown
- SSRF-валидатор: DNS resolve + проверка всех RFC1918/loopback диапазонов, DNS rebinding protection
- SELECT FOR UPDATE для `attempt_count`, 409 при ручном retry status=retrying
- APScheduler cron для 90-дневной очистки истории
- Логирование через structlog, unit-тесты с mock httpx и mock APScheduler

**T-122** (M, ~5 ч):
- Router `webhooks.py`: GET list, POST create, GET one, PUT update, DELETE
- Хелпер `_get_subscription_or_404(db, sub_id, venue_id)` — tenant isolation (404 при несовпадении venue_id)
- Endpoint `GET /api/webhooks/{id}/deliveries` с пагинацией (per_page ≤ 100) и фильтром
- Endpoint `POST /api/webhooks/{id}/deliveries/{d_id}/retry` (409 если status=retrying)
- Endpoint `POST /api/webhooks/{id}/test` (синхронный, таймаут 10с, SSRF-валидация)
- Ограничение 10 подписок на заведение, min 16 символов для secret
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

1. **Retry-механизм**: **Решено** — APScheduler с SQLite job store. Первая попытка через `BackgroundTasks`, retry через APScheduler jobs. `--workers 1` на RPi5. Задача в T-121.

2. **`tobacco.low_stock` порог**: **Решено** — настраиваемый per-tobacco через `Tobacco.low_stock_threshold` (default 200г). Дебаунс `last_low_stock_notified_at` — не чаще 1 раза в 4 часа. Задача в T-120/T-123.

3. **Размер payload**: **Решено** — NFR-120-05 ограничивает payload ≤ 100 KB. При типичном заказе (5-6 табаков) payload ~1 KB — нет проблем. Отдельный endpoint не нужен.

4. **SSRF-защита**: **Решено** — перенесено в FR-120-07a. Полный список блокируемых диапазонов (включая `169.254.0.0/16`), DNS rebinding protection, ограничение схемы и портов. Задача в T-121.

5. **Очистка истории доставок**: **Решено** — APScheduler cron раз в день. Перед удалением — отмена APScheduler jobs. Задача в T-121.

6. **Tenant isolation**: **Решено** — перенесено в FR-120-08a. Хелпер `_get_subscription_or_404(db, sub_id, venue_id)` — 404 при несовпадении. Задача в T-122.
