# HookahBook — Документация: соглашения и навигация

## Структура папки docs/

```
docs/
├── PRD-HookahBook-MVP.md          # Product Requirements Document
├── TECH-STACK.md                  # Выбор технологий и обоснование
├── DESIGN-BRIEF.md                # UX-флоу, дизайн-система, макеты ASCII
├── PHASE1-TICKETS.md              # Инженерные тикеты Фазы 1, прогресс, AC
├── ROADMAP.md                     # Высокоуровневый роадмап по фазам
└── features/                      # Детальные спеки фич (по одной на файл)
    └── PHASE-3-T110-notifications.md
```

## Соглашения по спецификациям фич

Каждый файл в `docs/features/` описывает одну крупную фичу (или связанный кластер тикетов) и должен содержать:

1. **Заголовок и мета** — Phase, Status, Dependencies, Date
2. **Overview** — проблема и решение в 2–3 предложениях
3. **User Stories** — `US-XXX-N: Как <роль>, я хочу <действие>, чтобы <результат>`
4. **Functional Requirements** — `FR-XXX-NN` с точными критериями
5. **Non-Functional Requirements** — `NFR-XXX-NN` (производительность, безопасность, надёжность)
6. **Database Changes** — SQL и SQLAlchemy модели
7. **API Endpoints** — метод, путь, Auth, Request/Response JSON, ошибки
8. **Frontend Components** — имя файла, пропсы, логика, состояния UI
9. **Integration Points** — таблица изменяемых файлов + список новых файлов
10. **Acceptance Criteria** — чеклист `- [ ]` для проверки
11. **Engineering Tickets** — таблица тикетов с оценкой (S/M/L) и зависимостями
12. **Open Questions** — вопросы с пометкой `**Решено:**` после закрытия

## Именование файлов спек

```
docs/features/PHASE-{N}-T{ticket}-{kebab-name}.md

Примеры:
  PHASE-3-T110-notifications.md
  PHASE-2-T090-hookah-constructor.md
  PHASE-2-T080-guest-auth.md
```

## Статусы тикетов

| Символ | Значение |
|--------|---------|
| ✅ | Завершено и смёрджено в main |
| 🔄 | В работе (есть открытый PR) |
| ⬜ | Не начато |
| 🔒 | Заблокировано зависимостями |

## Правило Open Questions

Все открытые вопросы (`Open Questions`) в спецификации **должны быть закрыты** перед стартом разработки тикета. Ответ фиксируется в том же файле с пометкой `**Решено: ...**` — в рамках PR с реализацией.

## Деплой-специфика (RPi5)

- **Хранилище**: SSD для всех Docker-томов, БД и логов. SD-карта — только для загрузки ОС.
- **Воркеры**: `--workers 1` (Uvicorn) — важно для APScheduler (cron без дублирования).
- **Архитектура**: ARM64 — убедиться, что все Docker-образы совместимы с `linux/arm64`.
