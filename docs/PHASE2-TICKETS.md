# Фаза 2 — Декомпозиция на инженерные тикеты

**Scope**: Предзаказ кальяна · Заказ по QR · Telegram-бот · Гостевая авторизация · Панель кальянщика

---

## Статус прогресса (обновлено: 2026-03-07)

| Тикет | Название | Тип | Оценка | Статус | Спека |
|-------|----------|-----|--------|--------|-------|
| T-050 | Enum OrderSource + поле source в HookahOrder + миграция | backend | S | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-051 | Pydantic-схемы заказа (OrderCreate, OrderPublic, OrderItem) | backend | S | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-052 | API: POST/GET /api/bookings/{id}/orders + фильтры tobaccos | backend | M | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-053 | Компонент HookahBuilder (StrengthSelector 1-10, TobaccoSelector, MasterRecommendations, OrderPreview) | frontend | L | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-054 | Интеграция HookahBuilder в Booking.tsx + экран успеха | frontend | M | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-055 | MasterRecommendation модель + миграция + CRUD API + публичный GET | backend | M | ⬜ Не начат | [T-050](features/PHASE-2-T050-hookah-preorder.md) |
| T-060 | QR-генератор: сервис + API endpoint + массовая генерация | backend | M | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-061 | Orders API: POST /api/orders + public_id + rate limit | backend | M | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-062 | WebSocket manager + WS /ws/orders/{public_id} | backend | L | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-063 | TableLanding + TableOrder страницы (с HookahBuilder) | frontend | M | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-064 | OrderStatus страница (прогресс-бар, WebSocket) | frontend | M | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-065 | Админ QR-страница + маршруты | frontend | S | ⬜ Не начат | [T-060](features/PHASE-2-T060-qr-table-ordering.md) |
| T-070 | Bot skeleton: main.py, api_client.py, messages.py, docker-compose сервис | backend | M | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-071 | /start handler + главное меню | backend | S | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-072 | Booking ConversationHandler (7 шагов) + keyboards | backend | L | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-073 | Order ConversationHandler (5 шагов) + keyboards | backend | L | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-074 | /status + /cancel handlers | backend | S | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-075 | notifications.py — уведомления при смене статуса | backend | M | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-076 | Интеграция notifications в booking/order status changes | backend | M | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-077 | Guest model: telegram_username, индекс telegram_id | backend | S | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-078 | E2E тесты бота (mock API + mock Telegram) | backend | M | ⬜ Не начат | [T-070](features/PHASE-2-T070-telegram-bot.md) |
| T-080 | Расширение Guest модели + миграция (last_login_at, login_count) | backend | S | ⬜ Не начат | [T-080](features/PHASE-2-T080-guest-auth.md) |
| T-081 | Guest auth API: POST /api/auth/guest + JWT + cookies | backend | M | ⬜ Не начат | [T-080](features/PHASE-2-T080-guest-auth.md) |
| T-082 | Guest profile API: GET/PUT /api/guest/me + dependencies | backend | S | ⬜ Не начат | [T-080](features/PHASE-2-T080-guest-auth.md) |
| T-083 | PhoneLogin компонент + GuestAuthProvider + интеграция Booking | frontend | M | ⬜ Не начат | [T-080](features/PHASE-2-T080-guest-auth.md) |
| T-090 | Master API: GET /api/master/orders + PUT status + зависимость hookah_master | backend | M | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |
| T-091 | WS /ws/master/orders + ws_manager расширение | backend | M | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |
| T-092 | MasterLayout + маршруты + auth guard | frontend | S | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |
| T-093 | OrderQueue страница + OrderCard компонент + WebSocket | frontend | L | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |
| T-094 | OrderHistory страница + звуковые уведомления (useOrderNotification) | frontend | M | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |
| T-095 | Recommendations страница + RecommendationForm в панели кальянщика | frontend | M | ⬜ Не начат | [T-090](features/PHASE-2-T090-hookah-master-panel.md) |

**Прогресс**: 0 / 31 тикета завершено (0%)

---


## Эпик 5: Предзаказ кальяна при бронировании

