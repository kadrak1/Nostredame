# Фаза 3 — Декомпозиция на инженерные тикеты

**Scope**: История заказов и повтор · Push-уведомления · Webhook API для интеграций

---

## Статус прогресса (обновлено: 2026-03-07)

| Тикет | Название | Тип | Оценка | Статус | Спека |
|-------|----------|-----|--------|--------|-------|
| T-100 | FavoriteMix модель + миграция | backend | S | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-101 | GET /api/guest/last-order + GET /api/guest/orders | backend | M | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-102 | POST /api/guest/orders/{id}/repeat + проверка наличия | backend | M | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-103 | CRUD /api/guest/favorites + лимит 5 | backend | S | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-104 | RepeatOrderButton + интеграция в HookahBuilder, Booking, TableOrder | frontend | M | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-105 | OrderHistory + Favorites страницы + GuestNav | frontend | M | ⬜ Не начат | [T-100](features/PHASE-3-T100-order-history-and-repeat.md) |
| T-110 | БД: push_subscriptions, Guest.notification_preference, миграции | backend | S | ⬜ Не начат | [T-110](features/PHASE-3-T110-notifications.md) |
| T-111 | Backend: services/notifications.py, telegram_notify.py, webpush.py | backend | M | ⬜ Не начат | [T-110](features/PHASE-3-T110-notifications.md) |
| T-112 | Backend API: /api/push/subscribe, /api/guest/notifications (GET/PUT) | backend | S | ⬜ Не начат | [T-110](features/PHASE-3-T110-notifications.md) |
| T-113 | Frontend: sw.js (SW), PushSubscribeButton, GuestNotifications страница | frontend | M | ⬜ Не начат | [T-110](features/PHASE-3-T110-notifications.md) |
| T-120 | БД: webhook_subscriptions, webhook_deliveries, Tobacco.low_stock_threshold, миграции | backend | S | ⬜ Не начат | [T-120](features/PHASE-3-T120-resource-accounting.md) |
| T-121 | Backend service: webhook.py — emit(), deliver(), HMAC, APScheduler retry, SSRF | backend | L | ⬜ Не начат | [T-120](features/PHASE-3-T120-resource-accounting.md) |
| T-122 | Backend API: CRUD /api/webhooks, deliveries, retry, tenant isolation | backend | M | ⬜ Не начат | [T-120](features/PHASE-3-T120-resource-accounting.md) |
| T-123 | Интеграция emit() в orders/bookings/tobaccos роутеры (5 событий) | backend | S | ⬜ Не начат | [T-120](features/PHASE-3-T120-resource-accounting.md) |
| T-124 | Frontend: Webhooks.tsx, WebhookForm.tsx, WebhookDeliveries.tsx | frontend | M | ⬜ Не начат | [T-120](features/PHASE-3-T120-resource-accounting.md) |

**Прогресс**: 0 / 15 тикетов завершено (0%)

---


## Эпик 10: История заказов и повтор кальяна

> **Спека**: [PHASE-3-T100-order-history-and-repeat.md](features/PHASE-3-T100-order-history-and-repeat.md)

Авторизованный гость видит историю заказов, может повторить любой заказ в один клик. Поддержка избранных миксов. `RepeatOrderButton` встраивается в `Booking.tsx` и `TableOrder.tsx`.

### T-100: ⬜ FavoriteMix модель + миграция
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-080
- `FavoriteMix`: id, guest_id (FK), name (str, 1-50), items (JSON: [{tobacco_id, weight_grams}]), created_at
- Индекс на guest_id
- Ограничение: максимум 5 миксов на гостя (проверка на уровне сервиса)
- Миграция Alembic
- **AC**: Миграция проходит, FavoriteMix создаётся

### T-101: ⬜ История заказов API
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-080, T-060
- `GET /api/guest/orders` — история заказов гостя (пагинация, фильтр by status), только `get_current_guest()`
- `GET /api/guest/last-order` — последний заказ (для быстрого повтора), с составом items
- Возвращать: order_id, date, table_number, items[], status, source
- **AC**: Авторизованный гость получает список заказов, неавторизованный — 401

