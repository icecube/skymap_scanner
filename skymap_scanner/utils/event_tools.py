"""Tools for functions/data related to icecube events."""

import dataclasses as dc

MIN_REAL_RUN_ID_INC = 1e5
MAX_REAL_RUN_ID_EXC = 1e6  # 1 million


@dc.dataclass
class EventMetadata:
    """Encapsulates metadata for an event."""

    run_id: int
    event_id: int
    event_type: str
    mjd: float  # required but meaningless for simulated events
    is_real_event: bool  # as opposed to simulation

    def __post_init__(self) -> None:
        if self.is_real_event and not (
            MIN_REAL_RUN_ID_INC <= self.run_id < MAX_REAL_RUN_ID_EXC
        ):
            raise ValueError(
                f"Run ID Out of Range for Real Event: {self.run_id} "
                f"(valid range is [{MIN_REAL_RUN_ID_INC}, {MAX_REAL_RUN_ID_EXC}))"
            )

    def __str__(self) -> str:
        """Use for logging & filenaming."""
        return f"run{self.run_id:08d}.evt{self.event_id:012d}.{self.event_type}"
