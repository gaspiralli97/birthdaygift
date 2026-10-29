"""Short, unambiguous card identifiers."""

import secrets

# No vowels, so an id cannot spell a word; no 0/1/l/o, so it survives being
# retyped by hand from a message.
_ALPHABET = "23456789bcdfghjkmnpqrstvwxyz"

# 27 symbols from a 28-character alphabet is ~129 bits.
#
# The length is set by the wrong-looking question, not the obvious one.
# Guessing one *particular* card is already hopeless at half this length. What
# matters is guessing *any* live card: with N cards alive the chance per
# request is N / 28**LENGTH, so a short id gets weaker exactly as the service
# gets more popular. At 129 bits that term stays negligible no matter how many
# cards exist, which is worth more than a tidy URL - and a card holds somebody
# else's name, age and a private memory.
_LENGTH = 27


def new_card_id() -> str:
    """A fresh id, drawn from a CSPRNG."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))


def is_card_id(value: str) -> bool:
    """Whether a string could be one of our ids, for rejecting junk early."""
    return len(value) == _LENGTH and all(char in _ALPHABET for char in value)
