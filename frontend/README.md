# HookahBook — Frontend

React-приложение для гостей и админ-панели HookahBook. Часть монорепозитория — см. [корневой README](../README.md) для общего контекста.

---

## Стек

| Технология | Версия | Назначение |
|-----------|--------|-----------|
| React | 18 | UI |
| TypeScript | 5 | Типизация |
| Vite | 6 | Dev-сервер, сборка |
| React Router | v6 | Маршрутизация |
| React Query (TanStack) | v5 | Серверное состояние, кеширование |
| Axios | — | HTTP-клиент |
| react-konva | — | Canvas-редактор плана зала |
| Shadcn/UI | — | UI-компоненты |
| Lucide | — | Иконки |
| Sonner | — | Toast-уведомления |

---

## Структура

```
frontend/src/
├── api/                 # API-клиент: axios-инстанс, react-query хуки
├── assets/              # Изображения, шрифты
├── layouts/             # Layout-компоненты (AdminLayout, GuestLayout)
├── pages/               # Страницы, разбитые по ролям
│   ├── admin/           #   Конструктор зала, каталог табаков, бронирования
│   └── guest/           #   Бронирование, профиль гостя, настройки уведомлений
├── App.tsx              # Корневой компонент, провайдеры
├── auth.tsx             # Утилиты аутентификации
├── App.css
└── index.css            # Глобальные стили, CSS-переменные темы
frontend/public/
└── sw.js                # Service Worker для Web Push (Phase 3)
```

---

## Запуск

```bash
# Установить зависимости
npm install

# Dev-сервер (API проксируется на localhost:8000)
npm run dev

# Сборка для production
npm run build

# Предпросмотр production-сборки
npm run preview
```

Переменные окружения — скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

---

## Команды

| Команда | Описание |
|---------|---------|
| `npm run dev` | Dev-сервер с HMR |
| `npm run build` | Production-сборка в `dist/` |
| `npm run preview` | Превью production-сборки |
| `npm run lint` | Линтинг (ESLint) |
| `npx tsc --noEmit` | Проверка типов без компиляции |

---

## Маршруты

| Путь | Компонент | Доступ |
|------|----------|--------|
| `/` | Главная + кнопка бронирования | Публичный |
| `/book` | Флоу бронирования (5 шагов) | Публичный |
| `/booking/:id` | Статус брони | Публичный |
| `/admin` | Redirect → `/admin/bookings` | Только admin |
| `/admin/floor` | Конструктор зала (react-konva) | owner, admin |
| `/admin/tobaccos` | Каталог табаков | owner, admin |
| `/admin/bookings` | Дашборд бронирований | owner, admin |
| `/guest/profile` | Профиль гостя | guest JWT |
| `/guest/notifications` | Настройки уведомлений | guest JWT |
| `/login` | Логин администратора | Публичный |

---

## Особенности безопасности

- **JWT в httpOnly cookie** — access и refresh токены хранятся в httpOnly cookie, а не в `localStorage` (защита от XSS)
- **Нет `dangerouslySetInnerHTML`** — запрещено через ESLint
- **API прокси в dev** — все запросы к `/api/*` проксируются через Vite на `localhost:8000`, CORS не нужен
- **React экранирует вывод** — по умолчанию, все данные из API рендерятся безопасно

---

## Переменные окружения

| Переменная | Описание |
|-----------|---------|
| `VITE_API_URL` | URL backend API (только production; в dev — прокси) |
| `VITE_VAPID_PUBLIC_KEY` | Публичный VAPID-ключ для Web Push (Phase 3) |
| `VITE_TELEGRAM_BOT_USERNAME` | Username бота для Telegram Login Widget |

> Все переменные `VITE_*` попадают в JS-бандл. Никогда не помещайте сюда приватные ключи или токены.

---

## Дизайн

Тёмная тема. Цветовая палитра и UX-флоу описаны в [`docs/DESIGN-BRIEF.md`](../docs/DESIGN-BRIEF.md).

**Ключевые принципы:**
- Mobile-first (80%+ трафика с телефона)
- Не более 4 тапов от открытия до бронирования
- Акцентный цвет `#E94560`, фон `#1A1A2E`
