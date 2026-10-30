"""The Telegram bot, which is the only way to make a card.

Everyone this is for is already on Telegram, so there is no web form: the
conversation here is the whole creation path. That is also what keeps the
public side read-only and the letter-writing behind a known Telegram account.

The flow is deliberately mostly taps - language, colour, who writes the letter,
the relationship, the field of work - with free text asked for only twice: the
person's name, and either the letter itself or everything the sender wants the
model to know.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)

from . import ai, cards, usage
from .config import get_settings
from .db import session_scope
from .facts import WORK_FIELDS
from .i18n import LANGUAGES, strings
from .schemas import RELATIONS, CardCreate
from .themes import THEME_KEYS

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"uz": "O‘zbekcha", "en": "English", "ko": "한국어", "ru": "Русский"}

#: Copy before a language is chosen has to be in some language; Uzbek is the
#: one the people this was built for share.
BOOTSTRAP_LANG = "uz"

MIN_LETTER_CHARS = 20
MIN_BRIEF_CHARS = 25


class Flow(StatesGroup):
    lang = State()
    theme = State()
    mode = State()
    name = State()
    age = State()
    relation = State()
    field = State()
    text = State()
    from_name = State()


def _rows(
    options: Sequence[tuple[str, str]], prefix: str, per_row: int = 2
) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"{prefix}:{value}")
        for value, label in options
    ]
    rows = [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _lang_keyboard() -> InlineKeyboardMarkup:
    return _rows([(code, LANGUAGE_NAMES[code]) for code in LANGUAGES], "lang")


def _theme_keyboard(lang: str) -> InlineKeyboardMarkup:
    names = strings(lang).themes
    return _rows([(key, names[key]) for key in THEME_KEYS], "theme", per_row=3)


def _mode_keyboard(lang: str) -> InlineKeyboardMarkup:
    copy = strings(lang).bot
    return _rows([("self", copy.mode_self), ("ai", copy.mode_ai)], "mode", per_row=1)


def _relation_keyboard(lang: str) -> InlineKeyboardMarkup:
    names = strings(lang).relations
    return _rows([(key, names[key]) for key in RELATIONS], "rel")


def _field_keyboard(lang: str) -> InlineKeyboardMarkup:
    names = strings(lang).fields
    return _rows([(key, names[key]) for key in WORK_FIELDS], "field")


async def _copy(state: FSMContext):  # type: ignore[no-untyped-def]
    data = await state.get_data()
    return strings(data.get("lang", BOOTSTRAP_LANG)).bot


dispatcher = Dispatcher(storage=MemoryStorage())


# --------------------------------------------------------------------------
# Entry and exit
# --------------------------------------------------------------------------


@dispatcher.message(CommandStart())
async def on_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Flow.lang)
    copy = strings(BOOTSTRAP_LANG).bot
    await message.answer(copy.start)
    await message.answer(copy.ask_lang, reply_markup=_lang_keyboard())


@dispatcher.message(Command("cancel"))
async def on_cancel(message: Message, state: FSMContext) -> None:
    copy = await _copy(state)
    await state.clear()
    await message.answer(copy.cancelled)


# --------------------------------------------------------------------------
# Taps
# --------------------------------------------------------------------------


@dispatcher.callback_query(Flow.lang, F.data.startswith("lang:"))
async def on_lang(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    lang = (query.data or "").split(":", 1)[1]
    await state.update_data(lang=lang if lang in LANGUAGES else BOOTSTRAP_LANG)
    copy = await _copy(state)
    await state.set_state(Flow.theme)
    if query.message:
        await query.message.answer(copy.ask_theme, reply_markup=_theme_keyboard(lang))


@dispatcher.callback_query(Flow.theme, F.data.startswith("theme:"))
async def on_theme(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(theme=(query.data or "").split(":", 1)[1])
    data = await state.get_data()
    copy = await _copy(state)
    await state.set_state(Flow.mode)
    if query.message:
        await query.message.answer(copy.ask_mode, reply_markup=_mode_keyboard(data["lang"]))


@dispatcher.callback_query(Flow.mode, F.data.startswith("mode:"))
async def on_mode(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(mode=(query.data or "").split(":", 1)[1])
    copy = await _copy(state)
    await state.set_state(Flow.name)
    if query.message:
        await query.message.answer(copy.ask_name)


@dispatcher.callback_query(Flow.relation, F.data.startswith("rel:"))
async def on_relation(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(relation=(query.data or "").split(":", 1)[1])
    data = await state.get_data()
    copy = await _copy(state)
    await state.set_state(Flow.field)
    if query.message:
        await query.message.answer(copy.ask_field, reply_markup=_field_keyboard(data["lang"]))


@dispatcher.callback_query(Flow.field, F.data.startswith("field:"))
async def on_field(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.update_data(field=(query.data or "").split(":", 1)[1])
    data = await state.get_data()
    copy = await _copy(state)
    await state.set_state(Flow.text)
    if query.message:
        await query.message.answer(copy.ask_brief if data.get("mode") == "ai" else copy.ask_letter)


# --------------------------------------------------------------------------
# Typing
# --------------------------------------------------------------------------


@dispatcher.message(Flow.name, F.text)
async def on_name(message: Message, state: FSMContext) -> None:
    copy = await _copy(state)
    name = (message.text or "").strip()
    if len(name.replace(" ", "")) < 2:
        await message.answer(copy.bad_name)
        return
    await state.update_data(name=name[:40])
    await state.set_state(Flow.age)
    await message.answer(copy.ask_age)


@dispatcher.message(Flow.age, F.text)
async def on_age(message: Message, state: FSMContext) -> None:
    copy = await _copy(state)
    text = (message.text or "").strip()
    if text != "/skip":
        try:
            age = int(text)
        except ValueError:
            await message.answer(copy.bad_age)
            return
        if not 1 <= age <= 129:
            await message.answer(copy.bad_age)
            return
        await state.update_data(age=age)
    data = await state.get_data()
    await state.set_state(Flow.relation)
    await message.answer(copy.ask_relation, reply_markup=_relation_keyboard(data["lang"]))


@dispatcher.message(Flow.text, F.text)
async def on_text(message: Message, state: FSMContext) -> None:
    copy = await _copy(state)
    data = await state.get_data()
    text = (message.text or "").strip()
    floor = MIN_BRIEF_CHARS if data.get("mode") == "ai" else MIN_LETTER_CHARS
    if len(text) < floor:
        await message.answer(copy.bad_text)
        return
    await state.update_data(text=text[:2000])
    await state.set_state(Flow.from_name)
    await message.answer(copy.ask_from)


@dispatcher.message(Flow.from_name, F.text)
async def on_from(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text != "/skip":
        await state.update_data(from_name=text[:40])
    await _finish(message, state)


@dispatcher.message()
async def on_stray(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer(strings(BOOTSTRAP_LANG).bot.unknown)


# --------------------------------------------------------------------------
# Finishing
# --------------------------------------------------------------------------


def _paragraphs(text: str) -> list[str]:
    parts = [" ".join(block.split()) for block in text.split("\n\n")]
    parts = [part for part in parts if part]
    return parts or [" ".join(text.split())]


async def _write_letter(data: dict[str, object]) -> tuple[list[str], str] | None:
    """The letter and where it came from, or ``None`` if the model was needed
    and could not be reached."""
    text = str(data.get("text", ""))
    if data.get("mode") != "ai":
        return _paragraphs(text), "self"

    brief = ai.Brief(
        lang=str(data.get("lang", BOOTSTRAP_LANG)),
        name=str(data.get("name", "")),
        age=data.get("age"),  # type: ignore[arg-type]
        relation=str(data.get("relation", "friend")),
        from_name=str(data.get("from_name", "")),
        extra=text,
    )
    paragraphs = await ai.write_letter(brief)
    return (paragraphs, "ai") if paragraphs else None


async def _finish(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    data = await state.get_data()
    copy = await _copy(state)

    if data.get("mode") == "ai":
        await message.answer(copy.working)

    written = await _write_letter(data)
    if written is None:
        # The model is the only thing that failed; the sender's own words
        # still work, so offer that rather than throwing the session away.
        await state.set_state(Flow.text)
        await state.update_data(mode="self")
        await message.answer(copy.ai_failed)
        await message.answer(copy.ask_letter)
        return

    paragraphs, source = written
    try:
        payload = CardCreate.model_validate(
            {
                "name": data.get("name", ""),
                "age": data.get("age"),
                "relation": data.get("relation", "friend"),
                "field": data.get("field", "other"),
                "lang": data.get("lang", BOOTSTRAP_LANG),
                "theme": data.get("theme", "qora"),
                "from_name": data.get("from_name", ""),
            }
        )
        with session_scope() as session:
            card = cards.create(session, payload, paragraphs, source)
            event_count = _record_usage(session, card, message)
    except Exception:
        logger.exception("could not save a card")
        await state.clear()
        await message.answer(copy.failed)
        return

    await state.clear()
    url = settings.card_url(card.id)
    await message.answer(f"{copy.done}\n\n{url}")
    await message.answer(f"<i>{copy.expiry.format(days=settings.card_ttl_days)}</i>\n{copy.again}")

    if event_count:
        await _maybe_report(message.bot)


def _record_usage(session, card, message: Message) -> int:  # type: ignore[no-untyped-def]
    user = message.from_user
    handle = ""
    if user is not None:
        handle = f"@{user.username}" if user.username else (user.full_name or "")
    usage.record(session, card, user.id if user else 0, handle[:80])
    return len(usage.pending_batch(session))


async def _maybe_report(bot: Bot | None) -> None:
    """Send the digest once ten cards have gone unreported."""
    settings = get_settings()
    if bot is None or not settings.telegram_owner_id:
        return
    with session_scope() as session:
        pending = usage.pending_batch(session)
        if len(pending) < settings.report_every:
            return
        batch = list(pending[: settings.report_every])
        text = usage.batch_report(batch)
        usage.mark_reported(session, batch, "in_batch_report")
    try:
        await bot.send_message(settings.telegram_owner_id, text)
    except Exception:
        logger.exception("could not deliver the batch report")


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------

_bot: Bot | None = None


def get_bot() -> Bot | None:
    return _bot


async def start_bot(app) -> str | None:  # type: ignore[no-untyped-def]
    """Register the webhook and return the bot's username."""
    global _bot
    settings = get_settings()
    _bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    me = await _bot.get_me()
    await _bot.set_webhook(
        f"{settings.site_url}/telegram/{settings.telegram_webhook_secret}",
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )
    logger.info("telegram webhook registered for @%s", me.username)
    app.state.bot_username = me.username
    return me.username


async def stop_bot(app) -> None:  # type: ignore[no-untyped-def]
    global _bot
    if _bot is not None:
        await _bot.session.close()
        _bot = None


async def handle_update(payload: dict[str, object]) -> None:
    """Feed one webhook body through the dispatcher."""
    if _bot is None:
        return
    await dispatcher.feed_update(_bot, Update.model_validate(payload, context={"bot": _bot}))
