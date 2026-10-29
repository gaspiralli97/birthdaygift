"""Writing the letter.

The default provider assembles a letter from per-language sentence pools. The
pools live in code rather than the translation JSON because each line needs a
little logic - whether an age was given, whether there are details to quote -
and template strings in a data file cannot express that.

Picking is seeded by a hash of the card's own fields, so one person always gets
the same letter while two different people get different ones. That is what
keeps the free path from reading like a form letter.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from typing import Protocol

from .schemas import CardCreate

logger = logging.getLogger(__name__)

Line = Callable[[CardCreate], str]

_TERMINATORS = ".!?…。！？"


def _sentence(text: str) -> str:
    """Give free-form input a sentence ending, so quoting it reads cleanly."""
    text = text.strip()
    if not text or text[-1] in _TERMINATORS:
        return text
    return f"{text}."


class Provider(Protocol):
    """Anything that can turn card details into paragraphs."""

    name: str

    def write(self, card: CardCreate) -> list[str]: ...


# --------------------------------------------------------------------------
# Sentence pools
# --------------------------------------------------------------------------

_POOLS: dict[str, dict[str, list[Line]]] = {
    "uz": {
        "open": [
            lambda c: (
                f"{c.age} yosh. {c.name}, bugun kun sizning nomingizda."
                if c.age
                else f"Tug‘ilgan kun. {c.name}, bugun kun sizning nomingizda."
            ),
            lambda c: (
                f"{c.name}, tug‘ilgan kuningiz bilan."
                + (f" {c.age} — yaxshi raqam." if c.age else "")
            ),
            lambda c: (
                f"Bugun {c.name}ning tug‘ilgan kuni"
                + (f", {c.age} yosh" if c.age else "")
                + " — shuning uchun bu sahifa bor."
            ),
        ],
        "details": [
            lambda c: (
                f"Siz haqingizda shuni aytdilar: {_sentence(c.details)} "
                "Shunga o‘xshagan narsalar esda qoladi."
            ),
            lambda c: f"Bu yerda yozilgani: {_sentence(c.details)} Qo‘shimcha so‘z keraksiz.",
        ],
        "middle": [
            lambda _: (
                "Yillar o‘tadi, odam esa o‘zi bo‘lib qolaveradi. Siz haqingizda ham xuddi shunday."
            ),
            lambda _: "Bir yil yana ortda qoldi. Ortga qarasa — arzigulik ish ko‘p.",
            lambda _: "Tug‘ilgan kun — hisob-kitob kuni emas, shunchaki yaxshi kun.",
        ],
        "close": [
            lambda _: (
                "Mustahkam salomatlik, boshlagan ishlaringizda omad va "
                "ko‘p kulgili kunlar tilayman."
            ),
            lambda _: "Sog‘lik, xotirjamlik va o‘zingizga yoqadigan ish tilayman. Qolgani keladi.",
            lambda _: "Yangi yoshingiz oldingisidan yengilroq va qiziqroq bo‘lsin.",
        ],
    },
    "en": {
        "open": [
            lambda c: (
                f"{c.age} years. {c.name}, today the day is yours."
                if c.age
                else f"A birthday. {c.name}, today the day is yours."
            ),
            lambda c: (
                f"{c.name}, happy birthday." + (f" {c.age} is a good number." if c.age else "")
            ),
            lambda c: (
                f"It is {c.name}'s birthday"
                + (f", number {c.age}" if c.age else "")
                + " — which is why this page exists."
            ),
        ],
        "details": [
            lambda c: (
                f"Here is what was said about you: {_sentence(c.details)} "
                "Those are the things people remember."
            ),
            lambda c: f"What the card came with: {_sentence(c.details)} Not much to add to that.",
        ],
        "middle": [
            lambda _: "Years pass and a person stays themselves. That seems to be true of you.",
            lambda _: "Another year behind you. Looking back, plenty of it was worth doing.",
            lambda _: "A birthday is not an audit. It is just a good day.",
        ],
        "close": [
            lambda _: (
                "Strong health, luck in everything you start, and many days worth laughing about."
            ),
            lambda _: "Health, a quiet mind, and work you actually like. The rest tends to follow.",
            lambda _: "May this year be lighter than the last one and more interesting than both.",
        ],
    },
    "ko": {
        "open": [
            lambda c: (
                f"{c.age}세. {c.name}님, 오늘은 당신의 날입니다."
                if c.age
                else f"생일입니다. {c.name}님, 오늘은 당신의 날입니다."
            ),
            lambda c: (
                f"{c.name}님, 생일 축하합니다." + (f" {c.age}, 좋은 숫자네요." if c.age else "")
            ),
            lambda c: (
                f"오늘은 {c.name}님의 "
                + (f"{c.age}번째 " if c.age else "")
                + "생일입니다. 그래서 이 페이지가 있습니다."
            ),
        ],
        "details": [
            lambda c: (
                f"당신에 대해 이렇게 전해 왔습니다: {_sentence(c.details)} "
                "사람들이 기억하는 건 그런 것들이죠."
            ),
            lambda c: f"카드에 함께 적혀 온 말: {_sentence(c.details)} 더 보탤 말이 없습니다.",
        ],
        "middle": [
            lambda _: "세월은 흘러도 사람은 자기 자신으로 남습니다. 당신도 그런 것 같아요.",
            lambda _: "또 한 해를 보냈습니다. 돌아보면 해볼 만한 일이 많았죠.",
            lambda _: "생일은 결산하는 날이 아니라 그냥 좋은 날입니다.",
        ],
        "close": [
            lambda _: "건강과, 시작하시는 모든 일의 좋은 결과와, 웃을 일이 많은 날들을 바랍니다.",
            lambda _: (
                "건강, 편안한 마음, 그리고 정말 좋아하는 일이 함께하기를. 나머지는 따라옵니다."
            ),
            lambda _: "올해가 지난해보다 가볍고, 그 어느 해보다 재미있기를 바랍니다.",
        ],
    },
    "ru": {
        "open": [
            lambda c: (
                f"{c.age} лет. {c.name}, сегодня день твой."
                if c.age
                else f"День рождения. {c.name}, сегодня день твой."
            ),
            lambda c: (
                f"{c.name}, с днём рождения." + (f" {c.age} — хорошее число." if c.age else "")
            ),
            lambda c: (
                f"Сегодня у {c.name} день рождения"
                + (f", {c.age}-й" if c.age else "")
                + " — поэтому эта страница и существует."
            ),
        ],
        "details": [
            lambda c: (
                f"Вот что о тебе передали: {_sentence(c.details)} Именно такое и запоминается."
            ),
            lambda c: f"Что пришло вместе с открыткой: {_sentence(c.details)} Добавить тут нечего.",
        ],
        "middle": [
            lambda _: "Годы идут, а человек остаётся собой. Про тебя это, похоже, верно.",
            lambda _: "Ещё один год позади. Если оглянуться — многое стоило сделать.",
            lambda _: "День рождения — не отчёт. Просто хороший день.",
        ],
        "close": [
            lambda _: (
                "Крепкого здоровья, удачи во всём, что начинаешь, и много дней, "
                "о которых смешно вспоминать."
            ),
            lambda _: (
                "Здоровья, спокойной головы и работы, которая правда нравится. Остальное придёт."
            ),
            lambda _: "Пусть этот год будет легче прошлого и интереснее обоих.",
        ],
    },
}


def _seed(card: CardCreate) -> int:
    key = f"{card.name}|{card.age}|{card.from_name}|{card.lang}|{card.details}"
    digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


class TemplateProvider:
    """Builds a letter out of the pools above. No network, no key, no cost."""

    name = "template"

    def write(self, card: CardCreate) -> list[str]:
        pool = _POOLS.get(card.lang, _POOLS["uz"])
        seed = _seed(card)

        def pick(slot: str, shift: int) -> str:
            options = pool[slot]
            return options[(seed >> shift) % len(options)](card)

        middle = pick("details", 16) if card.details else pick("middle", 16)
        return [pick("open", 0), middle, pick("close", 32)]


_TEMPLATE = TemplateProvider()


def _provider() -> Provider:
    """The configured provider.

    Only the template provider ships. ``TEXT_PROVIDER=anthropic`` is accepted by
    the settings model so the switch exists, but no such provider is wired up
    yet; until one is, fall back rather than fail a request.
    """
    return _TEMPLATE


def write_letter(card: CardCreate) -> tuple[list[str], str]:
    """Paragraphs plus the name of whatever produced them.

    Never raises: a slightly generic card beats an error page on a birthday, so
    any provider failure falls back to the template.
    """
    provider = _provider()
    if provider is not _TEMPLATE:
        try:
            return provider.write(card), provider.name
        except Exception:
            logger.exception("text provider %r failed; falling back to template", provider.name)
    return _TEMPLATE.write(card), _TEMPLATE.name
