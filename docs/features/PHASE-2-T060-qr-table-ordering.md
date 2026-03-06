# Feature: Заказ кальяна за столом через QR-код

**Phase**: 2
**PRD Requirement**: R4
**Status**: Planned
**Dependencies**: T-050 (HookahBuilder), T-013 (Tables API)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

На каждом столе кальянной размещён QR-код. Гость сканирует его камерой телефона и попадает на страницу заказа кальяна — без скачивания приложения, без регистрации. Это основной сценарий заказа кальяна "на месте", когда гость уже сидит за столом.

QR-код ведёт на URL `https://domain.com/table/{table_id}`. На лендинге гость выбирает канал заказа (веб или Telegram) и далее проходит через конструктор кальяна (HookahBuilder из T-050).

## 2. User Stories

- **US-060-1**: Как гость за столом, я хочу отсканировать QR-код и заказать кальян через телефон, чтобы не ждать кальянщика.
- **US-060-2**: Как гость, я хочу выбрать между веб-интерфейсом и Telegram-ботом для заказа.
- **US-060-3**: Как гость, я хочу видеть статус моего заказа в реальном времени (принят → готовится → подан).
- **US-060-4**: Как админ, я хочу генерировать и скачивать QR-коды для столов, чтобы разместить их в зале.
- **US-060-5**: Как кальянщик, я хочу видеть заказы с номером стола, чтобы знать куда нести кальян.

## 3. Functional Requirements / Функциональные требования

### 3.1 QR-код
- FR-060-01: Каждый активный стол имеет уникальный QR-код, ведущий на `https://{domain}/table/{table_id}`
- FR-060-02: Админ может сгенерировать QR-коды через API (`GET /api/tables/{id}/qr`)
- FR-060-03: QR-код содержит логотип заведения (по центру, опционально)
- FR-060-04: Формат QR — PNG, размер для печати: 5x5 см (300 DPI)
- FR-060-05: Массовая генерация: `GET /api/tables/qr-all` — ZIP-архив со всеми QR-кодами

### 3.2 Лендинг стола
- FR-060-06: Страница `/table/{table_id}` показывает: название заведения, номер стола, 2 кнопки выбора канала
- FR-060-07: Кнопка "Заказать через сайт" → переход к `HookahBuilder`
- FR-060-08: Кнопка "Заказать через Telegram" → deep link `t.me/{bot_username}?start=table_{table_id}`
- FR-060-09: Если стол не найден или неактивен — страница ошибки "Стол не найден"
- FR-060-10: Для авторизованных гостей (T-080) — показать блок "Ваш последний кальян" (слот для T-100)

### 3.3 Заказ через веб
- FR-060-11: Переиспользовать компонент `HookahBuilder` из T-050
- FR-060-12: При подтверждении заказа — `POST /api/orders` с `table_id`, `source=qr_table`
- FR-060-13: После создания заказа — перенаправление на страницу статуса
- FR-060-14: Гость может оставить имя (опционально) для идентификации заказа

### 3.4 Статус заказа (реальное время)
- FR-060-15: Страница `/orders/{order_id}/status` показывает текущий статус
- FR-060-16: Статусы отображаются как прогресс-бар: Создан → Принят → Готовится → Подан
- FR-060-17: Обновление статуса через WebSocket (`WS /ws/orders/{order_id}`)
- FR-060-18: Fallback на polling (GET каждые 10 сек) если WebSocket недоступен
- FR-060-19: Уведомление (вибрация/звук) при смене статуса на "Подан"

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-060-01: Лендинг стола загружается < 2 сек на 3G
- NFR-060-02: QR-генерация < 500мс на запрос
- NFR-060-03: WebSocket подключение — max 100 одновременных соединений (RPi5 ограничение)
- NFR-060-04: Rate limit: 5 заказов/час с одного IP (защита от спама)
- NFR-060-05: Страница статуса не требует авторизации (доступ по order_id — UUID)

## 5. Database Changes / Изменения в БД

### 5.1 Расширение HookahOrder
Если не добавлено в T-050:
```python
# Добавить поле guest_name для идентификации анонимного заказа
guest_name: Mapped[str | None] = mapped_column(Text, nullable=True)
# Добавить UUID для публичного доступа к статусу
public_id: Mapped[str] = mapped_column(Text, unique=True, index=True)
```

### 5.2 Миграции
- Alembic: добавить `guest_name`, `public_id` в `hookah_orders`

## 6. API Endpoints

### 6.1 Создание заказа за столом
- **Method**: `POST`
- **URL**: `/api/orders`
- **Auth**: public
- **Rate limit**: 5/час на IP
- **Request**:
```json
{
  "table_id": 3,
  "guest_name": "Алексей",
  "strength": 3,
  "notes": "Побольше дыма",
  "items": [
    {"tobacco_id": 1, "weight_grams": 15.0},
    {"tobacco_id": 5, "weight_grams": 10.0}
  ]
}
```
- **Response** (201):
```json
{
  "id": 42,
  "public_id": "a1b2c3d4-e5f6-7890",
  "table_id": 3,
  "status": "pending",
  "source": "qr_table",
  "status_url": "/orders/a1b2c3d4-e5f6-7890/status",
  "created_at": "2026-03-06T19:00:00"
}
```
- **Errors**: `404` — стол не найден, `400` — табак не в наличии, `429` — rate limit

