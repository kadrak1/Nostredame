# Feature: История заказов и повтор кальяна

**Phase**: 3
**PRD Requirement**: — (Phase 3)
**Status**: Planned
**Dependencies**: T-080 (guest auth), T-050 (hookah preorder), T-060 (QR ordering)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

Постоянные гости хотят не объяснять кальянщику свой микс каждый раз. После авторизации по телефону (T-080) система "помнит" гостя и предлагает повторить предыдущий заказ в один тап. Это:
- Экономит время гостя при повторном заказе
- Сокращает вероятность ошибок кальянщика
- Повышает лояльность (персонализация)

Ключевые сценарии: повтор при предзаказе во время бронирования, повтор при QR-заказе за столом.

## 2. User Stories

- **US-100-1**: Как возвращающийся гость, я хочу видеть мой последний кальян при новом бронировании и повторить его одной кнопкой.
- **US-100-2**: Как гость за столом (QR), я хочу видеть мой последний кальян и нажать "Повторить", чтобы не выбирать табаки заново.
- **US-100-3**: Как авторизованный гость, я хочу просматривать всю историю моих заказов и броней.
- **US-100-4**: Как гость, я хочу сохранить любимый микс как "Избранный" и быстро к нему возвращаться.

## 3. Functional Requirements / Функциональные требования

### 3.1 Повтор последнего заказа
- FR-100-01: При открытии HookahBuilder авторизованным гостем — показать блок "Ваш последний кальян" (занимает верхнюю часть экрана)
- FR-100-02: Блок показывает: крепость, список табаков с весом, комментарий
- FR-100-03: Кнопка "Повторить" — создаёт новый заказ с теми же параметрами (source текущего контекста: `booking_preorder` или `qr_table`)
- FR-100-04: Кнопка "Изменить" — открывает HookahBuilder с предзаполненными полями из последнего заказа
- FR-100-05: Если авторизованный гость никогда не заказывал — блок не показывается

### 3.2 История заказов
- FR-100-06: Страница `/guest/orders` — список заказов гостя в обратном хронологическом порядке
- FR-100-07: Карточка заказа: дата, номер стола, крепость, состав, статус
- FR-100-08: Пагинация: 10 заказов на страницу
- FR-100-09: Заказы из всех каналов (бронирование + QR + Telegram)
- FR-100-10: История броней: список броней гостя с датой, столом, статусом

### 3.3 Избранные миксы
- FR-100-11: Кнопка "Сохранить как избранный" доступна после просмотра любого заказа
- FR-100-12: Имя избранного — редактируемый текст ("Мой стандартный", "Крепкий на вечер")
- FR-100-13: Максимум 5 избранных миксов на гостя
- FR-100-14: Страница `/guest/favorites` — список сохранённых миксов с кнопкой "Заказать"
- FR-100-15: "Заказать" из избранного создаёт заказ (выбор контекста: уточнить номер стола или привязать к текущей брони)

### 3.4 Компонент RepeatOrderButton
- FR-100-16: Переиспользуемый компонент, встраиваемый в `HookahBuilder` (слот `repeatSlot`)
- FR-100-17: Получает `last_order` через `GET /api/guest/last-order` при монтировании
- FR-100-18: Показывается только если `useOptionalGuest()` вернул авторизованного гостя
- FR-100-19: Обновляет состояние HookahBuilder при нажатии "Повторить"

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-100-01: `GET /api/guest/last-order` — < 200мс (простой SELECT по guest_id)
- NFR-100-02: RepeatOrderButton не замедляет загрузку HookahBuilder (lazy load)
- NFR-100-03: История пагинирована — не загружает всю историю сразу
- NFR-100-04: Максимум 5 избранных — защита от бесконечного накопления

## 5. Database Changes / Изменения в БД

### 5.1 Новая таблица FavoriteMix
```python
class FavoriteMix(Base):
    __tablename__ = "favorite_mixes"

    id: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    strength: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    items: Mapped[str] = mapped_column(Text)  # JSON: [{"tobacco_id": 1, "weight_grams": 15.0}]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    guest = relationship("Guest")
```

### 5.2 Миграции
- Alembic: создать таблицу `favorite_mixes`

## 6. API Endpoints

### 6.1 Последний заказ гостя
- **Method**: `GET`
- **URL**: `/api/guest/last-order`
- **Auth**: guest JWT (cookie `guest_token`)
- **Response** (200):
```json
{
  "order_id": 42,
  "strength": 3,
  "strength_label": "Средний",
  "notes": "Больше мяты",
  "items": [
    {"tobacco_id": 1, "tobacco_name": "Al Fakher Мята", "weight_grams": 15.0},
    {"tobacco_id": 5, "tobacco_name": "Darkside Grape Core", "weight_grams": 10.0}
  ],
  "created_at": "2026-02-15T18:00:00"
}
```
- **Response** (204): если заказов ещё нет
- **Errors**: `401` — не авторизован

### 6.2 История заказов
- **Method**: `GET`
- **URL**: `/api/guest/orders`
- **Auth**: guest JWT
- **Query**: `?page=1&per_page=10`
- **Response** (200):
```json
{
  "items": [
    {
      "id": 42,
      "table_number": 3,
      "strength": 3,
      "status": "served",
      "source": "qr_table",
      "items": [...],
      "created_at": "2026-02-15T18:00:00"
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 10
}
```

