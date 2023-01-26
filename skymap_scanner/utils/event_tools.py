"""Tools for functions/data related to icecube events."""

import dataclasses as dc

MIN_REAL_RUN_ID = 100000


@dc.dataclass
class EventMetadata:
    """Encapsulates metadata for an event."""

    run_id: int
    event_id: int
    event_type: str
    mjd: float  # required but meaningless for simulated events
    is_real_event: bool  # as opposed to simulation

    def __post_init__(self) -> None:
        if self.is_real_event and self.run_id < MIN_REAL_RUN_ID:
            raise ValueError(
                f"Run ID Out of Range: {self.run_id} (valid range is {MIN_REAL_RUN_ID}+)"
            )

    def __str__(self) -> str:
        """Use for logging & filenaming."""
        return f"run{self.run_id:08d}.evt{self.event_id:012d}.{self.event_type}"
