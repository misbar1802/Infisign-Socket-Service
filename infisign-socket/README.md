# socket-service-python

Python version of the existing Node `socket-service`.

## What is included

- HTTPS/WebSocket server using Flask + python-socketio
- Route: `POST /service/api/infisign/v3.1.1/socket/send/msg`
- Event emit behavior based on `userId` (same pattern as Node service)
- Config loader from `.env`
- Test client script (`client.py`)

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run server

```bash
copy .env
python app.py
```

Server listens on port `7000` by default.


## Run test client

```bash
python client.py
```

## Notes

- This service runs without TLS certificates (plain HTTP/WebSocket).
- REST API and socket server are served by the same process in this Python version.

## Redis (optional)

Redis can be enabled as a Socket.IO message queue backend for multi-instance deployments.

Environment variables:

- `SOCKET_REDIS_URL`: Redis URL, for example `redis://localhost:6379/0`
- `SOCKET_REDIS_CHANNEL`: Pub/Sub channel name (default: `socketio`)
- `SOCKET_REDIS_WRITE_ONLY`: `true` to only publish without subscribing (default: `false`)
- `SOCKET_MESSAGE_TTL_SECONDS`: Message record TTL in seconds (default: `1800`, i.e. 30 minutes)

If `SOCKET_REDIS_URL` is not set, the service uses the default in-memory Socket.IO manager.
Message records are also stored in-memory by default and expire after 30 minutes.
