#!/usr/bin/env bash
# SQLite hot-backup for HookahBook (RPi5 production)
#
# Run via cron (root crontab on the host, or inside a Docker sidecar):
#   0 3 * * * /opt/hookahbook/scripts/backup.sh >> /opt/hookahbook/logs/backup.log 2>&1
#
# Environment variables (can be overridden):
#   DB_PATH       — path to the live database file
#   BACKUP_DIR    — destination directory for backups
#   RETAIN_DAYS   — how many days to keep old backups (default: 7)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH="${DB_PATH:-/opt/hookahbook/data/hookahbook.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/hookahbook/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
BACKUP_FILE="${BACKUP_DIR}/hookahbook_${TIMESTAMP}.db"
LOG_PREFIX="[backup][${TIMESTAMP}]"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo "${LOG_PREFIX} $*"; }
die()  { echo "${LOG_PREFIX} ERROR: $*" >&2; exit 1; }

# ── Pre-flight ────────────────────────────────────────────────────────────────
[[ -f "$DB_PATH" ]]  || die "DB not found: ${DB_PATH}"
mkdir -p "$BACKUP_DIR" || die "Cannot create backup dir: ${BACKUP_DIR}"

# ── Hot-backup via sqlite3 .backup command ────────────────────────────────────
# sqlite3 .backup acquires a shared lock and copies while the DB is live.
# This is safer than `cp` which can capture a torn write.
log "Starting backup → ${BACKUP_FILE}"
sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'" \
  || die "sqlite3 .backup failed"

# ── Integrity check on the copy ───────────────────────────────────────────────
log "Running integrity check …"
INTEGRITY="$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;")"
if [[ "$INTEGRITY" != "ok" ]]; then
    die "Integrity check FAILED for ${BACKUP_FILE}: ${INTEGRITY}"
fi
log "Integrity check passed"

# ── Size reporting ────────────────────────────────────────────────────────────
SIZE="$(du -sh "$BACKUP_FILE" | cut -f1)"
log "Backup size: ${SIZE}"

# ── Retention: remove backups older than RETAIN_DAYS ─────────────────────────
log "Pruning backups older than ${RETAIN_DAYS} days …"
PRUNED=0
while IFS= read -r old_file; do
    rm -f "$old_file"
    log "Deleted old backup: $(basename "$old_file")"
    (( PRUNED++ )) || true
done < <(find "$BACKUP_DIR" -name "hookahbook_*.db" -mtime "+${RETAIN_DAYS}" -type f)
log "Pruned ${PRUNED} old backup(s)"

# ── Disk-space warning ────────────────────────────────────────────────────────
AVAIL_KB="$(df -k "$BACKUP_DIR" | awk 'NR==2 {print $4}')"
AVAIL_MB=$(( AVAIL_KB / 1024 ))
if (( AVAIL_MB < 200 )); then
    log "WARNING: Only ${AVAIL_MB} MB free in ${BACKUP_DIR} — consider expanding storage"
fi

log "Backup complete ✓"
