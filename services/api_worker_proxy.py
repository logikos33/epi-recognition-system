"""
Proxy que a API usa para controlar o Worker via Redis.
Substitui chamadas diretas ao StreamManager na API.
"""
import os
import logging

logger = logging.getLogger(__name__)

_consumer = None

def get_consumer():
    global _consumer
    if _consumer is None:
        from services.shared.events import EventConsumer
        _consumer = EventConsumer()
    return _consumer

def is_redis_available():
    try:
        from services.shared.events import get_redis_client
        get_redis_client().ping()
        return True
    except Exception:
        return False

def start_stream(camera_id, rtsp_url, config=None):
    if not is_redis_available():
        return {'success': False, 'error': 'Redis não disponível — modo local'}
    c = get_consumer()
    worker_id = c.get_best_worker()
    if not worker_id:
        return {'success': False, 'error': 'Nenhum worker disponível'}
    c.set_camera_worker(camera_id, worker_id)
    c.send_command(worker_id, {
        'action': 'start_stream',
        'camera_id': str(camera_id),
        'rtsp_url': rtsp_url,
        'config': config or {}
    })
    return {'success': True, 'worker_id': worker_id}

def stop_stream(camera_id):
    if not is_redis_available():
        return {'success': False, 'error': 'Redis não disponível'}
    c = get_consumer()
    worker_id = c.get_camera_worker(camera_id)
    if not worker_id:
        worker_id = c.get_best_worker()
    if worker_id:
        c.send_command(worker_id, {
            'action': 'stop_stream',
            'camera_id': str(camera_id)
        })
    return {'success': True}

def get_stream_status(camera_id):
    if not is_redis_available():
        return {'status': 'unknown', 'mode': 'local'}
    return get_consumer().get_stream_status(camera_id)

def get_workers_health():
    if not is_redis_available():
        return []
    return get_consumer().get_all_workers_health()

def start_detection_listener(on_detection_cb):
    """
    Iniciar thread que escuta detecções do Worker.
    on_detection_cb(camera_id, detections, timestamp) → Rules Engine
    """
    import threading
    import json

    def _listen():
        from services.shared.events import EventConsumer
        consumer = EventConsumer()
        pubsub = consumer.subscribe_detections()
        logger.info("✅ API escutando detecções do Worker")
        for msg in pubsub.listen():
            if msg['type'] == 'message':
                try:
                    event = json.loads(msg['data'])
                    if event['type'] == 'detection':
                        on_detection_cb(
                            event['camera_id'],
                            event['detections'],
                            event.get('timestamp')
                        )
                except Exception as e:
                    logger.error(f"Erro detecção: {e}")

    t = threading.Thread(target=_listen, daemon=True, name="detection-listener")
    t.start()