> **Спека**: [PHASE-2-T050-hookah-preorder.md](features/PHASE-2-T050-hookah-preorder.md)
> **PRD**: R3 — Предзаказ кальяна

Гость в процессе бронирования стола может дополнительно сделать предзаказ кальяна: выбрать крепость, табаки из каталога и добавить комментарий. Менеджер видит предзаказ вместе с бронированием.

### T-050: ⬜ Enum OrderSource + поле source в HookahOrder + миграция
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-030
- Добавить enum `OrderSource` (`booking_preorder`, `qr_table`, `telegram`) в `models/enums.py`
- Добавить поле `source: Mapped[OrderSource]` в модель `HookahOrder`
- Написать и применить Alembic миграцию
- **AC**: `source` присутствует в БД, `alembic upgrade head` проходит без ошибок

### T-051: ⬜ Pydantic-схемы заказа
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-050
- `OrderItemCreate`, `OrderItemPublic` — позиция заказа (tobacco_id, weight_grams, comment)
- `OrderCreate` — создание заказа (booking_id?, table_id?, items[], guest_note, source)
- `OrderPublic` — ответ гостю (id, status, items, created_at)
- `OrderAdmin` — ответ для админа (расширенный, с guest info)
- **AC**: Схемы валидируют входные данные, некорректные tobacco_id отклоняются

### T-052: ⬜ API предзаказа + фильтры табаков
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-051, T-031
- `POST /api/bookings/{id}/orders` — создать предзаказ при бронировании
- `GET /api/bookings/{id}/orders` — список предзаказов по брони
- `GET /api/tobaccos?in_stock=true&strength=X` — фильтрация для HookahBuilder
- Проверка: booking принадлежит текущему гостю или публичный (guest_phone)
- **AC**: Предзаказ создаётся и привязывается к брони, появляется в ответе `/api/admin/bookings`

### T-053: ⬜ Компонент HookahBuilder
**Тип**: frontend · **Оценка**: L (~8 ч) · **Зависимости**: T-052, T-055
- `StrengthSelector.tsx` — переключатель крепости: «Лёгкий» (1-4) / «Средний» (5-7) / «Крепкий» (8-10), маппинг на шкалу 1-10
- `MasterRecommendations.tsx` — блок «Рекомендует кальянщик»: активные рекомендации для выбранного strength_level (из GET /api/master/recommendations), кнопка «Выбрать этот микс» предзаполняет TobaccoSelector
- `TobaccoSelector.tsx` — список с поиском и фильтром, чекбоксы, вес по умолчанию 20г (слайдер 5-40г)
- `OrderPreview.tsx` — итоговый список выбранных табаков
- `HookahBuilder.tsx` — контейнер, управление состоянием, отправка в API
- Props: `bookingId`, `onComplete`, `onSkip`
- Слот для `RepeatOrderButton` (авторизованный гость — T-100)
- **AC**: Гость может выбрать крепость, просмотреть рекомендации кальянщика, выбрать 1-3 табака (вес по умолчанию 20г), отправить заказ

### T-054: ⬜ Интеграция HookahBuilder в Booking.tsx
**Тип**: frontend · **Оценка**: M (~4 ч) · **Зависимости**: T-053
- После успешного бронирования — опциональный Шаг 6 "Добавить кальян"
- Кнопка "Пропустить" возвращает на экран подтверждения
- Экран успеха обновить: показывать детали предзаказа если он был сделан
- **AC**: Флоу бронирования с кальяном работает сквозь 6 шагов

### T-055: ⬜ MasterRecommendation модель + CRUD API + публичный GET
**Тип**: backend · **Оценка**: M (~5 ч) · **Зависимости**: T-031, T-004
- Модель `MasterRecommendation` в `backend/app/models/master_recommendation.py`:
  - Поля: `id`, `venue_id` (FK venues), `name` (String(100)), `strength_level` (String(10): `"light"` | `"medium"` | `"strong"`), `items` (JSON: `[{tobacco_id, weight_grams}]`), `is_active` (bool, default True), `created_by` (FK users), `created_at`
  - Маппинг strength_level: `"light"` → 1-4, `"medium"` → 5-7, `"strong"` → 8-10
  - Ограничение: не более 10 активных рекомендаций на venue
