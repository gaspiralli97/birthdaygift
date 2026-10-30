# birthdaygift

A Telegram bot that turns a few answers into a birthday card page. The bot
hands back a link; the recipient opens it, blows out one candle per year, the
*Happy Birthday* melody plays, and the letter appears. Five days later the
link is gone.

**Live:** https://151-145-79-228.sslip.io

---

## Why the card is a link and the bot is the only way to make one

Everybody this was built for is already on Telegram, so there is no web form.
That decision does most of the architectural work: the only internet-facing
surface is a card and its preview image, both read-only, and the part that
costs something to run sits behind a known Telegram account.

The card itself has to be a page rather than something sent into the chat, and
the reason is the expiry. An image or a video posted to a chat is permanent —
it is saved, forwarded, and entirely beyond the service. A link can actually
stop existing. A Telegram Mini App would expire too, but it is still a web
page behind a webview, and it stops working the moment someone forwards the
card to WhatsApp.

## How a card gets made

```
/start ─▶ language ─▶ colour ─▶ who writes the letter?
                                      │
             ┌────────────────────────┴───────────────────┐
             ▼                                            ▼
      "I will write it"                            "Let AI write it"
             │                                            │
             │                          name, age, relationship, field,
             │                          then one message about the person
             ▼                                            ▼
        the letter as typed              Claude Code CLI, as a subprocess
             └────────────────────────┬───────────────────┘
                                      ▼
                        a card row, expires_at = now + 5 days
                                      ▼
                     https://…/c/<27 characters of entropy>
```

## The letter

The thing that makes a birthday letter land is a sentence that *uses* a
detail rather than reciting it — "you solved the olympiad problems while the
rest of us were still reading the question" — and, better still, one that
connects two details the sender listed separately. A template can place a
detail next to a sentence; it cannot read the detail and build on it.

So the letter is written by a model, through the Claude Code CLI run as a
subprocess. That is also what makes the service free: the CLI authenticates
with the operator's own subscription rather than a metered key.

Three consequences shape `ai.py`:

- **The prompt goes in on stdin, not argv.** It carries a third party's name,
  age and private memories, and argv is readable by anyone who can run `ps`.
- **A failure is never fatal.** If the model cannot be reached the bot offers
  to let the sender write the letter instead, rather than discarding a
  half-finished conversation.
- **The sender's text is untrusted.** It reaches the prompt as data, and the
  prompt says so explicitly.

An earlier template-based engine is kept in [`reference/`](reference/) with a
note on why it was not good enough.

## The number on the card

Under the letter the card says one true thing about the age. This is the part
a template *can* be clever about, because it is computed rather than recalled,
so it never repeats: 28 is a perfect number and 30 is not.

Number theory is a lovely thing to say to a mathematician and a strange thing
to say to a nurse, so the person's field picks the lens:

| Field | At thirty |
|---|---|
| Maths | `30 = 2 × 3 × 5` — the product of the first three primes |
| Software | `30 = 0b11110 = 0x1E` |
| Medicine, sport | `1.1 billion` — roughly the heartbeats so far |
| Education | `175 million` — roughly the words spoken |
| Arts | `30` — that many springs, no two alike |
| Anything else | `28.2 billion km` — thirty laps around the sun |

The constants are honest averages (70 beats a minute, 16,000 spoken words a
day, a 940-million-km orbit) and the copy hedges accordingly.

## Design notes

- **Colourways.** Three, sampled from the [Baginy](https://baginy.kr)
  storefront rather than invented: near-black, burgundy, champagne. Contrast
  was checked against each background; the brand gold fails on the cream sheet
  at 2.07:1, so text there steps two stops darker.
- **Card ids are ~129 bits.** The length is set by the wrong-looking question.
  Guessing one particular card is hopeless at half this; guessing *any* live
  card gets easier as the service grows, and that term is what this makes
  negligible.
- **Cards delete themselves** on read once expired, and an hourly sweep
  catches the ones nobody opened. The usage log is a separate append-only
  table, because the weekly report has to see further back than the cards
  still alive.
- **The melody is synthesised to a WAV** and played through an `<audio>`
  element. An iPhone's ringer switch silences Web Audio outright; an `<audio>`
  element paired with `audioSession: "playback"` keeps playing.
- **Four languages** — Uzbek, English, Korean, Russian — validated against a
  Pydantic model at startup, so a typo in copy fails the boot rather than a
  render. Uzbek and Russian take their register from the relationship, which
  is the one mistake worse than a clumsy sentence.

## Running it locally

Needs Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn birthdaygift.main:app --reload
```

Without `TELEGRAM_BOT_TOKEN` the bot stays off and the card pages still
serve, which is the useful mode for working on the page.

```bash
uv run pytest        # 67 tests
uv run ruff check .
uv run mypy          # strict across the application
```

## Deploying

Ubuntu 24.04, arm64 or x86:

```bash
sudo DOMAIN=your-host.example bash deploy/setup.sh
```

It installs uv, nginx, certbot and a CJK font, provisions the service, opens
80/443 in the local firewall, issues a certificate and starts the unit. Three
things are left for a human, and the script says so when it finishes:
`claude setup-token`, the three secrets in `/etc/birthdaygift/env`, and a
restart. Secrets are never read from, or committed to, this repository.

On Oracle Cloud the VCN security list has to allow 80/443 as well; the host
firewall alone is not enough.

## Stack

Python 3.12 · FastAPI · Jinja2 · SQLAlchemy 2 with Alembic · SQLite in WAL
mode · aiogram 3 over a webhook · Pillow for the preview images · pytest ·
ruff · mypy · GitHub Actions · systemd behind nginx with Let's Encrypt.

No build step and no frontend framework: the page is a template, a stylesheet
and one script.

## Layout

```
src/birthdaygift/
  config.py      settings, read once from the environment
  models.py      cards, usage events, a small key-value table
  cards.py       create, read, expire
  ai.py          the prompt, and the CLI subprocess that answers it
  bot.py         the Telegram conversation
  facts.py       what is true about the age, and which lens suits the person
  og.py          preview images, picking a font per script
  usage.py       the record of who used it, and both reports
  scheduler.py   hourly upkeep and the weekly report
  routes/        card, preview image, landing page, webhook
deploy/          systemd unit, nginx vhost, provisioning script
reference/       the prototypes the design came from
```

## Licence

MIT
