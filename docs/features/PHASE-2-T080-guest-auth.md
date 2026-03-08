# Feature: Авторизация гостя по номеру телефона

**Phase**: 2
**PRD Requirement**: R8
**Status**: Planned
**Dependencies**: T-030 (Guest model)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

Сейчас гости анонимны — при каждом бронировании вводят имя и телефон заново. Это не позволяет предлагать повтор заказа, показывать историю, отправлять уведомления.

Авторизация по номеру телефона — максимально простой вход: одно поле (номер телефона), одна кнопка ("Войти"). Система ищет гостя по хэшу телефона или создаёт нового и выдаёт гостевой JWT. Без SMS-верификации, без Telegram Login — минимум friction для MVP.

Гостевой JWT отделён от админского и имеет ограниченные права: просмотр своей истории, повтор заказов, управление профилем.

## 2. User Stories

- **US-080-1**: Как гость, я хочу войти в систему по номеру телефона, чтобы видеть свои предыдущие заказы.
- **US-080-2**: Как гость, я хочу при повторном бронировании не вводить данные заново, чтобы сэкономить время.
- **US-080-3**: Как авторизованный гость, я хочу видеть свой профиль с историей посещений.
- **US-080-4**: Как система, я хочу идентифицировать возвращающихся гостей, чтобы предлагать персонализированный опыт.

## 3. Functional Requirements / Функциональные требования

### 3.1 Вход по телефону
- FR-080-01: Единственное поле — номер телефона в формате +7XXXXXXXXXX
- FR-080-02: Кнопка "Войти" — отправляет `POST /api/auth/guest`
- FR-080-03: Система хэширует телефон (`hash_phone` из `services/security.py`) и ищет `Guest` по `phone_hash`
- FR-080-04: Если гость найден → выдать гостевой JWT
- FR-080-05: Если гость НЕ найден → создать нового `Guest` (phone_hash + phone_encrypted) → выдать JWT
- FR-080-06: Гостевой JWT содержит: `guest_id`, `role: "guest"`, `exp` (7 дней)
- FR-080-07: JWT хранится в httpOnly cookie (как админский, но другое имя: `guest_token`)

### 3.2 Гостевой JWT
- FR-080-08: Отдельный от админского JWT — разные cookie names, разные claims
- FR-080-09: TTL access token: 7 дней (гости заходят реже, не нужен refresh)
- FR-080-10: Dependency injection: `get_current_guest` — аналог `get_current_user`, но для гостей
- FR-080-11: Опциональная авторизация: `get_optional_guest` — возвращает `Guest | None` (для показа блока "Повторить" авторизованным, без блокировки анонимных)

### 3.3 Профиль гостя
- FR-080-12: `GET /api/guest/me` — имя, маскированный телефон, дата первого визита, количество заказов
- FR-080-13: `PUT /api/guest/me` — обновить имя (единственное редактируемое поле)
- FR-080-14: `POST /api/auth/guest/logout` — удаление cookie

### 3.4 Интеграция с бронированием
- FR-080-15: Если гость авторизован при бронировании — имя и телефон заполнены автоматически
- FR-080-16: Новые бронирования автоматически привязываются к `guest_id`

### 3.5 Безопасность
- FR-080-17: Rate limit на `POST /api/auth/guest`: 10/мин на IP (защита от перебора)
- FR-080-18: Brute-force защита: блокировка IP на 15 мин после 20 попыток за 10 мин
- FR-080-19: Телефон хранится ТОЛЬКО в хэшированном + зашифрованном виде (существующий механизм)
- FR-080-20: Audit log: все входы гостей логируются (IP, phone_hash, timestamp)

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-080-01: Время входа < 500мс (один запрос к БД)
- NFR-080-02: Вход не требует внешних сервисов (без SMS API, без Telegram)
- NFR-080-03: Форма входа — mobile-first, одно поле + одна кнопка
- NFR-080-04: Cookie `guest_token` — httpOnly, Secure, SameSite=Strict

## 5. Database Changes / Изменения в БД

### 5.1 Расширение Guest
```python
# backend/app/models/guest.py — добавить поля:
last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
login_count: Mapped[int] = mapped_column(Integer, default=0)
```

### 5.2 Миграции
- Alembic: добавить `last_login_at` (nullable) и `login_count` (default=0) в `guests`

## 6. API Endpoints

### 6.1 Вход гостя
- **Method**: `POST`
- **URL**: `/api/auth/guest`
- **Auth**: public
- **Rate limit**: 10/мин на IP
- **Request**:
```json
{
  "phone": "+79001234567"
}
```
- **Response** (200 — существующий гость / 201 — новый):
```json
{
  "guest_id": 42,
  "name": "Алексей",
  "is_new": false
}
```
- **Cookies**: `Set-Cookie: guest_token=<JWT>; HttpOnly; Secure; SameSite=Strict; Max-Age=604800`
- **Errors**:
  - `400` — невалидный формат телефона
  - `429` — rate limit exceeded

