"""Samsung 32-bit IR encoder.

38 kHz carrier. Header is a 4500 µs pulse + 4500 µs space. Each bit is a
560 µs pulse followed by either a 560 µs (logical 0) or 1690 µs (logical 1)
space. End pulse 560 µs. Data is 32 bits, LSB first:

    address (8) | address (8) | command (8) | ~command (8)
"""

from __future__ import annotations

LEADER_PULSE = 4500
LEADER_SPACE = 4500
BIT_PULSE = 560
ZERO_SPACE = 560
ONE_SPACE = 1690
FRAME_GAP_US = 40_000


def encode_samsung32(*, address: int, command: int) -> list[int]:
    """Encode a Samsung 32-bit frame."""
    if not 0 <= address <= 0xFF:
        raise ValueError(f"Samsung address must fit in 8 bits, got {address!r}")
    if not 0 <= command <= 0xFF:
        raise ValueError(f"Samsung command must fit in 8 bits, got {command!r}")

    data = (
        (address & 0xFF)
        | ((address & 0xFF) << 8)
        | ((command & 0xFF) << 16)
        | (((~command) & 0xFF) << 24)
    )

    timings: list[int] = [LEADER_PULSE, -LEADER_SPACE]
    for i in range(32):
        bit = (data >> i) & 1
        timings.append(BIT_PULSE)
        timings.append(-ONE_SPACE if bit else -ZERO_SPACE)

    timings.append(BIT_PULSE)
    timings.append(-FRAME_GAP_US)
    return timings
