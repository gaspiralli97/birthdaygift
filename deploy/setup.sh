#!/usr/bin/env bash
# Provisions birthdaygift on Ubuntu 24.04 (tested on an Oracle Cloud arm64 box).
# Idempotent: re-run it after a code change to deploy the new revision.
#
#   sudo bash deploy/setup.sh
#
# Afterwards, fill in the three secrets in /etc/birthdaygift/env and restart.

set -euo pipefail

DOMAIN="${DOMAIN:-151-145-79-228.sslip.io}"
APP_DIR=/opt/birthdaygift
DATA_DIR=/var/lib/birthdaygift
ENV_DIR=/etc/birthdaygift
RUN_USER="${RUN_USER:-ubuntu}"
REPO="${REPO:-https://github.com/gaspiralli97/birthdaygift.git}"

say() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
id -u "$RUN_USER" >/dev/null 2>&1 || { echo "no such user: $RUN_USER" >&2; exit 1; }

say "Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl git ca-certificates nginx certbot python3-certbot-nginx \
    iptables-persistent python3-venv \
    fonts-noto-cjk   # preview images draw Korean names; without this they are boxes

say "uv"
if ! sudo -u "$RUN_USER" test -x "/home/$RUN_USER/.local/bin/uv"; then
  sudo -u "$RUN_USER" bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi
sudo -u "$RUN_USER" /home/"$RUN_USER"/.local/bin/uv --version

say "Claude Code CLI"
# This writes the letters, so CLAUDE_BIN has to exist before the operator can
# authenticate it. The installer lands in ~/.local/bin/claude, which is where
# the env file points and what the unit's PATH already covers.
if ! sudo -u "$RUN_USER" test -x "/home/$RUN_USER/.local/bin/claude"; then
  sudo -u "$RUN_USER" bash -c 'curl -fsSL https://claude.ai/install.sh | bash'
fi
sudo -u "$RUN_USER" /home/"$RUN_USER"/.local/bin/claude --version

say "Directories"
mkdir -p "$APP_DIR" "$DATA_DIR" "$ENV_DIR"
chown -R "$RUN_USER:$RUN_USER" "$APP_DIR" "$DATA_DIR"
# The env file is root-owned and group-readable by the service user, so the
# directory has to be group-traversable by that same user or the file is
# unreachable: systemd reads EnvironmentFile as root and would not notice,
# but the migration step below runs as $RUN_USER and does.
chown root:"$RUN_USER" "$ENV_DIR"
chmod 750 "$ENV_DIR"

say "Code"
if [[ -d $APP_DIR/.git ]]; then
  sudo -u "$RUN_USER" git -C "$APP_DIR" fetch --quiet origin
  sudo -u "$RUN_USER" git -C "$APP_DIR" reset --hard --quiet origin/main
else
  sudo -u "$RUN_USER" git clone --quiet "$REPO" "$APP_DIR"
fi

say "Dependencies"
sudo -u "$RUN_USER" bash -lc "cd $APP_DIR && /home/$RUN_USER/.local/bin/uv sync --no-dev"

# An env file from before the Python rewrite names none of the settings the
# application now reads, so carrying it forward would boot the service with
# nothing configured. SITE_URL is the marker: it tells the two schemas apart.
# The file is moved aside rather than deleted, because it holds secrets.
if [[ -f $ENV_DIR/env ]] && ! grep -q '^SITE_URL=' "$ENV_DIR/env"; then
  carried=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' "$ENV_DIR/env" | head -1)
  mv "$ENV_DIR/env" "$ENV_DIR/env.superseded.$(date +%Y%m%d%H%M%S)"
  say "Superseded a pre-rewrite $ENV_DIR/env (kept alongside as .superseded.*)"
fi

if [[ ! -f $ENV_DIR/env ]]; then
  say "Writing $ENV_DIR/env — fill in the two secrets yourself"
  cat > "$ENV_DIR/env" <<ENVEOF