### 6.2 Статус заказа
- **Method**: `GET`
- **URL**: `/api/orders/{public_id}/status`
- **Auth**: public (доступ по UUID)
- **Response** (200):
```json
{
  "public_id": "a1b2c3d4-e5f6-7890",
  "status": "preparing",
  "table_number": 3,
  "strength": 3,
  "items": [
    {"tobacco_name": "Al Fakher Мята", "weight_grams": 15.0}
  ],
  "created_at": "2026-03-06T19:00:00",
  "updated_at": "2026-03-06T19:05:00"
}
```

### 6.3 WebSocket статуса
- **URL**: `WS /ws/orders/{public_id}`
- **Сообщения**: JSON `{"status": "preparing", "updated_at": "..."}`
- **Закрытие**: после статуса `served` или `cancelled`

### 6.4 Генерация QR-кода (админ)
- **Method**: `GET`
- **URL**: `/api/tables/{id}/qr`
- **Auth**: admin
- **Query params**: `size=300` (пиксели)
- **Response**: PNG image (`Content-Type: image/png`)

### 6.5 Массовая генерация QR (админ)
- **Method**: `GET`
- **URL**: `/api/tables/qr-all`
- **Auth**: admin
- **Response**: ZIP-архив с QR-кодами (`table_1.png`, `table_2.png`, ...)

## 7. Frontend Components / Компоненты

### 7.1 `TableLanding`
- **Путь**: `frontend/src/pages/TableLanding.tsx`
- **Route**: `/table/:tableId`
- **Содержание**: название заведения, номер стола, 2 кнопки (веб/Telegram)
- **Стиль**: тёмная тема, mobile-first, крупные кнопки

### 7.2 `TableOrder`
- **Путь**: `frontend/src/pages/TableOrder.tsx`
- **Route**: `/table/:tableId/order`
- **Содержание**: обёртка над `HookahBuilder` с дополнительным полем "Ваше имя" и `POST /api/orders`
- **Props HookahBuilder**: `tableId`, `onSubmit`, `repeatSlot` (для T-100)

### 7.3 `OrderStatus`
- **Путь**: `frontend/src/pages/OrderStatus.tsx`
- **Route**: `/orders/:publicId/status`
- **Содержание**: прогресс-бар (4 шага), детали заказа, WebSocket-обновления
- **Анимация**: плавный переход между статусами

### 7.4 Админ: QR-генератор
- **Путь**: `frontend/src/pages/admin/QRCodes.tsx`
- **Route**: `/admin/qr-codes`
- **Содержание**: список столов + кнопка "Скачать QR" для каждого + "Скачать все"

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/app/routers/orders.py` | Новый файл — `POST /api/orders`, `GET /api/orders/{id}/status` |
| `backend/app/routers/tables.py` | Добавить `GET /api/tables/{id}/qr`, `GET /api/tables/qr-all` |
| `backend/app/main.py` | Регистрация WebSocket endpoint `/ws/orders/{public_id}` |
| `backend/app/services/ws_manager.py` | Новый файл — WebSocket connection manager |
| `backend/app/services/qr_generator.py` | Новый файл — генерация QR-кодов (библиотека: `qrcode`) |
| `frontend/src/App.tsx` | Новые маршруты: `/table/:id`, `/table/:id/order`, `/orders/:id/status` |
| `frontend/src/pages/TableLanding.tsx` | Новый файл |
| `frontend/src/pages/TableOrder.tsx` | Новый файл |
| `frontend/src/pages/OrderStatus.tsx` | Новый файл |
| `frontend/src/pages/admin/QRCodes.tsx` | Новый файл |
| `backend/requirements.txt` | Добавить `qrcode[pil]`, `websockets` |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: QR-код для стола генерируется и сканируется камерой → ведёт на `/table/{id}`
- [ ] AC-2: Лендинг показывает номер стола и 2 кнопки
- [ ] AC-3: Кнопка "Через сайт" открывает HookahBuilder
- [ ] AC-4: Кнопка "Через Telegram" ведёт на deep link бота
- [ ] AC-5: Заказ через `POST /api/orders` создаётся с `source=qr_table`
- [ ] AC-6: Страница статуса показывает прогресс-бар и обновляется в реальном времени
- [ ] AC-7: WebSocket отправляет обновления при смене статуса
- [ ] AC-8: Несуществующий стол → страница ошибки 404
- [ ] AC-9: Rate limit работает (6-й заказ за час отклоняется)
- [ ] AC-10: Админ может скачать QR-коды для всех столов одним ZIP-файлом
- [ ] AC-11: Mobile-first — лендинг и статус корректно отображаются на 320px+

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-060 | QR-генератор: сервис + API endpoint + массовая генерация | backend | T-013 | M |
| T-061 | Orders API: POST /api/orders + public_id + rate limit | backend | T-050, T-051 | M |
| T-062 | WebSocket manager + WS /ws/orders/{public_id} | backend | T-061 | L |
| T-063 | TableLanding + TableOrder страницы (с HookahBuilder) | frontend | T-053, T-061 | M |
| T-064 | OrderStatus страница (прогресс-бар, WebSocket) | frontend | T-062 | M |
| T-065 | Админ QR-страница + маршруты | frontend | T-060 | S |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Кто отвечает |
|---|--------|--------------|
| 1 | Нужен ли логотип на QR-коде? (усложняет генерацию) | Владелец |
| 2 | Показывать ли меню еды/напитков на лендинге? (out of scope MVP) | Владелец |
| 3 | Ограничение по количеству одновременных WebSocket соединений? (предлагаю 100) | DevOps |
| 4 | Использовать UUID4 для public_id или короткий ID (nanoid 8 символов)? | Команда |