- Миграция Alembic
- CRUD-эндпоинты (только `hookah_master | admin | owner`): `POST /api/master/recommendations`, `GET /api/master/recommendations`, `PUT /api/master/recommendations/{id}`, `DELETE /api/master/recommendations/{id}`
- Публичный эндпоинт: `GET /api/master/recommendations?strength_level=light|medium|strong` — для HookahBuilder
- **AC**: CRUD работает, публичный GET возвращает активные рекомендации для заданного strength_level

---

## Эпик 6: Заказ кальяна по QR-коду

> **Спека**: [PHASE-2-T060-qr-table-ordering.md](features/PHASE-2-T060-qr-table-ordering.md)
> **PRD**: R4 — Заказ за столом через QR

Гость сканирует QR-код на столе → видит лендинг с выбором канала (веб/Telegram) → собирает заказ через HookahBuilder → отслеживает статус в реальном времени через WebSocket.

### T-060: ⬜ QR-генератор: сервис + API endpoint
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-013
- Сервис `services/qr.py` — генерация QR PNG через `qrcode` (pil)
- `GET /api/tables/{id}/qr` — скачать PNG (только admin/owner)
- `GET /api/tables/qr/bulk.zip` — архив всех QR для зала
- URL в QR: `https://domain.com/table/{public_table_token}`
- `public_table_token` — UUIDv4, не раскрывающий числовой ID стола
- **AC**: QR-PNG скачивается, URL в нём ведёт на `/table/:token`

### T-061: ⬜ Orders API: POST /api/orders + public_id + rate limit
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-050, T-051
- `POST /api/orders` — создать заказ с привязкой к столу (по public_table_token)
- `GET /api/orders/{public_id}/status` — статус заказа (публичный)
- `public_id` — nanoid 8 символов для ссылки в статус-странице
- Rate limit: 3 заказа/мин на IP
- **AC**: Заказ создаётся, public_id возвращается, статус доступен без авторизации

### T-062: ⬜ WebSocket manager + WS /ws/orders/{public_id}
**Тип**: backend · **Оценка**: L (~8 ч) · **Зависимости**: T-061
- `services/ws_manager.py` — ConnectionManager (subscribe, broadcast, disconnect)
- `WS /ws/orders/{public_id}` — подписка гостя на обновления заказа
- `WS /ws/master/orders` — подписка кальянщика на новые заказы заведения
- Push при смене `OrderStatus` из orders.py
- **AC**: Браузер получает обновление через WS при смене статуса кальянщиком

### T-063: ⬜ TableLanding + TableOrder страницы
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-053, T-061
- `TableLanding.tsx` — route `/table/:token`: информация о столе, кнопки "Заказать в браузере" / "Открыть в Telegram"
- `TableOrder.tsx` — встраивает `HookahBuilder`, отправка заказа
- Слот для `RepeatOrderButton` (T-100)
- **AC**: Сканирование QR открывает лендинг, заказ создаётся

### T-064: ⬜ OrderStatus страница
**Тип**: frontend · **Оценка**: M (~4 ч) · **Зависимости**: T-062
- `OrderStatus.tsx` — route `/order/:public_id`
- Прогресс-бар: pending → accepted → preparing → served
- Обновление через WebSocket (fallback: polling каждые 5 с)
- **AC**: Статус обновляется в реальном времени без перезагрузки страницы

### T-065: ⬜ Админ QR-страница
**Тип**: frontend · **Оценка**: S (~3 ч) · **Зависимости**: T-060
- Страница `/admin/qr` — таблица столов, кнопка "Скачать QR" для каждого
- Кнопка "Скачать все (ZIP)"
- Превью QR в модальном окне
- **AC**: Администратор скачивает QR-коды для печати

---


## Эпик 7: Telegram-бот

> **Спека**: [PHASE-2-T070-telegram-bot.md](features/PHASE-2-T070-telegram-bot.md)
> **PRD**: R6 — Telegram-бот

Telegram-бот с ConversationHandler для бронирования и заказа кальяна. Заказ из бота — через ручной ввод номера стола (QR-код ведёт на веб, не в бот). Использует backend API через HTTP (не напрямую в БД).

