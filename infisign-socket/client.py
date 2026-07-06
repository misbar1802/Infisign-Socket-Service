import logging

import socketio


SERVER_URL = "http://localhost:7000"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def socket_test():
    my_email = "email@email.com"
    device_id = 12345

    sio = socketio.Client(ssl_verify=False, reconnection=True)

    @sio.event
    def connect():
        try:
            logger.info("socket connected")
            sio.emit("configure", {"email": my_email, "deviceid": device_id})
            sio.emit(f"/{device_id}", "003021")
        except Exception as exc:
            logger.exception("error while sending socket events: %s", exc)

    @sio.event
    def disconnect():
        logger.info("socket disconnected")

    try:
        logger.info("connecting with websocket transport")
        sio.connect(SERVER_URL, transports=["websocket"])
    except Exception as exc:
        logger.warning("websocket connect failed (%s), retrying with polling", exc)
        sio.connect(SERVER_URL, transports=["polling"])

    sio.wait()


if __name__ == "__main__":
    socket_test()