### 6.3 Повтор заказа
- **Method**: `POST`
- **URL**: `/api/guest/orders/{order_id}/repeat`
- **Auth**: guest JWT
- **Request**:
```json
{
  "table_id": 3,
  "source": "qr_table",
  "booking_id": null
}
```
- **Response** (201): новый `HookahOrder` (как в T-060 POST /api/orders)
- **Errors**: `404` — заказ не найден, `403` — не ваш заказ, `400` — табак не в наличии

### 6.4 CRUD Избранных миксов
- **Method**: `POST /api/guest/favorites` — сохранить микс
- **Method**: `GET /api/guest/favorites` — список (max 5)
- **Method**: `PUT /api/guest/favorites/{id}` — переименовать
- **Method**: `DELETE /api/guest/favorites/{id}` — удалить
- **Auth**: guest JWT

- **POST Request**:
```json
{
  "name": "Мой стандартный",
  "order_id": 42
}
```
- **GET Response**:
```json
{
  "items": [
    {
      "id": 1,
      "name": "Мой стандартный",
      "strength": 3,
      "items": [...],
      "created_at": "2026-02-15"
    }
  ]
}
```
- **Errors**: `400` — превышен лимит 5 избранных

## 7. Frontend Components / Компоненты

### 7.1 `RepeatOrderButton`
- **Путь**: `frontend/src/components/HookahBuilder/RepeatOrderButton.tsx`
- **Props**: `onRepeat: (order: HookahOrderData) => void`, `onCustomize: (order: HookahOrderData) => void`
- **Логика**: вызывает `GET /api/guest/last-order` при монтировании; рендерится только если данные получены
- **Вид**: карточка с составом заказа + 2 кнопки (Повторить / Изменить)

### 7.2 `OrderHistory`
- **Путь**: `frontend/src/pages/guest/OrderHistory.tsx`
- **Route**: `/guest/orders`
- Список карточек заказов, пагинация

### 7.3 `Favorites`
- **Путь**: `frontend/src/pages/guest/Favorites.tsx`
- **Route**: `/guest/favorites`
- Список сохранённых миксов + кнопка "Заказать" для каждого

### 7.4 `GuestNav`
- **Путь**: `frontend/src/components/GuestNav.tsx`
- Навбар для авторизованного гостя: История / Избранные / Выйти

### 7.5 Интеграция в HookahBuilder
- Пропс `repeatSlot` в `HookahBuilder` — передаётся `<RepeatOrderButton />` когда `useOptionalGuest()` != null
- Встраивается в `Booking.tsx` и `TableOrder.tsx`

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/app/models/` | Новый файл `favorite_mix.py` — модель FavoriteMix |
| `backend/app/routers/guest.py` | Добавить GET /api/guest/last-order, GET /api/guest/orders, POST /api/guest/orders/{id}/repeat, CRUD favorites |
| `backend/app/schemas/guest.py` | Добавить схемы: OrderHistory, FavoriteMix, RepeatOrder |
| `frontend/src/components/HookahBuilder/RepeatOrderButton.tsx` | Новый файл |
| `frontend/src/components/HookahBuilder/HookahBuilder.tsx` | Добавить prop `repeatSlot: ReactNode` |
| `frontend/src/pages/guest/OrderHistory.tsx` | Новый файл |
| `frontend/src/pages/guest/Favorites.tsx` | Новый файл |
| `frontend/src/components/GuestNav.tsx` | Новый файл |
| `frontend/src/pages/Booking.tsx` | Передать RepeatOrderButton в HookahBuilder |
| `frontend/src/pages/TableOrder.tsx` | Передать RepeatOrderButton в HookahBuilder |
| `frontend/src/App.tsx` | Добавить маршруты /guest/orders, /guest/favorites |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: Авторизованный гость видит "Ваш последний кальян" в HookahBuilder при наличии истории
- [ ] AC-2: Кнопка "Повторить" создаёт новый заказ с теми же параметрами
- [ ] AC-3: Кнопка "Изменить" открывает HookahBuilder с предзаполненными полями
- [ ] AC-4: Анонимный гость не видит RepeatOrderButton
- [ ] AC-5: `GET /api/guest/orders` возвращает пагинированную историю
- [ ] AC-6: Можно сохранить микс как избранный (до 5 штук)
- [ ] AC-7: 6-й избранный отклоняется (400)
- [ ] AC-8: RepeatOrderButton работает в Booking.tsx и TableOrder.tsx
- [ ] AC-9: Повтор заказа с недоступным табаком — 400 с сообщением об ошибке
- [ ] AC-10: История заказов из всех каналов (бронирование + QR + Telegram)

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-100 | FavoriteMix модель + миграция | backend | T-080 | S |
| T-101 | GET /api/guest/last-order + GET /api/guest/orders | backend | T-080, T-060 | M |
| T-102 | POST /api/guest/orders/{id}/repeat + проверка наличия | backend | T-101 | M |
| T-103 | CRUD /api/guest/favorites + лимит 5 | backend | T-100 | S |
| T-104 | RepeatOrderButton + интеграция в HookahBuilder, Booking, TableOrder | frontend | T-053, T-063, T-101 | M |
| T-105 | OrderHistory + Favorites страницы + GuestNav | frontend | T-101, T-103 | M |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Кто отвечает |
|---|--------|--------------|
| 1 | Показывать ли историю броней отдельно от истории заказов? | Владелец |
| 2 | Лимит 5 избранных — достаточно? Или сделать настраиваемым? | Владелец |
| 3 | Можно ли "повторить" заказ с табаком, которого нет в наличии, предложив замену? | Владелец |
