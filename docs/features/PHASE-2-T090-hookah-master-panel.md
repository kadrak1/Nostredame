# Feature: Панель кальянщика

**Phase**: 2
**PRD Requirement**: R10
**Status**: Planned
**Dependencies**: T-050 (hookah preorder), T-060 (QR ordering)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

Кальянщик сейчас не имеет интерфейса для управления очередью заказов — узнаёт о заказах устно или через мессенджеры. Панель кальянщика — упрощённый веб-интерфейс (мобильный, без лишнего): очередь заказов в реальном времени, управление статусами (принял → готовит → подал). Панель доступна по отдельному маршруту `/master/*` с авторизацией по роли `hookah_master`.

## 2. User Stories

- **US-090-1**: Как кальянщик, я хочу видеть все активные заказы с номером стола и составом, чтобы понимать что готовить.
- **US-090-2**: Как кальянщик, я хочу принять заказ в работу, чтобы гость знал что я начал готовить.
- **US-090-3**: Как кальянщик, я хочу отметить кальян поданным, чтобы завершённый заказ исчез из очереди.
- **US-090-4**: Как кальянщик, я хочу слышать звуковой сигнал при новом заказе, чтобы не пропустить его.
- **US-090-5**: Как кальянщик, я хочу видеть все заказы за день, чтобы оценить загрузку.

## 3. Functional Requirements / Функциональные требования

### 3.1 Авторизация
- FR-090-01: Вход через существующий `POST /api/auth/login` с ролью `hookah_master`
- FR-090-02: Redirect на `/master/orders` после входа
- FR-090-03: Sidebar максимально упрощён: только "Очередь" и "История"

### 3.2 Очередь заказов (реальное время)
- FR-090-04: Показывает все заказы со статусами `pending`, `accepted`, `preparing`
- FR-090-05: Карточка заказа содержит:
  - Номер стола (крупно)
  - Крепость (цветная пометка: зелёный/жёлтый/красный)
  - Список табаков с граммовкой
  - Комментарий (если есть)
  - Время создания + таймер "сколько ждёт"
  - Кнопки управления статусом
- FR-090-06: Заказы сортируются по времени создания (FIFO)
- FR-090-07: Новые заказы добавляются без перезагрузки (WebSocket)
- FR-090-08: Звуковое уведомление при новом заказе (Web Audio API)
- FR-090-09: Вибрация на мобильном при новом заказе (Vibration API)

### 3.3 Управление статусами
- FR-090-10: Кнопка "Принять" (`pending` → `accepted`) — отображается только для `pending`
- FR-090-11: Кнопка "Готовлю" (`accepted` → `preparing`) — старт таймера готовки
- FR-090-12: Кнопка "Подан" (`preparing` → `served`) — карточка исчезает из очереди (гостю статус не передаётся)
- FR-090-13: Кнопка "Отменить" — доступна для `pending` и `accepted`, с подтверждением

### 3.4 История заказов
- FR-090-14: Список заказов за выбранный день (по умолчанию — сегодня)
- FR-090-15: Фильтр: всё / только выполненные / только отменённые
- FR-090-16: Карточка в истории: сводка + финальный статус + время исполнения

### 3.5 WebSocket очереди
- FR-090-17: `WS /ws/master/orders` — поток событий для кальянщика
- FR-090-18: Типы событий: `order.created`, `order.updated`, `order.cancelled`
- FR-090-19: Один кальянщик = одно WebSocket соединение

### 3.6 Управление рекомендованными миксами
- FR-090-20: Кальянщик/admin/owner может создавать рекомендованные миксы (модель `MasterRecommendation` из T-055)
- FR-090-21: Форма создания микса: название (≤100 символов), уровень крепости (Лёгкий/Средний/Крепкий), список табаков с граммовкой
- FR-090-22: Список рекомендаций в панели с возможностью включить/отключить (`is_active`) и удалить
- FR-090-23: Максимум 10 активных рекомендаций на заведение (ошибка 422 при превышении)
- FR-090-24: Рекомендации отображаются гостям в HookahBuilder сразу после сохранения

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-090-01: Страница загружается < 2 сек на мобильном (3G)
- NFR-090-02: Mobile-first — кальянщик работает с телефоном в руке
- NFR-090-03: Крупные кнопки (min 44px tap area) — удобно в перчатках
- NFR-090-04: Тёмная тема — уместна в атмосфере кальянной
- NFR-090-05: При разрыве WebSocket — автоматическое переподключение каждые 5 сек

