import logging

from flask import Blueprint, jsonify, request

from message_store import MessageStore


logger = logging.getLogger(__name__)


def register_routes(app, sio, message_store: MessageStore):
    router = Blueprint("socket_routes", __name__)

    @router.post("/send/msg")
    def send_msg():
        # logger.info("***************SENDING NOTIFICATION********************")
        # logger.info("%s", request.path)
        # logger.info("***************SENDING NOTIFICATION********************")

        payload = request.get_json(silent=True) or {}
        user_id = payload.get("userId")
        msg = payload.get("msg")
        request_id = payload.get("requestId")
        metadata = payload.get("metadata")
        event_type = payload.get("type")

        # logger.info("%s userId web notify", user_id)

        sio.emit(
            user_id,
            {
                "status": True,
                "message": msg,
                "requestId": request_id,
                "type": event_type,
                "metadata": metadata,
            },
        )

        message_store.save_message(payload=payload, request_id=request_id)

        # logger.info("*************** NOTIFICATION DELIVERED********************")
        return jsonify({"status": True, "msg": "success"})

    @router.get("/service/ping")
    def ping():
        return jsonify({"status": True, "msg": "pong"})
        
    app.register_blueprint(router, url_prefix="/service/api/infisign/v3.1.1/socket")
