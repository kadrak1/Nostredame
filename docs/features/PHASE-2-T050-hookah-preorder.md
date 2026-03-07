# Feature: Предзаказ кальяна при бронировании

**Phase**: 2
**PRD Requirement**: R3
**Status**: Planned
**Dependencies**: T-030 (Booking models), T-031 (Booking API), T-020 (Tobacco model)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

Сейчас при бронировании стола гость не может заранее выбрать кальян. Это приводит к задержке: после прихода гость ждёт, пока кальянщик подойдёт, обсудит предпочтения, приготовит кальян (5–10 мин). Предзаказ кальяна на этапе бронирования позволит кальянщику начать подготовку до прихода гостя и сократить ожидание до ~2 минут.

**Ключевой компонент**: `HookahBuilder` — переиспользуемый конструктор кальяна, который будет интегрирован в:
- Бронирование (этот тикет)
- QR-заказ за столом (T-060)
- Telegram-бот (T-070)

## 2. User Stories

- **US-050-1**: Как гость, я хочу выбрать кальян при бронировании стола, чтобы он был готов к моему приходу.
- **US-050-2**: Как гость, я хочу выбрать крепость кальяна (лёгкий/средний/крепкий), чтобы не разбираться в числовых значениях 1-10.
- **US-050-6**: Как гость, я хочу видеть готовые рекомендованные миксы от кальянщика для выбранной крепости, чтобы не подбирать табаки самостоятельно.
- **US-050-3**: Как гость, я хочу выбрать табаки из доступных, чтобы составить микс по вкусу.
- **US-050-4**: Как гость, я хочу оставить комментарий к заказу (например, "больше мяты"), чтобы кальянщик учёл мои предпочтения.
- **US-050-5**: Как кальянщик, я хочу видеть предзаказы кальянов привязанные к бронированиям, чтобы подготовить их заранее.

## 3. Functional Requirements / Функциональные требования

### 3.1 Конструктор кальяна (HookahBuilder)
- FR-050-01: Выбор уровня крепости через 3 кнопки: "Лёгкий" (1-4), "Средний" (5-7), "Крепкий" (8-10) — маппинг на strength 1-10
- FR-050-01a: При выборе уровня крепости — показать блок "Рекомендует кальянщик" с активными `MasterRecommendation` для данного `strength_level` (из `GET /api/master/recommendations?strength_level=X`). Кнопка "Выбрать этот микс" предзаполняет TobaccoSelector.
- FR-050-02: Фильтрация доступных табаков по выбранной крепости через `GET /api/tobaccos?in_stock=true&strength_min=X&strength_max=Y`
- FR-050-03: Выбор табаков (1-3 штуки) для микса — карточки с названием, брендом, вкусовым профилем
- FR-050-04: Указание веса каждого табака (по умолчанию 20г, range slider 5-40г)
- FR-050-05: Текстовое поле для комментария (до 200 символов)
- FR-050-06: Предпросмотр кальяна перед подтверждением (сводка: крепость, табаки, вес, комментарий)

### 3.2 Интеграция в бронирование
- FR-050-07: После успешного создания брони — экран "Бронь создана!" с кнопкой "Добавить кальян" (не обязательно)
- FR-050-08: При нажатии "Добавить кальян" — открывается HookahBuilder
- FR-050-09: После подтверждения кальяна — создаётся `HookahOrder` привязанный к `Booking`
- FR-050-10: Можно добавить несколько кальянов к одной брони (кнопка "Добавить ещё один")
- FR-050-11: Для авторизованных гостей (Phase 3, T-100) — предусмотреть слот для блока "Повторить последний кальян"

### 3.3 Источник заказа
- FR-050-12: Добавить enum `OrderSource` в `app/models/enums.py`: `booking_preorder`, `qr_table`, `telegram`
- FR-050-13: Добавить поле `source` в модель `HookahOrder`

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-050-01: HookahBuilder должен загружаться < 1 сек (каталог табаков кешируется React Query)
- NFR-050-02: Mobile-first — корректное отображение на экранах 320px+
- NFR-050-03: Компонент HookahBuilder полностью переиспользуем (без привязки к Booking)
- NFR-050-04: Rate limit на создание заказов: 10/час на IP

## 5. Database Changes / Изменения в БД

### 5.1 Новый enum `OrderSource`
```python
# app/models/enums.py
class OrderSource(str, enum.Enum):
    booking_preorder = "booking_preorder"
    qr_table = "qr_table"
    telegram = "telegram"
```

### 5.2 Расширение HookahOrder
```python
# app/models/order.py — добавить поле:
source: Mapped[OrderSource] = mapped_column(
    SAEnum(OrderSource), default=OrderSource.booking_preorder
)
```

