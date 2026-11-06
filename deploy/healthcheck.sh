#!/usr/bin/env bash
# Checks that the service is actually serving and that the letter writer can
# still authenticate, and messages the operator on Telegram when it cannot.
#
# Run by birthdaygift-healthcheck.timer, every 15 minutes.
#
# Two failures are worth catching and they fail very differently. A dead site
# is obvious to anyone who looks. An expired CLI token is not: the bot keeps
# working, the card pages keep serving, and the only symptom is that every
# sender who asks for a written letter is quietly offered the "write it
# yourself" path instead. Nobody reports that, so it has to be watched for.
#
# Alerts are rate-limited to one per failing check per RENOTIFY_HOURS, because
# a check that runs every 15 minutes and notifies every time is a check that
# gets muted.

set -uo pipefail

ENV_FILE=${ENV_FILE:-/etc/birthdaygift/env}
STATE_DIR=${STATE_DIR:-/var/lib/birthdaygift/healthcheck}
RENOTIFY_HOURS=${RENOTIFY_HOURS:-12}
TIMEOUT=${TIMEOUT:-20}

[[ -r $ENV_FILE ]] || { echo "cannot read $ENV_FILE" >&2; exit 1; }
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

SITE_URL=${SITE_URL:-}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_OWNER_ID=${TELEGRAM_OWNER_ID:-}
CLAUDE_BIN=${CLAUDE_BIN:-claude}
CLAUDE_MODEL=${CLAUDE_MODEL:-sonnet}

mkdir -p "$STATE_DIR"

# Telegram's own API is the alert channel, so a message is sent with curl
# reading its arguments from stdin: the bot token would otherwise sit in argv
# for anyone running `ps`, which is the same reason the letter prompt does not
# go there either.
say() {
  local text=$1
  [[ -n $TELEGRAM_BOT_TOKEN && -n $TELEGRAM_OWNER_ID ]] || { echo "$text"; return; }
  printf 'url = "https://api.telegram.org/bot%s/sendMessage"\ndata-urlencode = "chat_id=%s"\ndata-urlencode = "text=%s"\n' \
    "$TELEGRAM_BOT_TOKEN" "$TELEGRAM_OWNER_ID" "$text" |
    curl -sS -m "$TIMEOUT" -K - -o /dev/null
}

# One alert per check per RENOTIFY_HOURS. Recovery clears the marker, so the
# next failure is reported immediately rather than waiting out the window.
report() {
  local check=$1 text=$2
  local marker="$STATE_DIR/$check.failing"
  if [[ -f $marker ]]; then
    local age=$(( ($(date +%s) - $(stat -c %Y "$marker" 2>/dev/null || echo 0)) / 3600 ))
    (( age < RENOTIFY_HOURS )) && return
  fi
  : > "$marker"
  say "birthdaygift: $text"
  echo "ALERT [$check] $text" >&2
}

recovered() {
  local check=$1
  local marker="$STATE_DIR/$check.failing"
  [[ -f $marker ]] || return
  rm -f "$marker"
  say "birthdaygift: $check is back."
  echo "RECOVERED [$check]" >&2
}

failures=0

# 1. The site answers, over the real URL rather than through the loopback, so
#    nginx and the certificate are covered as well as the application.
if [[ -n $SITE_URL ]]; then
  code=$(curl -sS -m "$TIMEOUT" -o /dev/null -w '%{http_code}' "$SITE_URL/healthz" || echo 000)
  if [[ $code == 200 ]]; then
    recovered site
  else
    report site "the site is not answering ($SITE_URL/healthz returned $code)."
    failures=$((failures + 1))
  fi
fi

# 2. The letter writer can authenticate. Asking for one word keeps this cheap
#    enough to run every quarter of an hour against a subscription.
if command -v "$CLAUDE_BIN" >/dev/null 2>&1 || [[ -x $CLAUDE_BIN ]]; then
  reply=$(printf 'Reply with exactly: OK' |
    timeout "$((TIMEOUT * 3))" "$CLAUDE_BIN" -p --model "$CLAUDE_MODEL" \
      --tools "" --restricted --permission-prompts none \
      --strict-mcp-config --setting-sources "" 2>&1)
  if [[ $reply == *OK* ]]; then
    recovered letters
  else
    report letters "the letter writer cannot authenticate, so every AI letter is falling back to \"write it yourself\". Run: claude setup-token, then put it in $ENV_FILE as CLAUDE_CODE_OAUTH_TOKEN. Last reply: ${reply:0:200}"
    failures=$((failures + 1))
  fi
else
  report letters "the Claude Code CLI is missing at $CLAUDE_BIN."
  failures=$((failures + 1))
fi

exit $(( failures > 0 ? 1 : 0 ))