### 6.2 Профиль гостя
- **Method**: `GET`
- **URL**: `/api/guest/me`
- **Auth**: guest JWT (cookie `guest_token`)
- **Response** (200):
```json
{
  "id": 42,
  "name": "Алексей",
  "phone_masked": "+7***4567",
  "first_visit": "2026-02-15",
  "total_orders": 5,
  "total_bookings": 3
}
```
- **Errors**: `401` — не авторизован

### 6.3 Обновление профиля
- **Method**: `PUT`
- **URL**: `/api/guest/me`
- **Auth**: guest JWT
- **Request**: `{"name": "Алексей К."}`
- **Response** (200): обновлённый профиль

### 6.4 Выход
- **Method**: `POST`
- **URL**: `/api/auth/guest/logout`
- **Auth**: guest JWT
- **Response** (200): `{"ok": true}`
- **Cookies**: `Set-Cookie: guest_token=; Max-Age=0` (удаление)

## 7. Frontend Components / Компоненты

### 7.1 `PhoneLogin`
- **Путь**: `frontend/src/components/PhoneLogin.tsx`
- **Содержание**: поле ввода телефона с маской (+7 XXX XXX-XX-XX), кнопка "Войти"
- **Стиль**: тёмная тема, крупный шрифт, мобильная клавиатура `type="tel"`
- **Состояние**: loading, error (невалидный формат), success → redirect

### 7.2 `GuestProfile`
- **Путь**: `frontend/src/components/GuestProfile.tsx`
- **Содержание**: аватар (инициалы), имя, маскированный телефон, статистика, кнопка "Выйти"
- **Используется**: в навбаре (если гость авторизован)

### 7.3 Расширение `auth.tsx`
- **Путь**: `frontend/src/auth.tsx`
- **Изменение**: добавить `GuestAuthProvider`, `useGuest()`, `useOptionalGuest()`
- **Логика**: при загрузке приложения — проверить cookie `guest_token` → `GET /api/guest/me`

### 7.4 Интеграция в Booking.tsx
- **Путь**: `frontend/src/pages/Booking.tsx`
- **Изменение**: если `useOptionalGuest()` вернул гостя → предзаполнить имя и телефон на шаге 4

## 8. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `backend/app/models/guest.py` | Добавить `last_login_at`, `login_count` |
| `backend/app/routers/auth.py` | Добавить `POST /api/auth/guest`, `POST /api/auth/guest/logout` |
| `backend/app/routers/guest.py` | Новый файл — `GET/PUT /api/guest/me` |
| `backend/app/schemas/guest.py` | Новый файл — `GuestLogin`, `GuestProfile`, `GuestUpdate` |
| `backend/app/dependencies.py` | Добавить `get_current_guest`, `get_optional_guest` |
| `backend/app/services/security.py` | Переиспользовать `hash_phone`, `encrypt_phone`, `decrypt_phone` |
| `backend/app/main.py` | Зарегистрировать `guest` роутер |
| `frontend/src/auth.tsx` | Добавить `GuestAuthProvider`, `useGuest()`, `useOptionalGuest()` |
| `frontend/src/components/PhoneLogin.tsx` | Новый файл |
| `frontend/src/components/GuestProfile.tsx` | Новый файл |
| `frontend/src/pages/Booking.tsx` | Предзаполнение данных авторизованного гостя |

## 9. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: Гость вводит телефон → получает JWT → видит профиль
- [ ] AC-2: При повторном входе с тем же телефоном — тот же `guest_id`
- [ ] AC-3: Новый телефон → создаётся новый Guest
- [ ] AC-4: Гостевой JWT не даёт доступ к админским endpoints (401)
- [ ] AC-5: Админский JWT не работает как гостевой (разные cookies)
- [ ] AC-6: Rate limit: 11-й запрос за минуту отклоняется (429)
- [ ] AC-7: При бронировании авторизованного гостя — имя и телефон предзаполнены
- [ ] AC-8: Logout удаляет cookie, `GET /api/guest/me` возвращает 401
- [ ] AC-9: Телефон нигде не логируется в открытом виде
- [ ] AC-10: Mobile-first — форма входа корректна на 320px+

## 10. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-080 | Расширение Guest модели + миграция (last_login_at, login_count) | backend | T-030 | S |
| T-081 | Guest auth API: POST /api/auth/guest + JWT + cookies | backend | T-080, T-004 | M |
| T-082 | Guest profile API: GET/PUT /api/guest/me + dependencies | backend | T-081 | S |
| T-083 | PhoneLogin компонент + GuestAuthProvider + интеграция Booking | frontend | T-081 | M |

## 11. Open Questions / Открытые вопросы

| # | Вопрос | Ответ | Дата |
|---|--------|-------|------|
| 1 | Нужно ли в будущем добавить SMS-верификацию поверх телефонного входа? | Да, но только после релиза текущей версии. В MVP — без SMS. | 2026-03-08 |
| 2 | Должен ли гостевой JWT истекать при каждом визите или быть постоянным? | 7 дней TTL. | 2026-03-08 |
| 3 | Показывать ли кнопку "Войти" на главной странице или только в процессе бронирования? | Показывать на главной странице. | 2026-03-08 |
