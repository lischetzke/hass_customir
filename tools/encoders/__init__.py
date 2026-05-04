"""Dev-time IR protocol encoders.

Each encoder takes protocol-specific parameters and returns a list of signed
microsecond timings (positive = pulse-on, negative = pulse-off), matching the
``infrared_protocols.Command.get_raw_timings()`` contract.

These encoders run on a contributor's machine at catalog-generation time;
they are NOT loaded by the Home Assistant integration at runtime.
"""

from __future__ import annotations

from .nec import encode_nec1, encode_necext
from .pronto import encode_pronto
from .rc5 import encode_rc5
from .rc6 import encode_rc6
from .samsung import encode_samsung32
from .sirc import encode_sirc

__all__ = [
    "encode_by_protocol",
    "encode_nec1",
    "encode_necext",
    "encode_pronto",
    "encode_rc5",
    "encode_rc6",
    "encode_samsung32",
    "encode_sirc",
]


def encode_by_protocol(
    protocol: str, *, device: int, subdevice: int, function: int
) -> tuple[list[int], int]:
    """Dispatch by irdb-style protocol name.

    Returns ``(timings, modulation_hz)``. ``subdevice`` may be ``-1`` in irdb
    to mean "use 8-bit standard NEC inversion".
    """
    name = protocol.upper().replace(" ", "")

    if name in ("NEC", "NEC1", "NEC2"):
        return encode_nec1(address=device, command=function), 38000
    if name in ("NECX", "NECX1", "NECX2", "NECEXT"):
        # irdb encodes "address" as device | (subdevice << 8). For NEC2 the
        # subdevice may be -1, fall back to NEC1's inverted-address form.
        if subdevice < 0:
            return encode_nec1(address=device, command=function), 38000
        addr16 = (device & 0xFF) | ((subdevice & 0xFF) << 8)
        return encode_necext(address=addr16, command=function), 38000
    if name in ("RC5", "RC-5"):
        return encode_rc5(address=device, command=function), 36000
    if name in ("RC6", "RC-6", "RC6-0", "RC6-0-16"):
        return encode_rc6(address=device, command=function), 36000
    if name in ("SONY12",):
        return encode_sirc(address=device, command=function, bits=12), 40000
    if name in ("SONY15",):
        return encode_sirc(address=device, command=function, bits=15), 40000
    if name in ("SONY20",):
        return encode_sirc(address=device, command=function, bits=20, extended=subdevice), 40000
    if name in ("SAMSUNG", "SAMSUNG32", "SAMSUNG36"):
        return encode_samsung32(address=device, command=function), 38000

    raise NotImplementedError(f"Unsupported protocol: {protocol!r}")
