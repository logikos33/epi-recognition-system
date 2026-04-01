"""
EPI Monitor — Camera Stream Manager

Gerencia streams HLS via FFmpeg em subprocessos isolados.
Singleton pattern para gerenciar todos os streams ativos.
"""

import os
import subprocess
import threading
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamManager:
    """Gerenciador singleton de streams HLS."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._streams: Dict[str, Dict] = {}
        self._max_streams = int(os.environ.get('MAX_CONCURRENT_STREAMS', 16))
        self._storage_path = os.environ.get('STREAM_STORAGE_PATH', 'storage/streams')

        # Criar diretório de storage
        os.makedirs(self._storage_path, exist_ok=True)

        # Iniciar monitor de streams
        self._monitor_thread = threading.Thread(target=self._monitor_streams,
                                               daemon=True)
        self._monitor_thread.start()

        logger.info(f"StreamManager inicializado (max_streams={self._max_streams})")

    def start_stream(self, camera_id: str, rtsp_url: str) -> Dict:
        """
        Inicia stream HLS para uma câmera.

        Retorna: {success, hls_url, error}
        """
        # Verificar limite de streams
        if len(self._streams) >= self._max_streams:
            return {'success': False,
                   'error': f'Máximo de {self._max_streams} streams atingido'}

        # Verificar se stream já existe
        if camera_id in self._streams:
            stream_info = self._streams[camera_id]
            if stream_info['process'].poll() is None:
                return {'success': True, 'hls_url': stream_info['hls_url']}

        # Criar diretório para a câmera
        camera_path = os.path.join(self._storage_path, camera_id)
        os.makedirs(camera_path, exist_ok=True)
        hls_path = os.path.join(camera_path, 'stream.m3u8')

        # Comando FFmpeg
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', rtsp_url,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-tune', 'zerolatency',
            '-f', 'hls',
            '-hls_time', '2',
            '-hls_list_size', '3',
            '-hls_segment_filename', f'{camera_path}/segment_%03d.ts',
            hls_path
        ]

        # Iniciar subprocess
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )

            self._streams[camera_id] = {
                'process': process,
                'rtsp_url': rtsp_url,
                'hls_url': f'/streams/{camera_id}/stream.m3u8',
                'hls_path': hls_path,
                'started_at': datetime.now(),
                'reconnect_attempts': 0
            }

            logger.info(f"Stream iniciado para câmera {camera_id}")
            return {'success': True, 'hls_url': f'/streams/{camera_id}/stream.m3u8'}

        except Exception as e:
            logger.error(f"Erro ao iniciar stream para {camera_id}: {e}")
            return {'success': False, 'error': str(e)}

    def stop_stream(self, camera_id: str) -> Dict:
        """
        Para stream HLS de uma câmera.

        Retorna: {success, error}
        """
        if camera_id not in self._streams:
            return {'success': False, 'error': 'Stream não encontrado'}

        stream_info = self._streams[camera_id]
        process = stream_info['process']

        try:
            # Terminar processo
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            # Remover arquivos HLS
            camera_path = os.path.join(self._storage_path, camera_id)
            if os.path.exists(camera_path):
                for f in os.listdir(camera_path):
                    os.remove(os.path.join(camera_path, f))
                os.rmdir(camera_path)

            del self._streams[camera_id]
            logger.info(f"Stream parado para câmera {camera_id}")
            return {'success': True}

        except Exception as e:
            logger.error(f"Erro ao parar stream para {camera_id}: {e}")
            return {'success': False, 'error': str(e)}

    def get_status(self, camera_id: str) -> Optional[Dict]:
        """Retorna status do stream de uma câmera."""
        if camera_id not in self._streams:
            return None

        stream_info = self._streams[camera_id]
        process = stream_info['process']

        return {
            'camera_id': camera_id,
            'active': process.poll() is None,
            'uptime_seconds': (datetime.now() - stream_info['started_at']).total_seconds(),
            'hls_url': stream_info['hls_url']
        }

    def get_all_status(self) -> Dict[str, Dict]:
        """Retorna status de todos os streams."""
        return {camera_id: self.get_status(camera_id)
               for camera_id in self._streams}

    def _monitor_streams(self):
        """Thread de monitoramento com auto-reconexão."""
        max_reconnect = int(os.environ.get('CAMERA_MAX_RECONNECT_ATTEMPTS', 5))

        while True:
            try:
                for camera_id, stream_info in list(self._streams.items()):
                    process = stream_info['process']

                    # Verificar se processo morreu
                    if process.poll() is not None:
                        stream_info['reconnect_attempts'] += 1

                        if stream_info['reconnect_attempts'] <= max_reconnect:
                            logger.warning(f"Stream {camera_id} morreu, "
                                         f"reconectando ({stream_info['reconnect_attempts']}/{max_reconnect})")
                            # Tentar reconectar
                            self.start_stream(camera_id, stream_info['rtsp_url'])
                        else:
                            logger.error(f"Stream {camera_id} falhou após "
                                        f"{max_reconnect} tentativas. Removendo.")
                            del self._streams[camera_id]

            except Exception as e:
                logger.error(f"Erro no monitor de streams: {e}")

            threading.Event().wait(30)  # Checar a cada 30s


# Instância global
_stream_manager = None


def get_stream_manager() -> StreamManager:
    """Retorna instância singleton de StreamManager."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
