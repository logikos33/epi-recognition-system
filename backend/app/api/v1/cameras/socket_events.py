"""SocketIO event handlers for camera monitoring.

Pattern:
    Worker publishes to Redis channel det:{camera_id}
    This module subscribes and re-emits to WebSocket rooms
    Browser joins room camera:{camera_id} on connect

Never send WebSocket from Worker directly.
"""
import json
import logging
import threading

logger = logging.getLogger(__name__)

_subscription_thread: threading.Thread | None = None
_running = False


def init_socket_events(socketio, redis_url: str) -> None:
    """Register SocketIO events and start Redis subscription thread."""

    @socketio.on("join_camera")
    def on_join_camera(data):
        from flask_socketio import join_room
        camera_id = data.get("camera_id")
        if camera_id:
            join_room(f"camera:{camera_id}")
            logger.debug("Client joined room camera:%s", camera_id)
            socketio.emit("joined", {"camera_id": camera_id}, room=f"camera:{camera_id}")

    @socketio.on("leave_camera")
    def on_leave_camera(data):
        from flask_socketio import leave_room
        camera_id = data.get("camera_id")
        if camera_id:
            leave_room(f"camera:{camera_id}")

    @socketio.on("connect")
    def on_connect():
        logger.debug("WebSocket client connected")

    @socketio.on("disconnect")
    def on_disconnect():
        logger.debug("WebSocket client disconnected")

    # Start Redis subscription in background thread
    _start_redis_subscriber(socketio, redis_url)


def _start_redis_subscriber(socketio, redis_url: str) -> None:
    """Start a background thread that subscribes to Redis det:* channels."""
    global _subscription_thread, _running

    def _subscribe():
        global _running
        try:
            import redis
            r = redis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.psubscribe("det:*")  # Subscribe to all camera detection channels
            logger.info("[SocketIO] Redis subscription started (det:* channels)")
            _running = True

            for message in pubsub.listen():
                if not _running:
                    break
                if message["type"] != "pmessage":
                    continue
                try:
                    channel = message["channel"]  # e.g. "det:camera-uuid"
                    camera_id = channel.split(":", 1)[1]
                    payload = json.loads(message["data"])
                    # Emit to the camera room
                    socketio.emit(
                        "detection",
                        payload,
                        room=f"camera:{camera_id}",
                        namespace="/",
                    )
                except Exception as e:
                    logger.debug("Redis message handling error: %s", e)
        except ImportError:
            logger.warning("[SocketIO] redis package not installed — real-time detections degraded")
        except Exception as e:
            logger.warning("[SocketIO] Redis subscription failed (degraded): %s", e)
            _running = False

    _subscription_thread = threading.Thread(
        target=_subscribe,
        daemon=True,
        name="redis-socketio-bridge",
    )
    _subscription_thread.start()


def stop_redis_subscriber() -> None:
    global _running
    _running = False
