"""Runtime IR command wrapper.

The bundled catalog stores fully-encoded raw timings per command. At runtime
we wrap that list in a tiny ``Command`` subclass so the core ``infrared``
domain can forward it to the chosen emitter without any decoding step.
"""

from __future__ import annotations

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
