#!/usr/bin/env bash
# Provisions birthdaygift on a fresh Ubuntu 24.04 host (tested on OCI arm64).
# Idempotent: safe to re-run after a code change.
#
#   sudo bash deploy/setup.sh
#
# Afterwards, put the secrets in /etc/birthdaygift/env and restart the service.

set -euo pipefail

DOMAIN="${DOMAIN:-151-145-79-228.sslip.io}"
APP_DIR=/opt/birthdaygift
DATA_DIR=/var/lib/birthdaygift
ENV_DIR=/etc/birthdaygift
REPO="${REPO:-https://github.com/gaspiralli97/birthdaygift.git}"

say() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }

say "Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl git ca-certificates nginx certbot python3-certbot-nginx iptables-persistent

if ! command -v node >/dev/null || [[ "$(node -v | cut -c2- | cut -d. -f1)" -lt 20 ]]; then
  say "Node.js 22 (arm64)"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -qq nodejs
fi
node -v

say "Service user and directories"
id -u birthdaygift >/dev/null 2>&1 || useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin birthdaygift
mkdir -p "$APP_DIR" "$DATA_DIR" "$ENV_DIR"
chown -R birthdaygift:birthdaygift "$DATA_DIR"
chmod 750 "$ENV_DIR"

say "Code"
if [[ -d $APP_DIR/.git ]]; then
  git -C "$APP_DIR" fetch --quiet origin
  git -C "$APP_DIR" reset --hard --quiet origin/HEAD
else
  git clone --quiet "$REPO" "$APP_DIR"
fi
chown -R root:root "$APP_DIR"

if [[ ! -f $ENV_DIR/env ]]; then
  say "Writing $ENV_DIR/env with placeholders - fill in the secrets yourself"
  cat > "$ENV_DIR/env" <<ENVEOF
PORT=3000
PUBLIC_URL=https://$DOMAIN
DATA_DIR=$DATA_DIR
CARD_TTL_DAYS=5
AI_PROVIDER=none
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-opus-5
TELEGRAM_BOT_TOKEN=
RATE_PER_USER_PER_DAY=3
RATE_GLOBAL_PER_DAY=100
ENVEOF
  chmod 640 "$ENV_DIR/env"
  chown root:birthdaygift "$ENV_DIR/env"
fi

say "Firewall (local iptables; the OCI security list must allow 80/443 too)"
for port in 80 443; do
  iptables -C INPUT -p tcp -m state --state NEW -m tcp --dport "$port" -j ACCEPT 2>/dev/null ||
    iptables -I INPUT 6 -p tcp -m state --state NEW -m tcp --dport "$port" -j ACCEPT
done
netfilter-persistent save >/dev/null

say "nginx"
install -m 644 "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/birthdaygift
sed -i "s/151-145-79-228\.sslip\.io/$DOMAIN/g" /etc/nginx/sites-available/birthdaygift
ln -sf /etc/nginx/sites-available/birthdaygift /etc/nginx/sites-enabled/birthdaygift
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

say "systemd"
install -m 644 "$APP_DIR/deploy/birthdaygift.service" /etc/systemd/system/birthdaygift.service
systemctl daemon-reload
systemctl enable --now birthdaygift
sleep 2
systemctl is-active birthdaygift

say "TLS certificate"
if [[ ! -d /etc/letsencrypt/live/$DOMAIN ]]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect
else
  echo "certificate already present"
fi

say "Done"
echo "  https://$DOMAIN"
echo
echo "Next: put TELEGRAM_BOT_TOKEN in $ENV_DIR/env, then:"
echo "  sudo systemctl restart birthdaygift"
