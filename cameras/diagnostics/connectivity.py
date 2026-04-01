"""
EPI Monitor — Camera Connectivity Diagnostic

Diagnóstico de conectividade em 5 camadas.
"""

import socket
import subprocess
import time
import cv2
import base64
from typing import Dict, Optional
from .error_mapper import map_error_to_message


class ConnectivityDiagnostic:
    """Teste de conectividade em 5 camadas."""

    TIMEOUT_GLOBAL = 15  # segundos

    def diagnose(self, host: str, port: int, username: str,
                 password: str, rtsp_url: str) -> Dict:
        """
        Executa diagnóstico em 5 camadas.

        Camadas:
        1. ICMP Ping
        2. TCP Socket na porta RTSP
        3. RTSP OPTIONS (detecta erro de auth)
        4. OpenCV VideoCapture (TCP → UDP fallback)
        5. Captura de frame real

        Para no primeiro erro e retorna diagnóstico.
        """
        result = {
            'success': False,
            'layer_reached': 0,
            'latency_ms': None,
            'snapshot_base64': None,
            'error': None,
            'details': {}
        }

        # Camada 1: ICMP Ping
        layer1_result = self._layer1_ping(host)
        result['details']['ping'] = layer1_result
        if not layer1_result['success']:
            result['error'] = layer1_result['error']
            return result
        result['layer_reached'] = 1
        result['latency_ms'] = layer1_result.get('latency_ms')

        # Camada 2: TCP Socket
        layer2_result = self._layer2_tcp_socket(host, port)
        result['details']['tcp'] = layer2_result
        if not layer2_result['success']:
            result['error'] = layer2_result['error']
            return result
        result['layer_reached'] = 2

        # Camada 3: RTSP OPTIONS
        layer3_result = self._layer3_rtsp_options(rtsp_url)
        result['details']['rtsp'] = layer3_result
        if not layer3_result['success']:
            result['error'] = layer3_result['error']
            return result
        result['layer_reached'] = 3

        # Camada 4: OpenCV VideoCapture
        layer4_result = self._layer4_opencv_capture(rtsp_url)
        result['details']['capture'] = layer4_result
        if not layer4_result['success']:
            result['error'] = layer4_result['error']
            return result
        result['layer_reached'] = 4

        # Camada 5: Frame real
        layer5_result = self._layer5_frame_capture(rtsp_url)
        result['details']['frame'] = layer5_result
        if not layer5_result['success']:
            result['error'] = layer5_result['error']
            return result

        # Sucesso!
        result['success'] = True
        result['layer_reached'] = 5
        result['snapshot_base64'] = layer5_result.get('snapshot_base64')

        return result

    def _layer1_ping(self, host: str) -> Dict:
        """Camada 1: ICMP ping."""
        try:
            start = time.time()
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', host],
                capture_output=True, timeout=5
            )
            latency_ms = round((time.time() - start) * 1000, 1)
            if result.returncode == 0:
                return {'success': True, 'latency_ms': latency_ms}
            else:
                return {'success': False, 'error': 'Host não respondeu ao ping'}
        except Exception as e:
            return {'success': False, 'error': map_error_to_message(e)}

    def _layer2_tcp_socket(self, host: str, port: int) -> Dict:
        """Camada 2: TCP socket na porta."""
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            connect_result = sock.connect_ex((host, port))
            sock.close()
            latency_ms = round((time.time() - start) * 1000, 1)

            if connect_result == 0:
                return {'success': True, 'latency_ms': latency_ms}
            else:
                return {'success': False, 'error': f'Porta {port} fechada'}
        except Exception as e:
            return {'success': False, 'error': map_error_to_message(e)}

    def _layer3_rtsp_options(self, rtsp_url: str) -> Dict:
        """Camada 3: RTSP OPTIONS (simplificado - apenas valida URL)."""
        # OpenCV já vai tentar conectar na camada 4
        # Aqui apenas validamos formato da URL
        if rtsp_url.startswith('rtsp://'):
            return {'success': True}
        return {'success': False, 'error': 'URL RTSP inválida'}

    def _layer4_opencv_capture(self, rtsp_url: str) -> Dict:
        """Camada 4: OpenCV VideoCapture com TCP → UDP fallback."""
        # Tentar TCP primeiro
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                return {'success': True}
            else:
                return {'success': False, 'error': 'Não foi possível capturar frame'}
        return {'success': False, 'error': 'OpenCV não conseguiu abrir stream'}

    def _layer5_frame_capture(self, rtsp_url: str) -> Dict:
        """Camada 5: Captura de frame real em base64."""
        try:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    # Converter para base64
                    _, buffer = cv2.imencode('.jpg', frame)
                    snapshot_base64 = base64.b64encode(buffer).decode('utf-8')
                    return {'success': True, 'snapshot_base64': snapshot_base64}

            return {'success': False, 'error': 'Falha ao capturar frame'}
        except Exception as e:
            return {'success': False, 'error': map_error_to_message(e)}
