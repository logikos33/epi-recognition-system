#!/usr/bin/env python3
"""
EPI Monitor — Worker Service
Responsabilidade: FFmpeg + YOLO + processamento de streams.
Não tem endpoints HTTP — comunica via Redis.
"""
import os
import sys
import json
import time
import signal
import logging
import threading
from pathlib import Path

# Adicionar raiz do projeto ao path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WORKER] %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Corrigir DATABASE_URL antes de qualquer import
_db = os.environ.get('DATABASE_URL', '')
if _db.startswith('postgres://'):
    os.environ['DATABASE_URL'] = _db.replace('postgres://', 'postgresql://', 1)

WORKER_ID = os.environ.get('WORKER_ID', 'worker-1')
YOLO_MODEL = os.environ.get('YOLO_MODEL_PATH', 'storage/models/active/model.pt')

class WorkerManager:
    def __init__(self):
        from services.shared.events import EventPublisher, get_redis_client
        self.publisher = EventPublisher()
        self.redis = get_redis_client()
        self.active = {}   # camera_id → config
        self.running = True
        self._load_processors()
        logger.info(f"✅ Worker {WORKER_ID} iniciado")

    def _load_processors(self):
        """Carregar StreamManager e YOLOProcessor do projeto."""
        try:
            from backend.stream_manager import StreamManager
            self.stream_mgr = StreamManager()
            logger.info("✅ StreamManager carregado")
        except ImportError as e:
            logger.warning(f"⚠️  StreamManager não disponível: {e}")
            self.stream_mgr = None

        try:
            from backend.yolo_processor import YOLOProcessor
            self.yolo = YOLOProcessor()
            # Registrar callback para publicar detecções
            self.yolo.on_detection = self._on_detection
            logger.info("✅ YOLOProcessor carregado")
        except ImportError as e:
            logger.warning(f"⚠️  YOLOProcessor não disponível: {e}")
            self.yolo = None

    def _on_detection(self, camera_id, detections, timestamp=None):
        """Callback: YOLO detectou algo → publicar via Redis."""
        self.publisher.publish_detection(
            camera_id=camera_id,
            detections=detections,
            timestamp=timestamp or time.time()
        )

    def start_stream(self, camera_id, rtsp_url, config=None):
        if camera_id in self.active:
            logger.info(f"Stream {camera_id} já ativo")
            return
        logger.info(f"Iniciando stream: {camera_id} — {rtsp_url[:30]}...")
        self.publisher.publish_stream_status(camera_id, 'starting')
        try:
            if self.stream_mgr:
                self.stream_mgr.start_stream(camera_id, rtsp_url)
            if self.yolo:
                self.yolo.start_processing(camera_id, rtsp_url, fps=5)
            self.active[camera_id] = {
                'rtsp_url': rtsp_url,
                'started_at': time.time(),
                'config': config or {}
            }
            self.publisher.publish_stream_status(camera_id, 'active')
            logger.info(f"✅ Stream {camera_id} ativo")
        except Exception as e:
            logger.error(f"❌ Erro stream {camera_id}: {e}")
            self.publisher.publish_stream_status(camera_id, 'error', str(e))

    def stop_stream(self, camera_id):
        if camera_id not in self.active:
            return
        logger.info(f"Parando stream: {camera_id}")
        try:
            if self.stream_mgr:
                self.stream_mgr.stop_stream(camera_id)
            if self.yolo:
                self.yolo.stop_processing(camera_id)
            del self.active[camera_id]
            self.publisher.publish_stream_status(camera_id, 'stopped')
            logger.info(f"✅ Stream {camera_id} parado")
        except Exception as e:
            logger.error(f"Erro ao parar {camera_id}: {e}")

    def handle_command(self, cmd):
        action = cmd.get('action')
        cam = cmd.get('camera_id')
        if action == 'start_stream':
            self.start_stream(cam, cmd.get('rtsp_url'), cmd.get('config'))
        elif action == 'stop_stream':
            self.stop_stream(cam)
        elif action == 'health_check':
            self._report_health()
        else:
            logger.warning(f"Comando desconhecido: {action}")

    def _report_health(self):
        self.publisher.update_worker_health(
            WORKER_ID,
            len(self.active),
            list(self.active.keys())
        )

    def _health_loop(self):
        while self.running:
            self._report_health()
            time.sleep(20)

    def run(self):
        """Loop principal — escutar comandos."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(f'epi:commands:{WORKER_ID}')
        logger.info(f"✅ Escutando: epi:commands:{WORKER_ID}")

        # Registrar worker como vivo
        self.redis.sadd('epi:workers', WORKER_ID)

        # Thread de health
        t = threading.Thread(target=self._health_loop, daemon=True)
        t.start()

        for msg in pubsub.listen():
            if not self.running:
                break
            if msg['type'] == 'message':
                try:
                    self.handle_command(json.loads(msg['data']))
                except Exception as e:
                    logger.error(f"Erro no comando: {e}")

    def shutdown(self):
        self.running = False
        for cam in list(self.active.keys()):
            self.stop_stream(cam)
        self.redis.srem('epi:workers', WORKER_ID)
        logger.info("Worker encerrado")


def main():
    logger.info("=" * 50)
    logger.info(f"EPI Monitor Worker — ID: {WORKER_ID}")
    logger.info("=" * 50)

    # Verificar Redis
    try:
        from services.shared.events import get_redis_client
        get_redis_client().ping()
        logger.info("✅ Redis OK")
    except Exception as e:
        logger.error(f"❌ Redis: {e}")
        sys.exit(1)

    mgr = WorkerManager()

    def shutdown(sig, frame):
        mgr.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    mgr.run()


if __name__ == '__main__':
    main()
