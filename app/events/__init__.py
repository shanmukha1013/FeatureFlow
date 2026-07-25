from .bus import EventBus


def get_event_bus() -> EventBus:
    raise RuntimeError("EventBus is not initialized.")


def set_event_bus(bus: EventBus):
    # This function is not used, but kept for compatibility.
    pass