### T-102: ⬜ POST /api/guest/orders/{id}/repeat
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-101
- `POST /api/guest/orders/{id}/repeat` — создать новый HookahOrder с теми же OrderItems
- Проверка наличия: если табак `in_stock=False`, вернуть `409 Conflict` с `unavailable_items[]`
- Принимает `booking_id` или `table_id` (куда привязать повтор)
- **AC**: Повтор создаёт заказ с теми же позициями; недоступные табаки возвращают 409

### T-103: ⬜ CRUD избранных миксов
**Тип**: backend · **Оценка**: S (~3 ч) · **Зависимости**: T-100
- `GET /api/guest/favorites` — список избранных миксов гостя
- `POST /api/guest/favorites` — сохранить микс (из текущего заказа)
- `PUT /api/guest/favorites/{id}` — переименовать
- `DELETE /api/guest/favorites/{id}` — удалить
- Лимит: 5 миксов, при превышении — 422
- **AC**: CRUD работает, лимит 5 соблюдается

### T-104: ⬜ RepeatOrderButton + интеграция
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-053, T-063, T-101
- `RepeatOrderButton.tsx` — кнопка "Ваш последний кальян: [название] → Повторить"
- Отображается только для авторизованных гостей, когда `GET /api/guest/last-order` не пустой
- При недоступных табаках — диалог с предложением замены
- Интеграция в `HookahBuilder.tsx` (слот из T-053) и `TableOrder.tsx` (слот из T-063)
- **AC**: Авторизованный гость видит кнопку повтора, нажатие заполняет HookahBuilder

### T-105: ⬜ OrderHistory + Favorites страницы + GuestNav
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-101, T-103
- `OrderHistory.tsx` — `/guest/orders`: карточки заказов с кнопкой "Повторить"
- `Favorites.tsx` — `/guest/favorites`: список избранных с кнопками "Заказать", "Переименовать", "Удалить"
- `GuestNav.tsx` — навигация в личном кабинете гостя (ссылки: Профиль, История, Избранное, Уведомления)
- **AC**: Страницы доступны только для авторизованных гостей

---

## Эпик 11: Push-уведомления

> **Спека**: [PHASE-3-T110-notifications.md](features/PHASE-3-T110-notifications.md)

Telegram + Web Push уведомления о статусе бронирования и готовности кальяна. APScheduler для напоминаний. Гость управляет настройками уведомлений.

### T-110: ⬜ БД: PushSubscription, Guest.notification_preference, миграции
**Тип**: backend · **Оценка**: S (~3 ч) · **Зависимости**: T-080
- `PushSubscription` модель: id, guest_id, endpoint, p256dh, auth, user_agent, created_at
- Добавить в Guest: `notification_preference` (Column(JSON)), `reminder_sent_at` (DateTime), `telegram_blocked` (bool, default False)
- Ограничение: максимум 5 подписок на гостя (через SELECT COUNT ... FOR UPDATE)
- Добавить `apscheduler>=3.10`, `pywebpush>=2.0` в `requirements.txt`
- VAPID env-vars: `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL` в `.env.example`
- `VITE_VAPID_PUBLIC_KEY` в `frontend/.env.example`
- **AC**: Миграции применены, VAPID-переменные задокументированы

### T-111: ⬜ Backend services: notifications.py, telegram_notify.py, webpush.py
**Тип**: backend · **Оценка**: M (~6 ч) · **Зависимости**: T-110, T-070
- `telegram_notify.py` — async httpx + проверка `response.json()["ok"]` + обработка 403 → `telegram_blocked=True`
- `webpush.py` — pywebpush отправка, удаление подписки при 410
- `notifications.py` — роутер `notify_guest(event, guest, db)` для обоих каналов, retry 3 попытки
- APScheduler cron каждые 15 мин: напоминание за 2 ч до брони (дедупликация через `reminder_sent_at`)
- Интеграция в `bookings.py` и `orders.py` через `BackgroundTasks` (отдельная DB-сессия)
- **AC**: Тест с mock httpx: уведомление доходит, 403 устанавливает `telegram_blocked`

