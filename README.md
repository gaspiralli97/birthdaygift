# birthdaygift

A Telegram bot that turns a few answers into a personal, animated birthday card
page. The bot hands back a link; the link opens anywhere; five days later it is
gone.

**Live:** https://151-145-79-228.sslip.io

---

## Why a link and not just a message

The card is interactive — one candle per year, tap to blow them out, confetti,
and the *Happy Birthday* melody synthesised in the browser. A chat bubble cannot
render that, and the two alternatives both fail a requirement:

| | Image / video in chat | Telegram Mini App | **Link to a page** |
|---|---|---|---|
| Interactive | no | yes | **yes** |
| Opens outside Telegram | no | no | **yes** |
| Can actually expire | no — a sent file is permanent | yes | **yes** |
| Needs a web server | no | yes (a Mini App *is* a web page) | yes |

A Mini App does not avoid the server, it only hides the browser — and it stops
working the moment someone forwards the card to WhatsApp. So: Telegram for
input, a plain `https://` link for the card.

## How it works

```
Telegram ──getUpdates──▶ bot (long polling)
                            │  5 questions: language, name, age,
                            │  relationship, details, sender
                            ▼
                    text layer  ──▶  template (default, free)
                            │        └─ or Claude, via one env var
                            ▼
                    JSON file in DATA_DIR, expires_at = now + 5 days
                            │
   visitor ──https──▶ nginx ──▶ node ──▶ rendered HTML page
```

Long polling means Telegram never needs to reach the host, so the only inbound
port is the one serving the card pages. Expired cards are dropped on read and
swept hourly, so storage self-cleans with no cron job.

## Design notes

- **No runtime dependencies.** The template path imports nothing outside Node's
  standard library. `@anthropic-ai/sdk` is imported lazily and only when
  `AI_PROVIDER=anthropic`, so the default install has an empty `node_modules`.
- **Swappable text layer.** `src/ai.js` exposes one function, `writeLetter`.
  Any provider failure falls back to the template — a slightly generic card
  beats an error page on someone's birthday.
- **Varied templates.** Sentences are drawn from per-language pools using a hash
  of the card's own fields, so two people get different letters while one card
  always renders the same text.
- **Untrusted input throughout.** The details field is public input that lands in
  both a prompt and an HTML page: it is length-capped, HTML-escaped on render,
  and the system prompt tells the model to treat it as data. Card ids are
  validated against a strict pattern before touching the filesystem.
- **Abuse limits.** Three cards per Telegram user per day and a global daily cap,
  because generation can cost the operator money.
- **One process, one unit.** HTTP server and bot share a process, a data
  directory and a systemd unit.

## Running locally

Needs Node 20+. No install step.

```bash
cp .env.example .env     # defaults are fine; the bot stays off without a token
npm start                # http://localhost:3000
```

Without `TELEGRAM_BOT_TOKEN` the bot is disabled and the card pages still serve,
which is the useful mode for working on the page itself.

## Deploying

Ubuntu 24.04, arm64 or x86:

```bash
sudo DOMAIN=your-host.example bash deploy/setup.sh
```

The script installs Node, nginx and certbot, creates a locked-down service
user, opens 80/443 in the local firewall, issues a Let's Encrypt certificate and
starts the unit. It writes `/etc/birthdaygift/env` with **empty** secret values
on first run — fill those in yourself, then `systemctl restart birthdaygift`.
Secrets are never read from, or committed to, this repository.

On Oracle Cloud the VCN security list must allow 80/443 as well; the host
firewall alone is not enough.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `3000` | loopback port the Node process binds |
| `PUBLIC_URL` | `http://localhost:3000` | origin used to build card links |
| `DATA_DIR` | `./data` | where card JSON lives |
| `CARD_TTL_DAYS` | `5` | how long a link survives |
| `AI_PROVIDER` | `none` | `none` (template) or `anthropic` |
| `ANTHROPIC_API_KEY` | — | required only for `anthropic` |
| `ANTHROPIC_MODEL` | `claude-opus-5` | model id |
| `TELEGRAM_BOT_TOKEN` | — | empty disables the bot |
| `RATE_PER_USER_PER_DAY` | `3` | per-Telegram-user daily cap |
| `RATE_GLOBAL_PER_DAY` | `100` | service-wide daily cap |

## Cost

Zero as configured: the template writes the text, Oracle's always-free tier
hosts it, `sslip.io` supplies the hostname and Let's Encrypt the certificate.
Setting `AI_PROVIDER=anthropic` is the only switch that spends money.

## Layout

```
src/config.js    environment loading
src/store.js     card files, expiry, rate limits
src/ai.js        writeLetter() - template and Claude providers
src/strings.js   page copy in uz / en / ko / ru
src/card.js      HTML renderer (card and expired pages)
src/bot.js       Telegram long-polling conversation
src/server.js    HTTP routes, hourly sweep, graceful shutdown
deploy/          systemd unit, nginx vhost, setup script
```

## License

MIT
