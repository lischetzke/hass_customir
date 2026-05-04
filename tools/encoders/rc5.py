"""Philips RC5 / RC5x encoder.

RC5 is a Manchester-encoded 14-bit protocol at 36 kHz:

    [start1][start2][toggle][addr5][cmd6]

Half-bit duration is 889 µs. A logical 0 transitions high→low at the bit
boundary (so encoded as ``+889, -889``) and a logical 1 transitions low→high
(``-889, +889``). Consecutive same-direction transitions merge.
"""

from __future__ import annotations

HALF_BIT_US = 889
FRAME_GAP_US = 89_000  # rest after a frame so totalframe ~114 ms


def encode_rc5(*, address: int, command: int, toggle: int = 0) -> list[int]:
    """Encode an RC5 frame.

    ``command`` may be 0..127 (the high bit becomes the inverted second start
    bit, giving RC5x's 7-bit command space). ``address`` is 0..31.
    """
    if not 0 <= address <= 0x1F:
        raise ValueError(f"RC5 address must fit in 5 bits, got {address!r}")
    if not 0 <= command <= 0x7F:
        raise ValueError(f"RC5 command must fit in 7 bits, got {command!r}")
    if toggle not in (0, 1):
        raise ValueError("toggle must be 0 or 1")

    start1 = 1
    start2 = 0 if (command & 0x40) else 1  # RC5x uses inverted high cmd bit
    bits: list[int] = [
        start1,
        start2,
        toggle,
        *_int_to_bits(address, 5),
        *_int_to_bits(command & 0x3F, 6),
    ]

    # Manchester: 0 -> +,-  1 -> -,+
    pulses: list[int] = []
    for bit in bits:
        if bit == 0:
            pulses.extend([HALF_BIT_US, -HALF_BIT_US])
        else:
            pulses.extend([-HALF_BIT_US, HALF_BIT_US])

    # Merge consecutive same-sign halves (e.g. -,- becomes one -1778).
    merged: list[int] = []
    for value in pulses:
        if merged and (merged[-1] > 0) == (value > 0):
            merged[-1] += value
        else:
            merged.append(value)

    # RC5 frames must start with a pulse (the first start bit forces this).
    if merged[0] < 0:
        # Should never happen given start1=1's encoding; defensive.
        merged = [HALF_BIT_US, *merged]

    # Trailing frame gap so a follow-up frame is well separated.
    if merged[-1] > 0:
        merged.append(-FRAME_GAP_US)
    else:
        merged[-1] -= FRAME_GAP_US - HALF_BIT_US

    return merged


def _int_to_bits(value: int, width: int) -> list[int]:
    return [(value >> i) & 1 for i in range(width - 1, -1, -1)]
