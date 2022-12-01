def create_event_id(run_id, event_id):
    return "run{0:08d}.evt{1:012d}.HESE".format(run_id, event_id)


def parse_event_id(event_id_string):
    parts = event_id_string.split('.')
    if len(parts) != 3:
        raise RuntimeError("event ID must have 3 parts separated by '.'")

    if not parts[0].startswith("run"):
        raise RuntimeError("event ID run part does not start with \"run\"")
    if not parts[1].startswith("evt"):
        raise RuntimeError("event ID event part does not start with \"evt\"")

    run = int(parts[0][3:])
    event = int(parts[1][3:])
    evt_type = parts[2]
    return (run, event, evt_type)