### T-112: ⬜ Push API: /api/push/subscribe + /api/guest/notifications
**Тип**: backend · **Оценка**: S (~3 ч) · **Зависимости**: T-111
- `POST /api/push/subscribe` — upsert подписки (201 при создании, 200 при обновлении)
- `DELETE /api/push/subscribe/{id}` — отписка (path param)
- `GET /api/guest/notifications` — настройки уведомлений гостя
- `PUT /api/guest/notifications` — изменить `notification_preference`
- Rate limit: 10 req/мин для subscribe-эндпоинтов
- **AC**: Подписка сохраняется, DELETE удаляет по ID, настройки обновляются

### T-113: ⬜ Frontend: sw.js, PushSubscribeButton, GuestNotifications
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-112, T-080
- `frontend/public/sw.js` — Service Worker с `push` и `notificationclick` обработчиками
- Регистрация SW в `frontend/src/main.tsx`
- `PushSubscribeButton.tsx` — 4 состояния: loading/granted/denied/unsupported
- `GuestNotifications.tsx` — страница `/guest/notifications` с переключателями telegram/web_push
- Ссылка на страницу из `GuestNav.tsx`
- `scripts/generate-vapid.py` — генерация VAPID-ключей (pywebpush)
- **AC**: Подписка на push работает в HTTPS-окружении, UI отражает текущий статус

---


## Эпик 12: Webhook API для интеграций (учёт ресурсов)

> **Спека**: [PHASE-3-T120-resource-accounting.md](features/PHASE-3-T120-resource-accounting.md)

Push-вебхуки для внешних систем (ERP, учёт склада). Подписчик получает события при смене статуса заказа/брони и при низком запасе табака. HMAC-SHA256 подпись, APScheduler retry, SSRF-защита.

### T-120: ⬜ БД: webhook_subscriptions, webhook_deliveries + миграции
**Тип**: backend · **Оценка**: S (~3 ч) · **Зависимости**: T-031
- `WebhookSubscription`: id, venue_id (FK), url, secret_enc (Fernet), events (JSON), is_active, created_at
- `WebhookDelivery`: id, subscription_id (FK), event, payload (JSON), status, attempt_count, next_retry_at, created_at
- Добавить в `Tobacco`: `low_stock_threshold` (Integer, default 200), `last_low_stock_notified_at` (DateTime)
- Добавить `apscheduler>=3.10` в `requirements.txt` (если не добавлен в T-110)
- Функция `decrypt_secret(secret_enc: str) -> str` в `services/security.py` (Fernet decrypt)
- Маскировка секрета: последние 4 символа (`****cret`) через `mask_secret()` в `security.py`
- **AC**: Миграции применены, `decrypt_secret` работает с ключом из `.env`

### T-121: ⬜ Backend service: webhook.py — emit, deliver, HMAC, retry
**Тип**: backend · **Оценка**: L (~10 ч) · **Зависимости**: T-120
- `WebhookService.emit(event, payload, db)` — находит активные подписки, создаёт `WebhookDelivery`, шедулит доставку
- `WebhookService.deliver(delivery_id)` — один HTTP POST с таймаутом 10 с
- HMAC: `decrypt_secret(sub.secret_enc)` → `sha256(f"{ts}.{payload}")` → заголовок `X-HookahBook-Signature-256`
- Заголовки: `X-HookahBook-Timestamp`, `X-HookahBook-Version: 1`, `X-HookahBook-Event`
- APScheduler с SQLite job store: init в `main.py` lifespan, graceful shutdown
- Retry: 1 мин → 5 мин → 30 мин (максимум 3 попытки), затем `status=failed`
- SELECT FOR UPDATE для `attempt_count` (идемпотентность при параллельных retry)
- SSRF-валидатор: DNS resolve + блокировка RFC1918/loopback/link-local, порты только 80/443
- APScheduler cron: очистка истории старше 90 дней (ежедневно)
- **AC**: Событие доставляется, HMAC верифицируется получателем, SSRF-URL отклоняется