### 5.3 Новая модель `MasterRecommendation`
```python
# app/models/master_recommendation.py
class MasterRecommendation(Base):
    __tablename__ = "master_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    venue_id: Mapped[int] = mapped_column(ForeignKey("venues.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))          # "Классика лёгкая"
    strength_level: Mapped[str] = mapped_column(String(10)) # "light"|"medium"|"strong"
    items: Mapped[dict] = mapped_column(JSON)                # [{tobacco_id, weight_grams}]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```
- `strength_level` маппинг: `"light"` → 1-4, `"medium"` → 5-7, `"strong"` → 8-10
- Ограничение: максимум 10 активных рекомендаций на заведение

### 5.4 Миграции
- Alembic миграция 1: добавить колонку `source` в `hookah_orders` (default='booking_preorder')
- Alembic миграция 2: создать таблицу `master_recommendations`

## 6. API Endpoints

### 6.1 Создание предзаказа кальяна к бронированию
- **Method**: `POST`
- **URL**: `/api/bookings/{booking_id}/orders`
- **Auth**: public (проверка guest_phone для верификации владельца брони)
- **Rate limit**: 10/час на IP
- **Request**:
```json
{
  "guest_phone": "+79001234567",
  "strength": 3,
  "notes": "Больше мяты, пожалуйста",
  "items": [
    {"tobacco_id": 1, "weight_grams": 20.0},
    {"tobacco_id": 5, "weight_grams": 15.0}
  ]
}
```
- **Response** (201):
```json
{
  "id": 42,
  "booking_id": 10,
  "table_id": 3,
  "strength": 3,
  "status": "pending",
  "source": "booking_preorder",
  "notes": "Больше мяты, пожалуйста",
  "items": [
    {"id": 1, "tobacco_id": 1, "tobacco_name": "Al Fakher Мята", "weight_grams": 20.0},
    {"id": 2, "tobacco_id": 5, "tobacco_name": "Darkside Grape Core", "weight_grams": 15.0}
  ],
  "created_at": "2026-03-06T18:00:00"
}
```
- **Errors**:
  - `404` — бронирование не найдено
  - `403` — телефон не совпадает с бронированием
  - `400` — табак не в наличии, невалидный strength (допустимый диапазон 1-10)
  - `429` — rate limit exceeded

### 6.2 Список заказов к бронированию
- **Method**: `GET`
- **URL**: `/api/bookings/{booking_id}/orders`
- **Auth**: public (проверка guest_phone через query param)
- **Response** (200): массив объектов заказов (как в 6.1 Response)

### 6.3 Публичный каталог табаков (уже существует, расширить фильтры)
- **Method**: `GET`
- **URL**: `/api/tobaccos?in_stock=true&strength_min=1&strength_max=4`
- **Auth**: public
- **Доработка**: добавить параметры `strength_min`, `strength_max` к существующим фильтрам (диапазон 1-10)

### 6.4 Рекомендации кальянщика
- **Method**: `GET`
- **URL**: `/api/master/recommendations?strength_level=light`
- **Auth**: public
- **Query params**: `strength_level` — `light` | `medium` | `strong` (обязательный)
- **Response** (200):
```json
[
  {
    "id": 1,
    "name": "Классика лёгкая",
    "strength_level": "light",
    "items": [
      {"tobacco_id": 3, "tobacco_name": "Al Fakher Яблоко", "weight_grams": 20},
      {"tobacco_id": 7, "tobacco_name": "Adalya Love 66", "weight_grams": 20}
    ]
  }
]
```
- **Errors**: `400` — невалидный strength_level

> CRUD для управления рекомендациями — в T-055 / T-090 (панель кальянщика)

## 7. Frontend Components / Компоненты

### 7.1 `HookahBuilder`
- **Путь**: `frontend/src/components/HookahBuilder/HookahBuilder.tsx`
- **Props**:
  - `onSubmit: (order: HookahOrderData) => void` — колбэк при подтверждении
  - `onCancel: () => void` — отмена
  - `tableId: number` — стол (для привязки)
  - `repeatSlot?: ReactNode` — слот для кнопки "Повторить" (Phase 3)
- **Состояние**: strength_level → recommendations + tobaccos (filtered) → selected items → notes → preview
- **Шаги**:
  1. Выбор крепости (3 карточки: Лёгкий 1-4 / Средний 5-7 / Крепкий 8-10)
  2. Блок "Рекомендует кальянщик" (если есть `MasterRecommendation`для выбранного уровня) + выбор табаков вручную (карточки с чекбоксами, макс. 3)
  3. Настройка веса (default 20г) + комментарий
  4. Предпросмотр + кнопка "Подтвердить"

