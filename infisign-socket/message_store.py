import json
import logging
import time
from threading import Lock
from uuid import uuid4

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


logger = logging.getLogger(__name__)


class MessageStore:
    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 1800) -> None:
        self.ttl_seconds = max(1, ttl_seconds)
        self._lock = Lock()
        self._in_memory_store: dict[str, tuple[float, str]] = {}
        self._redis = None

        if redis_url:
            if redis is None:
                logger.warning("redis package is not installed, using in-memory backend")
                redis_url = None

        if redis_url:
            try:
                self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                # logger.info("Message store backend: redis (ttl=%s seconds)", self.ttl_seconds)
            except Exception:
                logger.exception("Redis unavailable for message store, using in-memory backend")
                self._redis = None

        # if self._redis is None:
        #     logger.info("Message store backend: in-memory (ttl=%s seconds)", self.ttl_seconds)

    def save_message(self, payload: dict, request_id: str | None) -> str:
        message_id = (request_id or "").strip() or str(uuid4())
        key = f"socket:message:{message_id}"
        value = json.dumps(payload)

        if self._redis is not None:
            try:
                self._redis.setex(key, self.ttl_seconds, value)
                return key
            except Exception:
                logger.exception("Failed to save message in redis, falling back to in-memory backend")

        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._cleanup_expired_locked()
            self._in_memory_store[key] = (expires_at, value)
        return key

    def _cleanup_expired_locked(self) -> None:
        now = time.time()
        expired_keys = [k for k, (exp, _) in self._in_memory_store.items() if exp <= now]
        for key in expired_keys:
            del self._in_memory_store[key]
