"""Pronto-hex → raw-timings decoder.

Pronto format (learned codes, prefix 0000):

    0000 FFFF B1 B2  d1 d1 ... d1 d1  d2 d2 ... d2 d2

* word 0: ``0000`` → modulated learned code.
* word 1: carrier frequency code; ``f_hz = 1_000_000 / (FFFF * 0.241246)``.
* word 2: number of pulse pairs in the once-burst.
* word 3: number of pulse pairs in the repeat-burst.
* remaining words: alternating on/off counts measured in carrier cycles.

We expand only the once-burst (matching how most upstream DBs publish single
press codes) and ignore the repeat block; if you need repeats, set
``repeat_count`` on the resulting :class:`infrared_protocols.Command` instead.
"""

from __future__ import annotations


def encode_pronto(hex_str: str) -> tuple[list[int], int]:
    """Decode a Pronto hex string. Returns ``(timings_us, modulation_hz)``."""
    words = [int(token, 16) for token in hex_str.split() if token]
    if len(words) < 4:
        raise ValueError("Pronto hex must contain at least 4 words")
    if words[0] != 0x0000:
        raise ValueError("Only learned (preamble 0000) Pronto codes are supported")

    freq_word = words[1]
    if freq_word == 0:
        raise ValueError("Pronto carrier frequency word is zero")
    period_us = freq_word * 0.241246
    modulation_hz = round(1_000_000 / period_us)

    once_pairs = words[2]
    repeat_pairs = words[3]
    expected = 4 + 2 * (once_pairs + repeat_pairs)
    if len(words) < expected:
        raise ValueError(
            f"Pronto data truncated: expected {expected} words, got {len(words)}"
        )

    # Use the once-burst when present, otherwise fall back to the repeat-burst.
    if once_pairs:
        pair_words = words[4 : 4 + 2 * once_pairs]
    else:
        pair_words = words[4 + 2 * once_pairs : 4 + 2 * (once_pairs + repeat_pairs)]

    timings: list[int] = []
    for i, count in enumerate(pair_words):
        us = round(count * period_us)
        if us == 0:
            us = 1
        timings.append(us if i % 2 == 0 else -us)

    return timings, modulation_hz
