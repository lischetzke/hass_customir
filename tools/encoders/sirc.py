"""Sony SIRC (12/15/20-bit) IR encoder.

40 kHz carrier. Header is a 2400 µs pulse + 600 µs space. Each bit is a
600 µs space preceded by either a 600 µs (logical 0) or 1200 µs (logical 1)
pulse. Frame total ≈ 45 ms.

Bits are transmitted LSB first within each field. The 20-bit variant
includes a 5-bit "extended" device number after the 7-bit command and 5-bit
address.
"""

from __future__ import annotations

HEADER_PULSE = 2400
HEADER_SPACE = 600
ZERO_PULSE = 600
ONE_PULSE = 1200
BIT_SPACE = 600
FRAME_GAP_US = 25_000


def encode_sirc(
    *,
    address: int,
    command: int,
    bits: int = 12,
    extended: int = 0,
) -> list[int]:
    """Encode a Sony SIRC frame.

    bits: 12 (7-bit cmd + 5-bit addr), 15 (7+8) or 20 (7+5+8 extended).
    """
    if bits not in (12, 15, 20):
        raise ValueError("Sony SIRC bits must be 12, 15 or 20")
    if not 0 <= command <= 0x7F:
        raise ValueError(f"SIRC command must fit in 7 bits, got {command!r}")

    if bits == 12:
        if not 0 <= address <= 0x1F:
            raise ValueError("SIRC12 address must fit in 5 bits")
        payload = [
            *_int_to_bits_lsb(command, 7),
            *_int_to_bits_lsb(address, 5),
        ]
    elif bits == 15:
        if not 0 <= address <= 0xFF:
            raise ValueError("SIRC15 address must fit in 8 bits")
        payload = [
            *_int_to_bits_lsb(command, 7),
            *_int_to_bits_lsb(address, 8),
        ]
    else:  # 20
        if not 0 <= address <= 0x1F:
            raise ValueError("SIRC20 address must fit in 5 bits")
        if not 0 <= max(extended, 0) <= 0xFF:
            raise ValueError("SIRC20 extended must fit in 8 bits")
        payload = [
            *_int_to_bits_lsb(command, 7),
            *_int_to_bits_lsb(address, 5),
            *_int_to_bits_lsb(max(extended, 0), 8),
        ]

    pulses: list[int] = [HEADER_PULSE, -HEADER_SPACE]
    for bit in payload:
        pulses.append(ONE_PULSE if bit else ZERO_PULSE)
        pulses.append(-BIT_SPACE)

    # Replace the last bit-space with a long frame gap.
    pulses[-1] = -FRAME_GAP_US
    return pulses


def _int_to_bits_lsb(value: int, width: int) -> list[int]:
    return [(value >> i) & 1 for i in range(width)]