### T-070: ⬜ Bot skeleton: main.py, api_client.py, docker-compose
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-080
- Структура: `backend/bot/handlers/`, `backend/bot/keyboards/`, `backend/bot/api_client.py`
- `api_client.py` — обёртка над httpx для backend API
- `messages.py` — шаблоны сообщений (русский текст)
- Добавить сервис `bot` в `docker-compose.yml`
- **AC**: Бот запускается, отвечает на `/start`

### T-071: ⬜ /start handler + главное меню
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-070
- `/start` — приветствие + главное меню (inline keyboard)
- `/help` — список команд
- **AC**: `/start` открывает меню с кнопками «Забронировать», «Заказать кальян», «Мои брони»

### T-072: ⬜ Booking ConversationHandler (7 шагов)
**Тип**: backend · **Оценка**: L (~8 ч) · **Зависимости**: T-070, T-071
- Шаги: дата → время → гостей → выбор стола → имя → телефон → подтверждение
- Inline keyboards: даты (на неделю вперёд), временные слоты, список доступных столов
- `PUT /api/bookings` через `api_client.py`
- Отмена в любой момент через /cancel
- **AC**: Гость бронирует стол через 7 шагов, получает ID брони

### T-073: ⬜ Order ConversationHandler (6 шагов)
**Тип**: backend · **Оценка**: L (~8 ч) · **Зависимости**: T-070, T-071
- Шаги: номер стола → крепость → табаки → вес → комментарий → подтверждение
- Валидация стола через `GET /api/tables/{id}`
- `POST /api/orders` через `api_client.py`
- **AC**: Гость создаёт заказ через 6 шагов, получает public_id

### T-074: ⬜ /status + /cancel handlers
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-072, T-073
- `/status` — список активных броней/заказов гостя с телефоном
- `/cancel {id}` — отмена брони через API
- **AC**: Гость видит статусы и может отменить бронь

### T-075: ⬜ notifications.py — уведомления при смене статуса
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-070
- `bot/notifications.py` — функции `notify_booking_status`, `notify_order_status`
- Отправка сообщения через Bot API (httpx) на `Guest.telegram_id`
- Обработка ошибок: 403 → устанавливать `Guest.telegram_blocked = True`
- **AC**: При подтверждении брони гость получает уведомление в Telegram

### T-076: ⬜ Интеграция notifications в status changes
**Тип**: backend · **Оценка**: M (~3 ч) · **Зависимости**: T-075
- Вызов `notify_booking_status()` в `PUT /api/admin/bookings/{id}/confirm|reject`
- Вызов `notify_order_status()` в `PUT /api/master/orders/{id}/accept|preparing|serve`
- Через `BackgroundTasks` с отдельной DB-сессией
- **AC**: При изменении статуса через API гость получает Telegram-уведомление

### T-077: ⬜ Guest model: telegram_username, индекс telegram_id
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-030
- Добавить `telegram_username: Mapped[str | None]` в модель `Guest`
- Добавить Index на `telegram_id` для быстрого поиска
- Механизм привязки: `/start phone_{phone_hash}` — бот ищет Guest по phone_hash, обновляет telegram_id
- Миграция Alembic
- **AC**: Индекс создан, привязка Telegram-аккаунта работает

### T-078: ⬜ E2E тесты бота
**Тип**: backend · **Оценка**: M (~5 ч) · **Зависимости**: T-070, T-071, T-072, T-073, T-074, T-075, T-076
- Mock Telegram Bot API (python-telegram-bot test helpers)
- Mock backend API через `respx`
- Тест BookingConversation: полный флоу 7 шагов
- Тест OrderConversation: полный флоу 6 шагов (с вводом номера стола)
- **AC**: pytest проходит без реального подключения к Telegram

---

## Эпик 8: Гостевая авторизация по телефону

> **Спека**: [PHASE-2-T080-guest-auth.md](features/PHASE-2-T080-guest-auth.md)
> **PRD**: R8 — Гостевая авторизация

Гость вводит номер телефона → система ищет или создаёт Guest по phone_hash → выдаёт гостевой JWT с ограниченными правами. Без SMS-OTP — максимально простой вход.