SITE_URL=https://$DOMAIN
DATABASE_PATH=$DATA_DIR/birthdaygift.db
CARD_TTL_DAYS=5

# The Claude Code CLI writes the letters. It authenticates with the
# subscription this user logged in with: run \`claude setup-token\` once.
CLAUDE_BIN=/home/$RUN_USER/.local/bin/claude
CLAUDE_MODEL=sonnet

# From @BotFather.
TELEGRAM_BOT_TOKEN=${carried:-}
# Telegram echoes this back on every webhook call and the endpoint refuses
# anything without it. Generated here: a human choosing it adds nothing.
TELEGRAM_WEBHOOK_SECRET=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')
# Your own Telegram id, where both usage reports are delivered.
TELEGRAM_OWNER_ID=

REPORT_EVERY=10
RATE_PER_USER_PER_DAY=5
RATE_GLOBAL_PER_DAY=60
ENVEOF
  chmod 640 "$ENV_DIR/env"
  chown root:"$RUN_USER" "$ENV_DIR/env"
fi

say "Database"
sudo -u "$RUN_USER" bash -lc \
  "cd $APP_DIR && set -a && . $ENV_DIR/env && set +a && /home/$RUN_USER/.local/bin/uv run alembic upgrade head"

say "Firewall (local iptables; the cloud security list must allow 80/443 too)"
# The chain ends in a catch-all REJECT, so the ACCEPTs have to go before it.
# Appending, or inserting at a fixed index, silently puts them after it.
reject_pos() {
  iptables -L INPUT --line-numbers -n |
    awk '$2 == "REJECT" || $2 == "DROP" { print $1; exit }'
}
for port in 80 443; do
  if ! iptables -C INPUT -p tcp -m state --state NEW -m tcp --dport "$port" -j ACCEPT 2>/dev/null; then
    pos=$(reject_pos)
    if [[ -n $pos ]]; then
      iptables -I INPUT "$pos" -p tcp -m state --state NEW -m tcp --dport "$port" -j ACCEPT
    else
      iptables -A INPUT -p tcp -m state --state NEW -m tcp --dport "$port" -j ACCEPT
    fi
  fi
done
netfilter-persistent save >/dev/null

say "nginx"
grep -q 'zone=cards' /etc/nginx/nginx.conf || \
  sed -i '/http {/a \    limit_req_zone $binary_remote_addr zone=cards:10m rate=10r/s;' /etc/nginx/nginx.conf
install -m 644 "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/birthdaygift
sed -i "s/151-145-79-228\.sslip\.io/$DOMAIN/g" /etc/nginx/sites-available/birthdaygift
ln -sf /etc/nginx/sites-available/birthdaygift /etc/nginx/sites-enabled/birthdaygift
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

say "systemd"
install -m 644 "$APP_DIR/deploy/birthdaygift.service" /etc/systemd/system/birthdaygift.service
sed -i "s/^User=ubuntu$/User=$RUN_USER/; s/^Group=ubuntu$/Group=$RUN_USER/" \
  /etc/systemd/system/birthdaygift.service
systemctl daemon-reload
systemctl enable birthdaygift
# restart, not `enable --now`: on a re-run the unit is already active and
# --now would leave the old revision serving, which is the one case this
# script exists for.
systemctl restart birthdaygift
sleep 3
systemctl is-active birthdaygift

say "TLS certificate"
if [[ ! -d /etc/letsencrypt/live/$DOMAIN ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect
else
  echo "certificate already present"
fi

say "Done"
echo "  https://$DOMAIN"
echo
echo "Still to do, by hand — both need a person, not a script:"
echo "  1. sudo -u $RUN_USER /home/$RUN_USER/.local/bin/claude setup-token"
echo "  2. put TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID into $ENV_DIR/env"
echo "  3. sudo systemctl restart birthdaygift"
