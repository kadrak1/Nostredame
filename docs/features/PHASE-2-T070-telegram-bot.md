# Feature: Telegram-бот

**Phase**: 2
**PRD Requirement**: R6
**Status**: Planned
**Dependencies**: T-050 (hookah preorder), T-080 (guest auth)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

Telegram-бот предоставляет альтернативный канал для бронирования столов и заказа кальянов. Гость использует бота через привычный мессенджер: диалоги с кнопками вместо форм. Бот работает на long polling, использует `python-telegram-bot v20+` (async) и обращается к backend API через HTTP — так бизнес-логика не дублируется.

Скелет директорий `backend/bot/handlers/` и `backend/bot/keyboards/` уже создан.

## 2. User Stories

- **US-070-1**: Как гость, я хочу забронировать стол через Telegram, чтобы не заходить на сайт.
- **US-070-2**: Как гость, я хочу заказать кальян через Telegram, указав номер стола, чтобы не заходить на сайт.
- **US-070-3**: Как гость, я хочу получить подтверждение брони и уведомление о готовности кальяна в Telegram.
- **US-070-4**: Как гость, я хочу отменить бронирование через бот.
- **US-070-5**: Как гость, я хочу узнать статус своего заказа через бот.

## 3. Functional Requirements / Функциональные требования

### 3.1 Команды бота
- FR-070-01: `/start` — приветствие + главное меню (кнопки: 📅 Забронировать, 🌿 Заказать кальян, 📋 Мои брони)
- FR-070-02: `/book` — запуск ConversationHandler бронирования
- FR-070-03: `/order` — запуск ConversationHandler заказа (гость вводит номер стола вручную)
- FR-070-04: `/status` — статус последнего активного заказа/брони
- FR-070-05: `/cancel` — отмена активного заказа/брони (с подтверждением)
- FR-070-06: `/help` — список команд

### 3.2 ConversationHandler: Бронирование
- FR-070-08: Шаг 1 — Дата: показать inline keyboard с ближайшими 7 днями
- FR-070-09: Шаг 2 — Время: показать inline keyboard с доступными слотами (через `GET /api/bookings/available-tables`)
- FR-070-10: Шаг 3 — Гости: ввод числа от 1 до 20
- FR-070-11: Шаг 4 — Стол: inline keyboard со свободными столами (`[Стол №3 (4 чел.)]`, `[Стол №7 (2 чел.)]`)
- FR-070-12: Шаг 5 — Имя: ввод текстом
- FR-070-13: Шаг 6 — Телефон: ввод текстом с валидацией
- FR-070-14: Шаг 7 — Подтверждение: сводка + кнопки "✅ Подтвердить" / "❌ Отменить"
- FR-070-15: После создания брони — сообщение с ID брони и кнопкой "🌿 Добавить кальян"

### 3.3 ConversationHandler: Заказ кальяна
- FR-070-16: Шаг 1 — Стол: ввод номера стола текстом; проверка через `GET /api/tables/{id}`
- FR-070-17: Шаг 2 — Крепость: 3 inline кнопки (🌿 Лёгкий / 🔥 Средний / 💪 Крепкий)
- FR-070-18: Шаг 3 — Табаки: постраничный список табаков (по 5 на страницу) с кнопками `[✓ Выбрать]`
- FR-070-19: Шаг 4 — Выбрано X табаков: кнопки "Добавить ещё" / "Готово"
- FR-070-20: Шаг 5 — Комментарий: ввод текстом или кнопка "Пропустить"
- FR-070-21: Шаг 6 — Подтверждение: сводка (стол + состав) + "✅ Заказать"
- FR-070-22: После создания заказа — сообщение со статусом и обещанием уведомления при готовности

### 3.4 Уведомления
- FR-070-25: При подтверждении брони — уведомление гостю в Telegram (если известен telegram_id)
- FR-070-26: При отклонении брони — уведомление с причиной
- FR-070-27: При смене статуса заказа на "served" — уведомление "Ваш кальян готов! 🌿"
- FR-070-28: Уведомления отправляются через `bot.send_message(chat_id=telegram_id, ...)` из backend-сервиса