### T-080: ⬜ Расширение модели Guest + миграция
**Тип**: backend · **Оценка**: S (~2 ч) · **Зависимости**: T-030
- Добавить поля `last_login_at: Mapped[datetime | None]`, `login_count: Mapped[int]` (default 0)
- Добавить `telegram_blocked: Mapped[bool]` (default False) — флаг блокировки от T-077
- Написать и применить миграцию Alembic
- **AC**: Миграция проходит, поля доступны

### T-081: ⬜ Guest auth API: POST /api/auth/guest
**Тип**: backend · **Оценка**: M (~5 ч) · **Зависимости**: T-080, T-004
- `POST /api/auth/guest` — принимает `{ guest_phone }`, возвращает гостевой JWT + httpOnly cookie
- Логика: phone → phone_hash → поиск Guest → создать если не найден → обновить last_login_at
- Гостевой JWT: payload `{ sub: guest_id, role: "guest", venue_id }`, TTL 7 дней
- Rate limit: 5 попыток/мин с одного IP
- **AC**: POST с телефоном возвращает JWT, повторный вход находит того же Guest

### T-082: ⬜ Guest profile API: GET/PUT /api/guest/me
**Тип**: backend · **Оценка**: S (~3 ч) · **Зависимости**: T-081
- Dependency `get_current_guest()` в `dependencies.py` — проверяет гостевой JWT
- `GET /api/guest/me` — профиль гостя (без телефона в открытом виде)
- `PUT /api/guest/me` — обновление имени гостя
- **AC**: Авторизованный гость получает и обновляет профиль

### T-083: ⬜ PhoneLogin компонент + GuestAuthProvider
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-081
- `PhoneLogin.tsx` — одно поле ввода телефона + кнопка "Войти"
- `GuestAuthProvider.tsx` — React Context для гостевой сессии (хранение токена, текущий guest)
- Интеграция в `Booking.tsx`: кнопка "Войти" на шаге ввода данных
- После входа — имя гостя подставляется автоматически
- **AC**: Гость входит по телефону, имя отображается на шаге бронирования

---


## Эпик 9: Панель кальянщика

> **Спека**: [PHASE-2-T090-hookah-master-panel.md](features/PHASE-2-T090-hookah-master-panel.md)
> **PRD**: R10 — Панель кальянщика

Веб-панель для роли `hookah_master` — очередь заказов в реальном времени, управление статусами через кнопки, история смены.

### T-090: ⬜ Master API: GET /api/master/orders + PUT status
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-050, T-060
- `GET /api/master/orders` — активные заказы заведения (status != served/cancelled), только `hookah_master`
- `PUT /api/master/orders/{id}/accept` → `OrderStatus.accepted`
- `PUT /api/master/orders/{id}/preparing` → `OrderStatus.preparing`
- `PUT /api/master/orders/{id}/serve` → `OrderStatus.served`
- Dependency: `get_current_user` с проверкой роли `hookah_master | admin | owner`
- **AC**: Кальянщик меняет статус заказа, изменение сохраняется

### T-091: ⬜ WS /ws/master/orders + ws_manager расширение
**Тип**: backend · **Оценка**: M (~4 ч) · **Зависимости**: T-062, T-090
- `WS /ws/master/orders` — подписка кальянщика на новые заказы заведения (venue_id из JWT)
- Расширить `ws_manager.py` — группы подписок по `venue_id`
- Push событий: `order.new`, `order.updated` при смене статуса
- **AC**: При создании нового заказа кальянщик получает WS-уведомление без перезагрузки

### T-092: ⬜ MasterLayout + маршруты + auth guard
**Тип**: frontend · **Оценка**: S (~2 ч) · **Зависимости**: T-011
- `MasterLayout.tsx` — отдельный layout для панели кальянщика
- Маршруты `/master/*` в React Router
- Auth guard: только пользователи с ролью `hookah_master | admin | owner`
- **AC**: Попытка открыть `/master` без роли hookah_master → редирект на логин

