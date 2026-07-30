import asyncio
import logging
from typing import Awaitable, Callable, List

from app.cache.redis_client import RedisClient
from app.events.schema import Event

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.subscribers: dict[str, List[Callable[[Event], Awaitable[None]]]] = {}
        self.channel_name = "featureflow_events"
        self._listener_task = None
        self._pubsub = None

    async def start(self):
        """Starts the event bus listener in the background."""
        if self._listener_task is not None:
            return

        redis_conn = self.redis.client
        if not redis_conn or not self.redis.is_connected:
            logger.warning("Redis client not available, EventBus running in detached mode")
            return

        try:
            self._pubsub = redis_conn.pubsub()
            await self._pubsub.subscribe(self.channel_name)
            self._listener_task = asyncio.create_task(self._listen())
            logger.info("EventBus started and subscribed to channel: %s", self.channel_name)
        except Exception as e:
            logger.warning(f"Failed to subscribe to EventBus channel (detached mode): {e}")
            self._pubsub = None

    async def stop(self):
        """Stops the event bus listener."""
        if self._pubsub:
            await self._pubsub.unsubscribe(self.channel_name)
            await self._pubsub.close()
            self._pubsub = None

        if self._listener_task:
            self._listener_task.cancel()
            self._listener_task = None
        logger.info("EventBus stopped.")

    async def publish(self, event: Event):
        """Publishes an event to the Redis channel."""
        redis_conn = self.redis.client
        if redis_conn:
            # Serialize the event (handling datetime)
            payload = event.model_dump_json()
            await redis_conn.publish(self.channel_name, payload)
        else:
            # If Redis is down, we might want to log it or push to an in-memory queue
            logger.warning("Redis unavailable. Failed to publish event: %s", event.type)

    def subscribe(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Registers a callback for a specific event type, or '*' for all events."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    async def _listen(self):
        """Background task that listens to Redis Pub/Sub."""
        if not self._pubsub:
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    raw_data = message["data"]
                    if isinstance(raw_data, bytes):
                        raw_data = raw_data.decode("utf-8")
                    try:
                        event = Event.model_validate_json(raw_data)
                        await self._dispatch(event)
                    except Exception as e:
                        logger.error("Failed to parse or dispatch event: %s. Error: %s", raw_data, e)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("EventBus listener encountered an error: %s", e)

    async def _dispatch(self, event: Event):
        """Dispatches an incoming event to registered local subscribers."""
        handlers = self.subscribers.get(event.type, [])
        wildcard_handlers = self.subscribers.get("*", [])

        all_handlers = handlers + wildcard_handlers
        for handler in all_handlers:
            try:
                # Dispatch concurrently
                asyncio.create_task(handler(event))
            except Exception as e:
                logger.error("Error in event handler for %s: %s", event.type, e)
