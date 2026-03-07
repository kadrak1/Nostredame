# Feature: Защита сервера RPi5

**Phase**: 1
**PRD Requirement**: —
**Status**: Planned
**Dependencies**: T-001 (Docker), T-003 (security headers)
**Date**: 2026-03-06

---

## 1. Overview / Обзор

HookahBook работает на Raspberry Pi 5 с прямым доступом из интернета. Без базовой защиты сервер уязвим для brute-force SSH, сканирования портов и эксплуатации необновлённых пакетов. Данный тикет закрывает последний пункт Фазы 1 — hardening серверной среды.

## 2. User Stories

- **US-41**: Как владелец, я хочу быть уверен, что мой сервер защищён от несанкционированного доступа, чтобы данные гостей и бизнеса были в безопасности.

## 3. Functional Requirements / Функциональные требования

### 3.1 Firewall (ufw)
- FR-041-01: Установить и включить `ufw`
- FR-041-02: Разрешить только порты: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- FR-041-03: Политика по умолчанию — deny incoming, allow outgoing
- FR-041-04: Логирование отклонённых подключений

### 3.2 SSH Hardening
- FR-041-05: Отключить парольный вход (`PasswordAuthentication no`)
- FR-041-06: Отключить root login (`PermitRootLogin no`)
- FR-041-07: Разрешить только аутентификацию по ключу (`PubkeyAuthentication yes`)
- FR-041-08: Изменить стандартный порт SSH (опционально, например 2222)
- FR-041-09: Ограничить количество попыток (`MaxAuthTries 3`)

### 3.3 fail2ban
- FR-041-10: Установить и настроить fail2ban для SSH
- FR-041-11: Параметры: `maxretry=5`, `bantime=3600` (1 час), `findtime=600` (10 мин)
- FR-041-12: Настроить jail для Caddy (HTTP brute-force) — опционально

### 3.4 Docker Security
- FR-041-13: Все контейнеры работают под non-root пользователем (уже реализовано в `backend/Dockerfile`: `USER appuser`)
- FR-041-14: Проверить, что frontend Dockerfile также использует non-root
- FR-041-15: Ограничить capabilities контейнеров через `docker-compose.yml` (`cap_drop: ALL`)
- FR-041-16: Read-only root filesystem для контейнеров где возможно (`read_only: true`)

### 3.5 Автоматические обновления
- FR-041-17: Установить `unattended-upgrades` для автоматических обновлений безопасности
- FR-041-18: Настроить автоматический перезапуск при необходимости (`Unattended-Upgrade::Automatic-Reboot "true"`)
- FR-041-19: Время перезагрузки: 04:00 (минимальная нагрузка)

### 3.6 Бэкапы БД
- FR-041-20: Cron-скрипт ежедневного бэкапа SQLite (`cp` + timestamp)
- FR-041-21: Хранить последние 7 дней бэкапов
- FR-041-22: Скрипт ротации — удалять бэкапы старше 7 дней

## 4. Non-Functional Requirements / Нефункциональные требования

- NFR-041-01: Скрипт hardening должен быть идемпотентным (повторный запуск безопасен)
- NFR-041-02: Все настройки задокументированы в README серверной части
- NFR-041-03: Время развёртывания hardening: < 10 минут

## 5. Database Changes / Изменения в БД

Нет изменений в БД.

## 6. API Endpoints

Нет новых endpoints.

## 7. Frontend Components / Компоненты

Нет изменений во фронтенде.

## 8. Скрипты и файлы

### 8.1 `scripts/harden-server.sh`
Основной скрипт hardening:
```bash
#!/bin/bash
# Идемпотентный скрипт защиты RPi5
# Запуск: sudo bash scripts/harden-server.sh

# 1. ufw
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw --force enable

# 2. SSH hardening
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config
systemctl restart sshd

# 3. fail2ban
apt-get install -y fail2ban
# Конфиг в scripts/jail.local

# 4. unattended-upgrades
apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades
```

### 8.2 `scripts/jail.local`
Конфигурация fail2ban:
```ini
[sshd]
enabled = true
port = ssh
filter = sshd
maxretry = 5
bantime = 3600
findtime = 600
```

### 8.3 `scripts/backup-db.sh`
Скрипт бэкапа SQLite:
```bash
#!/bin/bash
BACKUP_DIR="/home/pi/backups/hookahbook"
DB_FILE="/var/lib/docker/volumes/hookahbook_db-data/_data/hookahbook.db"
mkdir -p "$BACKUP_DIR"
cp "$DB_FILE" "$BACKUP_DIR/hookahbook_$(date +%Y%m%d_%H%M%S).db"
# Удалить бэкапы старше 7 дней
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete
```

### 8.4 Изменения в `docker-compose.yml`
Добавить security-опции для контейнеров:
```yaml
services:
  backend:
    # ... existing config ...
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

## 9. Integration Points / Точки интеграции

| Файл | Изменение |
|------|-----------|
| `docker-compose.yml` | Добавить `security_opt`, `cap_drop` для контейнеров |
| `Caddyfile.production` | Без изменений (security headers уже настроены) |
| `backend/Dockerfile` | Без изменений (non-root уже реализован) |
| `scripts/` | Новые файлы: `harden-server.sh`, `jail.local`, `backup-db.sh` |
| `crontab` | Добавить задание бэкапа: `0 3 * * * /path/to/backup-db.sh` |

## 10. Acceptance Criteria / Критерии приёмки

- [ ] AC-1: `nmap` снаружи видит только порты 80, 443, 22
- [ ] AC-2: Парольный SSH-вход отклоняется
- [ ] AC-3: fail2ban банит IP после 5 неудачных SSH-попыток
- [ ] AC-4: Docker-контейнеры работают под non-root (проверка: `docker exec <container> whoami`)
- [ ] AC-5: `unattended-upgrades` установлен и активен
- [ ] AC-6: Бэкап SQLite создаётся по расписанию, ротация работает
- [ ] AC-7: Скрипт `harden-server.sh` идемпотентен (повторный запуск не ломает систему)

## 11. Engineering Tickets / Тикеты

| Тикет | Название | Тип | Зависимости | Оценка |
|-------|----------|-----|-------------|--------|
| T-041 | Скрипт hardening: ufw + SSH + fail2ban + unattended-upgrades + Docker security + бэкапы | devops | T-001 | M |

## 12. Open Questions / Открытые вопросы

| # | Вопрос | Кто отвечает |
|---|--------|--------------|
| 1 | Менять ли стандартный SSH-порт (22 → 2222)? | Владелец |
| 2 | Нужен ли мониторинг (Prometheus/Grafana) на RPi5 или хватит логов? | Владелец |
| 3 | Куда отправлять алерты fail2ban — email или Telegram? | Владелец |