### T-093: ⬜ OrderQueue страница + OrderCard + WebSocket
**Тип**: frontend · **Оценка**: L (~8 ч) · **Зависимости**: T-091, T-092
- `OrderQueue.tsx` — страница `/master/orders`, три колонки: Новые / В работе / Готово
- `OrderCard.tsx` — карточка заказа: стол, гость, состав кальяна, кнопки смены статуса
- WebSocket подключение через `useWebSocket` hook
- **AC**: Карточки появляются в реальном времени, кнопки меняют статус

### T-094: ⬜ OrderHistory страница + звуковые уведомления
**Тип**: frontend · **Оценка**: M (~4 ч) · **Зависимости**: T-092
- `OrderHistory.tsx` — страница `/master/history`, фильтр по дате
- `useOrderNotification` hook — звуковой сигнал при поступлении нового заказа (Web Audio API)
- Настройка: включить/отключить звук
- **AC**: При новом заказе звучит сигнал (если включён), история доступна за любую дату

### T-095: ⬜ Recommendations страница + RecommendationForm в панели кальянщика
**Тип**: frontend · **Оценка**: M (~5 ч) · **Зависимости**: T-055, T-092
- `Recommendations.tsx` — страница `/master/recommendations`, список карточек рекомендаций (имя, strength_level, состав)
- `RecommendationForm.tsx` — форма создания/редактирования рекомендации (имя, уровень крепости, список табаков с весом, переключатель is_active)
- Отображение предупреждения при достижении лимита 10 активных рекомендаций
- Маршрут `/master/recommendations` в MasterLayout
- **AC**: Кальянщик создаёт, редактирует и деактивирует рекомендации; изменения сразу отражаются в HookahBuilder гостей

---

## Граф зависимостей Фазы 2

```
T-030 (Phase 1) ──► T-080 ──► T-081 ──► T-082
                         └──────────────► T-083
                    └──► T-077

T-031 (Phase 1) ──► T-052
T-013 (Phase 1) ──► T-060 ──► T-065
T-020 (Phase 1)          \
T-021 (Phase 1)           └──────────────────────────┐
                                                       ▼
T-030 ──► T-050 ──► T-051 ──► T-052 ──► T-053 ──► T-054
                         └──► T-061 ──► T-062 ──► T-063
                                    └──────────► T-064

T-031 ──► T-055 ──────────────────────► T-053
                └──────────────────────► T-095

T-080 ──► T-070 ──► T-071 ──► T-072
                       ├──────────► T-073
                       └──────────► T-075 ──► T-076
T-030 ──────────────► T-077
T-070..T-076 ──────► T-078

T-050, T-060 ──► T-090 ──► (T-093)
T-062 ──────────► T-091 ──► T-093
T-011 ──────────► T-092 ──► T-093, T-094, T-095
T-055, T-092 ───────────► T-095
```

---

## Порядок реализации Фазы 2

```
T-080 (гость-модель)                             [Sprint 1 начало]
T-081 → T-082 → T-083 (гостевой вход)
T-050 → T-051 → T-052 (предзаказ backend)
T-055 (MasterRecommendation модель + API)
T-053 → T-054 (HookahBuilder + рекомендации)    [Sprint 1 конец]

T-060 → T-061 → T-062 (QR + заказы)             [Sprint 2 начало]
T-063 → T-064 → T-065 (QR фронтенд)
T-090 → T-091 → T-092 → T-093 → T-094
T-095 (Recommendations страница)                 [Sprint 2 конец]

T-077 → T-070 → T-071 (бот skeleton)            [Sprint 3 начало]
T-072 → T-073 → T-074 (бот handlers)
T-075 → T-076 → T-078 (notifications)           [Sprint 3 конец]
```

**Итого: 31 тикет для Фазы 2**

---

## Критерии готовности Фазы 2

- [ ] Гость может авторизоваться по номеру телефона
- [ ] При бронировании доступен опциональный предзаказ кальяна
- [ ] Гость может заказать кальян через QR-код на столе
- [ ] Статус заказа обновляется в реальном времени через WebSocket
- [ ] Telegram-бот позволяет бронировать и заказывать кальян
- [ ] Кальянщик видит очередь заказов и управляет статусами
- [ ] Кальянщик создаёт рекомендации миксов, гость видит их в HookahBuilder
- [ ] При смене статуса гость получает уведомление в Telegram
