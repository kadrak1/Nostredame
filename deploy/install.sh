#!/usr/bin/env bash
# One-shot installation script for HookahBook on a fresh RPi5 (Raspberry Pi OS Lite 64-bit)
#
# Usage (as root or with sudo):
#   bash deploy/install.sh
#
# What it does:
#   1. Creates /opt/hookahbook with correct permissions
#   2. Installs ufw firewall rules (SSH + HTTP + HTTPS only)
#   3. Hardens SSH (disable password auth)
#   4. Installs the systemd service
#   5. Creates the daily backup cron job
#   6. Configures log-directory structure

set -euo pipefail

APP_DIR="/opt/hookahbook"
APP_USER="${SUDO_USER:-pi}"   # the non-root user running docker
LOG_DIR="/opt/hookahbook/logs"
BACKUP_DIR="/opt/hookahbook/backups"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

log() { echo "[install] $*"; }
die() { echo "[install] ERROR: $*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "Run as root: sudo bash deploy/install.sh"

# ── 1. Directory structure ────────────────────────────────────────────────────
log "Creating directory structure …"
mkdir -p "$APP_DIR" "$LOG_DIR/caddy" "$BACKUP_DIR"
cp -r "$REPO_ROOT"/. "$APP_DIR/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 750 "$APP_DIR"
chmod 700 "$BACKUP_DIR"   # backups contain DB snapshots

log "App deployed to $APP_DIR"

# ── 2. Firewall (ufw) ─────────────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
    log "Configuring ufw firewall …"
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp   comment "SSH"
    ufw allow 80/tcp   comment "HTTP (Caddy → HTTPS redirect)"
    ufw allow 443/tcp  comment "HTTPS"
    ufw --force enable
    log "Firewall active. Open ports: 22, 80, 443"
else
    log "WARNING: ufw not found — skipping firewall setup"
fi

# ── 3. SSH hardening ──────────────────────────────────────────────────────────
SSHD_CONF="/etc/ssh/sshd_config.d/99-hookahbook-hardening.conf"
if [[ ! -f "$SSHD_CONF" ]]; then
    log "Hardening SSH config → $SSHD_CONF"
    cat > "$SSHD_CONF" <<'EOF'
# HookahBook SSH hardening — applied by deploy/install.sh
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
MaxAuthTries 3
LoginGraceTime 20
EOF
    systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
    log "SSH hardened (password auth disabled)"
else
    log "SSH hardening already applied — skipping"
fi

# ── 4. systemd service ────────────────────────────────────────────────────────
log "Installing systemd service …"
cp "$SCRIPT_DIR/hookahbook.service" /etc/systemd/system/hookahbook.service
systemctl daemon-reload
systemctl enable hookahbook
log "Service installed and enabled (starts on boot)"

# ── 5. Daily backup cron ──────────────────────────────────────────────────────
CRON_FILE="/etc/cron.d/hookahbook-backup"
if [[ ! -f "$CRON_FILE" ]]; then
    log "Installing backup cron job …"
    cat > "$CRON_FILE" <<EOF
# HookahBook SQLite backup — daily at 03:00
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
DB_PATH=/opt/hookahbook/data/hookahbook.db
BACKUP_DIR=/opt/hookahbook/backups
RETAIN_DAYS=7
0 3 * * * root bash /opt/hookahbook/scripts/backup.sh >> /opt/hookahbook/logs/backup.log 2>&1
EOF
    chmod 644 "$CRON_FILE"
    log "Backup cron installed (daily 03:00, keeps 7 days)"
else
    log "Backup cron already exists — skipping"
fi

# ── 6. .env reminder ─────────────────────────────────────────────────────────
if [[ ! -f "$APP_DIR/.env" ]]; then
    log ""
    log "⚠  IMPORTANT: Copy and fill in the production environment file:"
    log "     cp $APP_DIR/.env.example $APP_DIR/.env"
    log "     nano $APP_DIR/.env"
    log ""
    log "   Required values:"
    log "     DOMAIN          — your public domain name"
    log "     JWT_SECRET_KEY  — run: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    log "     ENCRYPTION_KEY  — run: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
fi

log ""
log "Installation complete ✓"
log ""
log "Next steps:"
log "  1. Edit $APP_DIR/.env  (set DOMAIN, JWT_SECRET_KEY, ENCRYPTION_KEY)"
log "  2. sudo systemctl start hookahbook"
log "  3. sudo systemctl status hookahbook"
log "  4. curl -I https://\$DOMAIN/api/health"