## 5. Database Changes / Изменения в БД

### 5.1 Расширение HookahOrder
```python
# Добавить поле для назначения кальянщика (опционально для MVP):
assigned_master_id: Mapped[int | None] = mapped_column(
    ForeignKey("users.id"), nullable=True
)
```

### 5.2 Миграции
- Alembic: добавить `assigned_master_id` в `hookah_orders` (nullable)

## 6. API Endpoints

### 6.1 Список активных заказов
- **Method**: `GET`
- **URL**: `/api/master/orders`
- **Auth**: JWT, роль `hookah_master` или `admin`
- **Query**: `?status=active` (pending+accepted+preparing) или `?date=2026-03-06`
- **Response** (200):
```json
{
  "orders": [
    {
      "id": 42,
      "public_id": "a1b2c3d4",
      "table_number": 3,
      "strength": 3,
      "strength_label": "Средний",
      "notes": "Больше дыма",
      "status": "pending",
      "source": "qr_table",
      "guest_name": "Алексей",
      "wait_seconds": 180,
      "items": [
        {"tobacco_name": "Al Fakher Мята", "brand": "Al Fakher", "weight_grams": 15.0},
        {"tobacco_name": "Darkside Grape Core", "brand": "Darkside", "weight_grams": 10.0}
      ],
      "created_at": "2026-03-06T19:00:00"
    }
  ],
  "total": 3
}
```

### 6.2 Смена статуса заказа
- **Method**: `PUT`
- **URL**: `/api/master/orders/{id}/status`
- **Auth**: JWT, роль `hookah_master` или `admin`
- **Request**: `{"status": "accepted" | "preparing" | "served" | "cancelled"}`
- **Response** (200): обновлённый заказ
- **Errors**: `404` — заказ не найден, `400` — недопустимый переход статуса, `403` — недостаточно прав

### 6.3 CRUD рекомендованных миксов (только для роли master/admin/owner)
- **Method**: `POST`
- **URL**: `/api/master/recommendations`
- **Auth**: `hookah_master | admin | owner`
- **Request**: `{ "name": "Тропический микс", "strength_level": "medium", "items": [{"tobacco_id": 3, "weight_grams": 20}] }`
- **Response** (201): созданный объект `MasterRecommendation`
- **Errors**: `422` — превышен лимит 10 активных рекомендаций, табак не в наличии

- **Method**: `GET` **URL**: `/api/master/recommendations` — все рекомендации заведения (admin-список, включая неактивные)
- **Method**: `PUT` **URL**: `/api/master/recommendations/{id}` — обновить (название, состав, is_active)
- **Method**: `DELETE` **URL**: `/api/master/recommendations/{id}` — удалить

> Публичный эндпоинт `GET /api/master/recommendations?strength_level=X` описан в T-050 (6.4) — используется в HookahBuilder

### 6.4 WebSocket очереди для кальянщика
- **URL**: `WS /ws/master/orders`
- **Auth**: JWT в query param `?token=<access_token>`
- **Входящие события**:
```json
{"event": "order.created", "order": {...}}
{"event": "order.updated", "order": {...}}
{"event": "order.cancelled", "order_id": 42}
```
- **Исходящие** (ping): `{"type": "ping"}` каждые 30 сек

## 7. Frontend Components / Компоненты

### 7.1 `MasterLayout`
- **Путь**: `frontend/src/layouts/MasterLayout.tsx`
- Упрощённый layout: только header с именем кальянщика + выход, и контент
- Без бокового меню (всё на одной странице или 2 вкладки)

### 7.2 `OrderQueue`
- **Путь**: `frontend/src/pages/master/OrderQueue.tsx`
- **Route**: `/master/orders`
- Список карточек `OrderCard`, WebSocket подключение, звуковые уведомления

