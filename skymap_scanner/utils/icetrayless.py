"""Tools that don't need icecube/icetray."""


def create_event_id_string(run_id, event_id, event_type=None):
    return f"run{run_id:08d}.evt{event_id:012d}.{event_type}"


def parse_event_id_string(event_id_string):
    parts = event_id_string.split(".")
    if len(parts) != 3:
        raise RuntimeError("event ID must have 3 parts separated by '.'")

    if not parts[0].startswith("run"):
        raise RuntimeError('event ID run part does not start with "run"')
    if not parts[1].startswith("evt"):
        raise RuntimeError('event ID event part does not start with "evt"')

    run = int(parts[0][3:])
    event = int(parts[1][3:])
    evt_type = parts[2]
    return (run, event, evt_type)
