"""Runtime IR command wrapper.

The bundled catalog stores fully-encoded raw timings per command. At runtime
we wrap that list in a tiny ``Command`` subclass so the core ``infrared``
domain can forward it to the chosen emitter without any decoding step.

A second variant — :class:`LegacyRawCommand` — is provided as a workaround for
emitter integrations that are still on the pre-2.0 ``infrared-protocols`` API
(where ``get_raw_timings()`` returned ``list[Timing]`` with ``.high_us`` /
``.low_us`` attributes). The breaking change landed in
`infrared-protocols#19 <https://github.com/home-assistant-libs/infrared-protocols/pull/19>`_
on 2026-04-20. Users hitting ``'int' object has no attribute 'high_us'`` can
flip the *Legacy timing pairs* option on; the underlying fix is for the
emitter to consume the modern ``list[int]`` shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import override

from infrared_protocols import Command


class RawCommand(Command):
    """Pre-encoded IR command — replays a stored list of raw timings."""

    def __init__(
        self,
        *,
        modulation: int,
        repeat_count: int = 0,
        timings: list[int],
    ) -> None:
        """Initialize the raw IR command."""
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._timings: list[int] = list(timings)

    @override
    def get_raw_timings(self) -> list[int]:
        """Return the stored timings verbatim.

        Positive values are pulse-on durations in microseconds; negative
        values are pulse-off durations.
        """
        return list(self._timings)


@dataclass(frozen=True, slots=True)
class _LegacyTiming:
    """Pulse/space pair shaped like the pre-2.0 ``infrared_protocols.Timing``.

    Also exposes integer-equivalence so emitters that fell back to treating
    each entry as ``int`` (e.g. ``protobuf.timings.extend(...)``) keep working.
    """

    high_us: int
    low_us: int

    def __int__(self) -> int:
        return self.high_us

    def __index__(self) -> int:
        return self.high_us


class LegacyRawCommand(Command):
    """Compatibility shim — emits ``[_LegacyTiming, …]`` instead of ``list[int]``.

    Use only if the receiving emitter integration accesses ``.high_us`` /
    ``.low_us`` on each timing element. This shape was removed from
    ``infrared-protocols`` in 2.0.0; the proper fix is to update the emitter.
    """

    def __init__(
        self,
        *,
        modulation: int,
        repeat_count: int = 0,
        timings: list[int],
    ) -> None:
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._pairs: list[_LegacyTiming] = []
        # Group alternating signed-µs ints into (pulse, space) pairs. NEC
        # frames end with a trailing pulse (positive int) and no following
        # space — that becomes one ``_LegacyTiming(high_us=p, low_us=0)``.
        i = 0
        while i < len(timings):
            high = timings[i]
            low = 0
            if i + 1 < len(timings) and timings[i + 1] < 0:
                low = -timings[i + 1]
                i += 2
            else:
                i += 1
            self._pairs.append(_LegacyTiming(high_us=high, low_us=low))

    @override
    def get_raw_timings(self) -> list[_LegacyTiming]:  # type: ignore[override]
        return list(self._pairs)
