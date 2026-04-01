"""
Sistema de eventos entre Worker e API via Redis.
Worker publica detecções → API consome e aplica Rules Engine.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

def get_redis_client():
    import redis
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    return redis.from_url(url, decode_responses=True)

class EventPublisher:
    """Worker usa para publicar eventos."""
    def __init__(self):
        self.r = get_redis_client()

    def publish_detection(self, camera_id, detections, timestamp):
        self.r.publish('epi:detections', json.dumps({
            'type': 'detection',
            'camera_id': str(camera_id),
            'detections': detections,
            'timestamp': timestamp
        }))

    def publish_stream_status(self, camera_id, status, error=None):
        event = {
            'type': 'stream_status',
            'camera_id': str(camera_id),
            'status': status
        }
        if error:
            event['error'] = error
        self.r.publish('epi:stream_status', json.dumps(event))
        # Cache no Redis para consulta direta
        self.r.setex(
            f'epi:stream:{camera_id}',
            120,
            json.dumps({'status': status, 'error': error})
        )

    def update_worker_health(self, worker_id, active_streams, stream_ids):
        self.r.sadd('epi:workers', worker_id)
        self.r.setex(f'epi:worker:{worker_id}:alive', 60, '1')
        self.r.setex(f'epi:worker:{worker_id}:health', 90, json.dumps({
            'worker_id': worker_id,
            'active_streams': active_streams,
            'stream_ids': stream_ids
        }))

class EventConsumer:
    """API usa para consumir eventos e enviar comandos."""
    def __init__(self):
        self.r = get_redis_client()

    def subscribe_detections(self):
        pubsub = self.r.pubsub()
        pubsub.subscribe('epi:detections', 'epi:stream_status')
        return pubsub

    def send_command(self, worker_id, command):
        self.r.publish(f'epi:commands:{worker_id}', json.dumps(command))

    def get_best_worker(self):
        """Retorna worker com menos streams ativos."""
        workers = self.r.smembers('epi:workers')
        best = None
        min_streams = float('inf')
        for wid in workers:
            if not self.r.get(f'epi:worker:{wid}:alive'):
                continue
            health = self.r.get(f'epi:worker:{wid}:health')
            if health:
                data = json.loads(health)
                n = data.get('active_streams', 0)
                if n < 4 and n < min_streams:
                    min_streams = n
                    best = wid
        return best or (list(workers)[0] if workers else None)

    def get_stream_status(self, camera_id):
        data = self.r.get(f'epi:stream:{camera_id}')
        return json.loads(data) if data else {'status': 'stopped'}

    def get_all_workers_health(self):
        workers = self.r.smembers('epi:workers')
        result = []
        for wid in workers:
            health = self.r.get(f'epi:worker:{wid}:health')
            alive = bool(self.r.get(f'epi:worker:{wid}:alive'))
            if health:
                data = json.loads(health)
                data['is_alive'] = alive
                result.append(data)
        return result

    def set_camera_worker(self, camera_id, worker_id):
        self.r.setex(f'epi:camera:{camera_id}:worker', 3600, worker_id)

    def get_camera_worker(self, camera_id):
        return self.r.get(f'epi:camera:{camera_id}:worker')