### T-122: ⬜ Backend API: CRUD /api/webhooks + deliveries + retry
**Тип**: backend · **Оценка**: M (~5 ч) · **Зависимости**: T-121
- `GET /api/webhooks` — список подписок заведения
- `POST /api/webhooks` — создать (min 16 символов secret, max 10 подписок на venue)
- `GET /api/webhooks/{id}` — деталь (secret маскируется `mask_secret()`)
- `PUT /api/webhooks/{id}` — обновить
- `DELETE /api/webhooks/{id}` — удалить
- `GET /api/webhooks/{id}/deliveries` — история доставок (пагинация, per_page ≤ 100)
- `POST /api/webhooks/{id}/deliveries/{d_id}/retry` — ручной повтор (409 если status=retrying)
- `POST /api/webhooks/{id}/test` — тестовая отправка (синхронно, таймаут 10 с, SSRF-валидация)
- Хелпер `_get_subscription_or_404(db, sub_id, venue_id)` — tenant isolation (404 при несовпадении)
- **AC**: CRUD работает, tenant isolation не позволяет видеть чужие вебхуки

### T-123: ⬜ Интеграция emit() в orders/bookings/tobaccos (5 событий)
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-122, T-050
- `orders.py`: emit `order.served` и `order.cancelled` (cancelled включает `items[]` для ERP)
- `bookings.py`: emit `booking.completed` и `booking.cancelled`
- `tobaccos.py`: emit `tobacco.low_stock` при обновлении stock ниже threshold (debounce 4 ч через `last_low_stock_notified_at`)
- Все emit через `BackgroundTasks` (не блокируют ответ)
- Payload версия `"version": "1"` во всех событиях
- **AC**: Смена статуса заказа триггерит доставку вебхука в БД

### T-124: ⬜ Frontend: Webhooks.tsx, WebhookForm.tsx, WebhookDeliveries.tsx
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-122
- `Webhooks.tsx` — страница `/admin/webhooks`: таблица подписок, кнопки Test/History/Edit/Delete
- `WebhookForm.tsx` — модальная форма create/edit: URL, secret (генератор), multi-select событий
- `WebhookDeliveries.tsx` — таблица истории с фильтром по статусу и кнопкой Retry
- Добавить ссылку `/admin/webhooks` в `AdminLayout.tsx`
- **AC**: Администратор создаёт вебхук, проверяет тестовой отправкой, видит историю

---

## Граф зависимостей Фазы 3

```
T-080 (Phase 2) ──► T-100 ──► T-101 ──► T-102
                         └──────────► T-103
T-053, T-063 ───────────────────────► T-104 (RepeatOrderButton)
T-101, T-103 ───────────────────────► T-105

T-080 (Phase 2) ──► T-110 ──► T-111 ──► T-112 ──► T-113
T-070 (Phase 2) ────────────► T-111

T-031 (Phase 1) ──► T-120 ──► T-121 ──► T-122 ──► T-123
T-050 (Phase 2) ────────────────────────────────► T-123
                                        T-122 ──► T-124
```

---

## Порядок реализации Фазы 3

```
T-100 → T-101 → T-102 → T-103 (история backend)    [Sprint 1 начало]
T-104 → T-105 (история frontend)

T-110 → T-111 → T-112 → T-113 (уведомления)        [Sprint 1 конец]

T-120 → T-121 → T-122 (вебхуки backend)             [Sprint 2]
T-123 (интеграция событий)
T-124 (вебхуки frontend)
```

**Итого: 15 тикетов для Фазы 3**

---

## Критерии готовности Фазы 3

- [ ] Авторизованный гость видит историю заказов
- [ ] Гость может повторить прошлый заказ в один клик
- [ ] Работают избранные миксы (создание, повтор, лимит 5)
- [ ] Telegram-уведомления отправляются при смене статуса брони/заказа
- [ ] Web Push уведомления работают в браузере (HTTPS)
- [ ] Напоминание о брони отправляется за 2 часа
- [ ] Внешняя система может подписаться на вебхуки и получать события
- [ ] Вебхуки подписаны HMAC-SHA256, получатель может верифицировать
- [ ] SSRF-атаки через вебхук URL блокируются

---

## Сводная статистика всех фаз

| Фаза | Тикетов | Спек | Статус |
|------|---------|------|--------|
| Фаза 1 | 20 | — | ✅ 100% завершено |
| Фаза 2 | 29 | 5 спек | ⬜ Не начата |
| Фаза 3 | 15 | 3 спеки | ⬜ Не начата |
| **Итого** | **64** | **8 спек** | |