### 7.2 `StrengthSelector`
- **Путь**: `frontend/src/components/HookahBuilder/StrengthSelector.tsx`
- 3 карточки с иконками и описанием

### 7.3 `MasterRecommendations`
- **Путь**: `frontend/src/components/HookahBuilder/MasterRecommendations.tsx`
- Отображается между StrengthSelector и TobaccoSelector если `GET /api/master/recommendations?strength_level=X` вернул непустой список
- Карточки рекомендаций: название + список табаков + кнопка "Выбрать этот микс"
- При клике — предзаполняет TobaccoSelector выбранными позициями

### 7.4 `TobaccoSelector`
- **Путь**: `frontend/src/components/HookahBuilder/TobaccoSelector.tsx`
- Карточки табаков с фильтрацией, чекбокс выбора, вкусовые теги

### 7.4 `OrderPreview`
- **Путь**: `frontend/src/components/HookahBuilder/OrderPreview.tsx`
- Сводка заказа перед подтверждением

### 7.5 Интеграция в Booking.tsx
- **Путь**: `frontend/src/pages/Booking.tsx`
- После успешного создания брони: экран "Бронь создана!" → кнопка "Добавить кальян"
- При клике — рендер `HookahBuilder` с `onSubmit` → `POST /api/bookings/{id}/orders`

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/app/models/enums.py` | Добавить `OrderSource` enum |
| `backend/app/models/order.py` | Добавить поле `source` в `HookahOrder` |
| `backend/app/schemas/booking.py` | Без изменений (заказ создаётся отдельным endpoint) |
| `backend/app/routers/bookings.py` | Добавить `POST /api/bookings/{id}/orders`, `GET /api/bookings/{id}/orders` |
| `backend/app/routers/tobaccos.py` | Добавить фильтры `strength_min`, `strength_max` |
| `backend/app/schemas/` | Новый файл `order.py` — Pydantic-схемы для заказов |
| `frontend/src/pages/Booking.tsx` | Добавить экран успеха с кнопкой "Добавить кальян" |
| `backend/app/models/master_recommendation.py` | Новая модель `MasterRecommendation` |
| `backend/app/routers/master.py` | Добавить `GET /api/master/recommendations` (публичный) + CRUD (T-055) |
| `frontend/src/components/HookahBuilder/` | Новая директория с компонентами |
| `frontend/src/api/client.ts` | Добавить функции API для заказов |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: Гость после создания брони видит кнопку "Добавить кальян"
- [ ] AC-2: HookahBuilder показывает 3 уровня крепости
- [ ] AC-3: При выборе крепости загружаются только табаки нужной крепости, в наличии
- [ ] AC-4: Можно выбрать 1-3 табака, указать вес каждого
- [ ] AC-5: Заказ успешно создаётся через `POST /api/bookings/{id}/orders`
- [ ] AC-6: Заказ привязан к бронированию (booking_id) и столу (table_id)
- [ ] AC-7: Поле `source` = `booking_preorder`
- [ ] AC-8: Можно добавить несколько кальянов к одной брони
- [ ] AC-9: Кальянщик видит предзаказы в панели (зависит от T-090)
- [ ] AC-10: Mobile-first — корректное отображение на 320px+
- [ ] AC-11: При выборе крепости загружаются рекомендации от кальянщика (если есть)
- [ ] AC-12: Нажатие "Выбрать этот микс" предзаполняет TobaccoSelector позициями из рекомендации
- [ ] AC-13: Strength хранится как int 1-10; в UI отображается как Лёгкий/Средний/Крепкий

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-050 | Enum OrderSource + поле source в HookahOrder + миграция | backend | T-030 | S |
| T-051 | Pydantic-схемы заказа (OrderCreate, OrderPublic, OrderItem) | backend | T-050 | S |
| T-052 | API: POST/GET /api/bookings/{id}/orders + фильтры tobaccos | backend | T-051, T-031 | M |
| T-053 | Компонент HookahBuilder (StrengthSelector, MasterRecommendations, TobaccoSelector, OrderPreview) | frontend | T-052, T-055 | L |
| T-054 | Интеграция HookahBuilder в Booking.tsx + экран успеха | frontend | T-053 | M |
| T-055 | MasterRecommendation модель + миграция + CRUD API + публичный GET | backend | T-050, T-020 | M |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Статус |
|---|--------|--------|
| 1 | Максимальное количество кальянов на одну бронь? (предлагаю 5) | ⬜ Открыт |
| 2 | ~~Нужна ли рекомендация табаков?~~ | ✅ Решено: добавлены рекомендации кальянщика (FR-050-01a, T-055) |
| 3 | Показывать ли цену кальяна (если да — нужно поле price в Tobacco)? | ⬜ Открыт |