### 7.3 `OrderCard`
- **Путь**: `frontend/src/components/master/OrderCard.tsx`
- **Props**: `order: MasterOrder`, `onStatusChange: (id, status) => void`
- Карточка со всей информацией и кнопками статусов
- Таймер ожидания (обновляется каждые 10 сек через `setInterval`)
- Анимация появления новой карточки (slide-in)

### 7.4 `OrderHistory`
- **Путь**: `frontend/src/pages/master/OrderHistory.tsx`
- **Route**: `/master/history`
- Список за день с датой-фильтром, статистика (выполнено/отменено)

### 7.5 Звуковые уведомления
- **Путь**: `frontend/src/hooks/useOrderNotification.ts`
- `useOrderNotification()` — хук, воспроизводит звук и вибрацию при `order.created`
- Звук: короткий тон через Web Audio API (без внешних файлов)

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/app/routers/master.py` | Новый файл — master endpoints |
| `backend/app/main.py` | Регистрация роутера + WS endpoint `/ws/master/orders` |
| `backend/app/services/ws_manager.py` | Расширение из T-060 — добавить `master_manager` |
| `backend/app/dependencies.py` | Добавить `require_hookah_master` dependency |
| `backend/app/models/order.py` | Добавить `assigned_master_id` |
| `frontend/src/App.tsx` | Маршруты `/master/*` |
| `frontend/src/layouts/MasterLayout.tsx` | Новый файл |
| `frontend/src/pages/master/OrderQueue.tsx` | Новый файл |
| `frontend/src/pages/master/OrderHistory.tsx` | Новый файл |
| `frontend/src/components/master/OrderCard.tsx` | Новый файл |
| `frontend/src/hooks/useOrderNotification.ts` | Новый файл |
| `frontend/src/pages/master/Recommendations.tsx` | Новый файл — CRUD рекомендаций |
| `frontend/src/components/master/RecommendationForm.tsx` | Новый файл — форма создания/редактирования |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: Кальянщик входит с ролью `hookah_master` → попадает на `/master/orders`
- [ ] AC-2: Новый заказ появляется в очереди без перезагрузки (WebSocket)
- [ ] AC-3: Звуковой сигнал при новом заказе (если открыта вкладка)
- [ ] AC-4: Кнопка "Принять" переводит в `accepted`, гость видит обновление статуса
- [ ] AC-5: Кнопка "Подан" переводит в `served`, заказ пропадает из очереди
- [ ] AC-6: Нельзя нажать "Готовлю" до "Принять" (последовательность)
- [ ] AC-7: Таймер ожидания показывает сколько минут гость ждёт
- [ ] AC-8: История заказов за день с фильтрами работает
- [ ] AC-9: При разрыве WebSocket — автоматическое переподключение
- [ ] AC-10: Кальянщик не видит бронирования (только заказы кальянов)
- [ ] AC-11: Кнопки крупные (44px+), корректны на мобильном
- [ ] AC-12: Кальянщик может создать рекомендованный микс и он сразу появляется в HookahBuilder
- [ ] AC-13: Деактивированный микс не отображается гостям в HookahBuilder

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-090 | Master API: GET /api/master/orders + PUT status + зависимость hookah_master | backend | T-050, T-060 | M |
| T-091 | WS /ws/master/orders + ws_manager расширение | backend | T-062, T-090 | M |
| T-092 | MasterLayout + маршруты + auth guard | frontend | T-011 | S |
| T-093 | OrderQueue страница + OrderCard компонент + WebSocket | frontend | T-091, T-092 | L |
| T-094 | OrderHistory страница + звуковые уведомления (useOrderNotification) | frontend | T-092 | M |
| T-095 | Recommendations страница + RecommendationForm в панели кальянщика | frontend | T-055, T-092 | M |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Кто отвечает |
|---|--------|--------------|
| 1 | Нужен ли таймер готовки (сколько времени занял кальянщик)? | Владелец |
| 2 | Видит ли кальянщик брони или только активные заказы? | Владелец |
| 3 | Может ли быть несколько кальянщиков одновременно? | Владелец |
| 4 | Нужна ли статистика (среднее время готовки) в панели кальянщика? | Владелец |
