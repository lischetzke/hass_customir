"""Philips RC6 Mode 0 encoder.

RC6 Mode 0 layout (21 bits total, transmitted MSB first):

    [leader 2666µs pulse + 889µs space]
    [start bit = 1]
    [3 mode bits = 0,0,0]
    [toggle bit (DOUBLE-WIDTH Manchester half-bits)]
    [8 address bits]
    [8 command bits]
    [signal-free time ≥ 2666µs]

Half-bit duration is 444 µs (the toggle bit's halves are 888 µs each).
Manchester here uses the IEEE convention: bit 1 = high→low (``+,-``);
bit 0 = low→high (``-,+``).
"""

from __future__ import annotations

HALF_BIT_US = 444
LEADER_PULSE = 2666
LEADER_SPACE = 889
TRAILER_US = 2666


def encode_rc6(*, address: int, command: int, toggle: int = 0) -> list[int]:
    """Encode an RC6 Mode 0 frame."""
    if not 0 <= address <= 0xFF:
        raise ValueError(f"RC6 address must fit in 8 bits, got {address!r}")
    if not 0 <= command <= 0xFF:
        raise ValueError(f"RC6 command must fit in 8 bits, got {command!r}")
    if toggle not in (0, 1):
        raise ValueError("toggle must be 0 or 1")

    pulses: list[int] = [LEADER_PULSE, -LEADER_SPACE]

    bits: list[tuple[int, int]] = [(1, HALF_BIT_US)]
    bits.extend([(0, HALF_BIT_US)] * 3)               # mode 000
    bits.append((toggle, HALF_BIT_US * 2))            # double-width toggle
    bits.extend((b, HALF_BIT_US) for b in _int_to_bits(address, 8))
    bits.extend((b, HALF_BIT_US) for b in _int_to_bits(command, 8))

    for bit, half in bits:
        if bit == 1:
            pulses.extend([half, -half])
        else:
            pulses.extend([-half, half])

    # Merge consecutive same-sign halves.
    merged: list[int] = []
    for value in pulses:
        if merged and (merged[-1] > 0) == (value > 0):
            merged[-1] += value
        else:
            merged.append(value)

    # Trailing signal-free gap.
    if merged[-1] > 0:
        merged.append(-TRAILER_US)
    else:
        merged[-1] -= TRAILER_US - HALF_BIT_US

    return merged


def _int_to_bits(value: int, width: int) -> list[int]:
    return [(value >> i) & 1 for i in range(width - 1, -1, -1)]
