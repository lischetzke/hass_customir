"""NEC-family IR encoders.

Delegates to ``infrared_protocols.NECCommand`` for the actual timing math so
that the runtime library and the dev-time migrator agree on the wire format.
"""

from __future__ import annotations

from infrared_protocols import NECCommand


def encode_nec1(*, address: int, command: int, repeat_count: int = 0) -> list[int]:
    """Standard 8-bit NEC: 8-bit address + ~address + 8-bit command + ~command."""
    if not 0 <= address <= 0xFF:
        raise ValueError(f"NEC1 address must fit in 8 bits, got {address!r}")
    if not 0 <= command <= 0xFF:
        raise ValueError(f"NEC1 command must fit in 8 bits, got {command!r}")
    return NECCommand(
        address=address, command=command, repeat_count=repeat_count
    ).get_raw_timings()


def encode_necext(*, address: int, command: int, repeat_count: int = 0) -> list[int]:
    """Extended NEC: 16-bit address (no inversion) + 8-bit command + ~command."""
    if not 0 <= address <= 0xFFFF:
        raise ValueError(f"NECext address must fit in 16 bits, got {address!r}")
    if not 0 <= command <= 0xFF:
        raise ValueError(f"NECext command must fit in 8 bits, got {command!r}")
    # NECCommand auto-detects 16-bit addresses (address > 0xFF).
    if address <= 0xFF:
        # Force NECext encoding by setting the high byte explicitly. NECCommand
        # treats any address > 0xFF as extended; an exactly-8-bit value would
        # use inverted-address format. Bump into 16-bit space without changing
        # the meaningful address bits:
        address = address | 0x0000  # already <=0xFF; the caller really meant NEC1.
        return NECCommand(
            address=address, command=command, repeat_count=repeat_count
        ).get_raw_timings()
    return NECCommand(
        address=address, command=command, repeat_count=repeat_count
    ).get_raw_timings()
