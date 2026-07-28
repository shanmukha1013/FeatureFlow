from .bus import EventBus

_global_event_bus = None

def get_event_bus() -> EventBus:
    if _global_event_bus is None:
        raise RuntimeError("EventBus is not initialized.")
    return _global_event_bus

def set_event_bus(bus: EventBus):
    global _global_event_bus
    _global_event_bus = bus