### 3.5 Аутентификация гостя в боте
- FR-070-29: При первом контакте с ботом — `telegram_id` из `update.effective_user.id` используется для идентификации
- FR-070-30: Перед шагом "Телефон" в бронировании — проверить, есть ли гость с таким `telegram_id` в БД
- FR-070-31: Если найден — предложить использовать сохранённый телефон

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-070-01: Long polling (не webhook) для RPi5 — нет нужды открывать порты
- NFR-070-02: Бот запускается как отдельный процесс или Docker-сервис
- NFR-070-03: Таймаут ConversationHandler: 5 минут без ответа → /cancel
- NFR-070-04: Rate limit на стороне backend защищает от спама через бот
- NFR-070-05: Все тексты бота вынесены в `backend/bot/messages.py` для удобной локализации
- NFR-070-06: При падении бота — автоматический перезапуск (`restart: unless-stopped` в docker-compose)

## 5. Database Changes / Изменения в БД

### 5.1 Расширение Guest
```python
# backend/app/models/guest.py — добавить поле (если не было):
telegram_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True, index=True)
telegram_username: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Примечание: `telegram_id` уже объявлен в модели `Guest` (по описанию T-030). Нужно проверить наличие индекса.

### 5.2 Миграции
- Alembic: добавить `telegram_username` если отсутствует; добавить индекс на `telegram_id`

## 6. API Endpoints (используются ботом)

Бот использует существующие и новые API endpoints через HTTP-клиент. Новых endpoints только для бота не создаётся.

| Endpoint | Когда используется |
|----------|-------------------|
| `GET /api/bookings/available-tables?date=...&time_from=...&time_to=...&guests=...` | Шаг 4 бронирования |
| `POST /api/bookings` | Создание брони |
| `GET /api/bookings/{id}` | Статус брони |
| `PUT /api/bookings/{id}/cancel` | Отмена брони |
| `POST /api/bookings/{id}/orders` | Предзаказ кальяна |
| `POST /api/orders` | Заказ за столом |
| `GET /api/orders/{public_id}/status` | Статус заказа |
| `GET /api/tobaccos?in_stock=true&strength_min=X&strength_max=Y` | Список табаков по крепости |
| `GET /api/tables/{id}` | Проверка существования стола при вводе номера |

## 7. Структура файлов бота

### 7.1 `backend/bot/main.py`
```python
# Application setup, long polling
# Регистрация handlers
# Запуск: app.run_polling()
```

### 7.2 `backend/bot/api_client.py`
```python
# Async HTTP-клиент (httpx) к backend API
# Базовый URL из config (BACKEND_BASE_URL)
# Методы: create_booking(), get_available_tables(), create_order(), etc.
```

### 7.3 `backend/bot/handlers/start.py`
- `/start` команда
- Главное меню с inline keyboard

### 7.4 `backend/bot/handlers/booking.py`
- `ConversationHandler` для бронирования (7 шагов)
- States: DATE, TIME, GUESTS, TABLE, NAME, PHONE, CONFIRM

### 7.5 `backend/bot/handlers/order.py`
- `ConversationHandler` для заказа кальяна
- States: TABLE_INPUT, STRENGTH, TOBACCOS, COMMENT, CONFIRM
- Шаг 0: гость вводит номер стола вручную

### 7.6 `backend/bot/handlers/status.py`
- `/status` — последний активный заказ/бронь
- `/cancel` — отмена с подтверждением

### 7.7 `backend/bot/keyboards/booking.py`
- `dates_keyboard(days=7)` — inline keyboard с датами
- `tables_keyboard(tables)` — inline keyboard со столами
- `confirm_keyboard()` — кнопки Подтвердить / Отменить

### 7.8 `backend/bot/keyboards/order.py`
- `strength_keyboard()` — 3 кнопки крепости
- `tobaccos_keyboard(tobaccos, page, selected_ids)` — постраничный список
- `done_keyboard()` — кнопки Добавить ещё / Готово

### 7.9 `backend/bot/messages.py`
```python
# Все текстовые сообщения бота — константы или функции
# Пример:
WELCOME = "Привет! Я помогу вам забронировать стол и заказать кальян. 🌿"
BOOKING_DATE = "Выберите дату:"
ORDER_READY = "Ваш кальян готов! Приятного отдыха 🌿"
```

### 7.10 `backend/bot/notifications.py`
```python
# Async функции для отправки уведомлений
# send_booking_confirmed(telegram_id, booking_id)
# send_order_ready(telegram_id, table_number)
# Используются из backend services при смене статуса
```

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/bot/main.py` | Новый файл — точка запуска |
| `backend/bot/api_client.py` | Новый файл — HTTP-клиент |
| `backend/bot/handlers/start.py` | Новый файл |
| `backend/bot/handlers/booking.py` | Новый файл |
| `backend/bot/handlers/order.py` | Новый файл |
| `backend/bot/handlers/status.py` | Новый файл |
| `backend/bot/keyboards/booking.py` | Новый файл |
| `backend/bot/keyboards/order.py` | Новый файл |
| `backend/bot/messages.py` | Новый файл |
| `backend/bot/notifications.py` | Новый файл |
| `docker-compose.yml` | Новый сервис `bot` |
| `backend/requirements.txt` | Добавить `python-telegram-bot>=20.0`, `httpx` |
| `backend/app/config.py` | `TELEGRAM_BOT_TOKEN` уже есть, добавить `BOT_USERNAME` |
| `backend/app/models/guest.py` | Проверить/добавить `telegram_username` |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: `/start` открывает главное меню с 3 кнопками
- [ ] AC-2: `/book` запускает ConversationHandler, бронь создаётся через API
- [ ] AC-3: `/order` предлагает ввести номер стола, заказ создаётся с `source=telegram`
- [ ] AC-4: При подтверждении брони — гость получает уведомление в Telegram
- [ ] AC-5: При готовности кальяна — гость получает уведомление "Ваш кальян готов!"
- [ ] AC-6: Таймаут диалога 5 мин → `/cancel` срабатывает
- [ ] AC-7: `/cancel` с подтверждением отменяет активную бронь через API
- [ ] AC-8: Бот автоматически перезапускается при падении (`restart: unless-stopped`)
- [ ] AC-9: Все тексты вынесены в `messages.py`

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-070 | Bot skeleton: main.py, api_client.py, messages.py, docker-compose сервис | backend | T-080 | M |
| T-071 | /start handler + главное меню | backend | T-070 | S |
| T-072 | Booking ConversationHandler (7 шагов) + keyboards | backend | T-070, T-071 | L |
| T-073 | Order ConversationHandler (5 шагов) + keyboards | backend | T-070, T-071 | L |
| T-074 | /status + /cancel handlers | backend | T-072, T-073 | S |
| T-075 | notifications.py — уведомления при смене статуса | backend | T-070 | M |
| T-076 | Интеграция notifications в booking/order status changes | backend | T-075 | M |
| T-077 | Guest model: telegram_username, индекс telegram_id | backend | T-030 | S |
| T-078 | E2E тесты бота (mock API + mock Telegram) | backend | T-070..T-076 | M |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Кто отвечает |
|---|--------|--------------|
| 1 | Нужен ли webhook вместо long polling при большой нагрузке? (для RPi5 рекомендую long polling) | DevOps |
| 2 | Формат нумерации слотов времени в боте (08:00, 08:30, ... или только целые часы)? | Владелец |
| 3 | Нужно ли хранить историю диалогов бота в БД? | Владелец |
| 4 | Язык бота — только русский или с выбором? | Владелец |
| 5 | ✅ **Решено**: QR deep link в боте (`/start table_3`) убран. Заказ через QR-код идёт только через веб. Бот принимает заказы через `/order` с ручным вводом номера стола. | |
