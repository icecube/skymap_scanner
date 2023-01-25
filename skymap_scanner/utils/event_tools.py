"""Tools for functions/data related to icecube events."""

import dataclasses as dc


@dc.dataclass
class EventMetadata:
    """Encapsulates metadata for an event."""

    run_id: int
    event_id: int
    event_type: str
    mjd: float  # required but meaningless for simulated events
    is_real: bool  # as opposed to simulation

    def __str__(self) -> str:
        """Use for logging & filenaming."""
        return f"run{self.run_id:08d}.evt{self.event_id:012d}.{self.event_type}"
