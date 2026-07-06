import os
import logging

import socketio
from flask import Flask
from dotenv import load_dotenv

from message_store import MessageStore
from routes import register_routes

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _build_socket_manager() -> socketio.RedisManager | None:
    redis_url = os.getenv("SOCKET_REDIS_URL", "").strip()
    if not redis_url:
        logger.info("SOCKET_REDIS_URL not set; using in-memory Socket.IO manager")
        return None

    redis_channel = os.getenv("SOCKET_REDIS_CHANNEL", "socketio").strip() or "socketio"
    write_only = _parse_bool(os.getenv("SOCKET_REDIS_WRITE_ONLY"), default=False)

    try:
        manager = socketio.RedisManager(
            redis_url,
            channel=redis_channel,
            write_only=write_only,
        )
        # logger.info(
        #     "Redis manager enabled for Socket.IO (channel=%s, write_only=%s)",
        #     redis_channel,
        #     write_only,
        # )
        return manager
    except Exception:
        logger.exception("Failed to initialize Redis manager; falling back to in-memory manager")
        return None


def create_app() -> tuple[Flask, socketio.Server]:
    app = Flask(__name__)

    redis_url = os.getenv("SOCKET_REDIS_URL", "").strip() or None
    message_ttl_seconds = _parse_int(os.getenv("SOCKET_MESSAGE_TTL_SECONDS"), default=1800)

    client_manager = _build_socket_manager()
    message_store = MessageStore(redis_url=redis_url, ttl_seconds=message_ttl_seconds)

    sio = socketio.Server(
        cors_allowed_origins="*",
        async_mode="eventlet",
        client_manager=client_manager,
    )

    whitelist = {
        "https://staging.infisign.net",
        "https://app.infisign.net",
        "https://oidc.infisign.net",
        "https://wallet.infisign.net",
        "http://localhost:7001",
        "http://localhost:4201",
        "http://localhost:4202",
        "https://people.entrans.io",
    }

    @app.before_request
    def handle_preflight():
        from flask import request, make_response

        if request.method == "OPTIONS":
            response = make_response("", 200)
            origin = request.headers.get("Origin")
            if origin in whitelist:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,appToken"
            response.headers["X-Frame-Options"] = "sameorigin"
            response.headers["Content-Security-Policy"] = "frame-ancestors 'self';"
            return response
        return None

    @app.after_request
    def set_headers(response):
        from flask import request

        origin = request.headers.get("Origin")
        if origin in whitelist:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,appToken"
        response.headers["X-Frame-Options"] = "sameorigin"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self';"
        return response

    @sio.event
    def connect(sid, environ, auth):
        logger.info("socket connected: %s", sid)

    @sio.event
    def disconnect(sid):
        logger.info("socket disconnected: %s", sid)

    @sio.on("configure")
    def configure(sid, data):
        logger.info("configure event from %s: %s", sid, data)

    register_routes(app, sio, message_store)

    return app, sio


def main() -> None:
    app, sio = create_app()
    socket_port = 7000

    logger.info("socket io on port: %s", socket_port)
    # logger.info("Starting without TLS certificates (HTTP/WebSocket mode).")
    # logger.info("REST route is served from the same socket server process.")

    wrapped_app = socketio.WSGIApp(sio, app)

    import eventlet
    import eventlet.wsgi

    listener = eventlet.listen(("0.0.0.0", socket_port))
    eventlet.wsgi.server(listener, wrapped_app, log_output=True)


if __name__ == "__main__":
    main()
