"""
EPI Monitor — Camera Service

Camada de serviço que orquestra Repository + Protocols + Diagnostics.
"""

import logging
from typing import List, Dict, Optional
from cameras.models import Camera, DVR, Channel, ConnectionResult
from cameras.repository import CameraRepository, DVRRepository
from cameras.encryption import get_encryption
from cameras.network_utils import NetworkUtils
from cameras.diagnostics.connectivity import ConnectivityDiagnostic
from cameras.stream_manager import get_stream_manager

logger = logging.getLogger(__name__)


class CameraService:
    """Serviço para gerenciamento de câmeras."""

    def __init__(self):
        self.encryption = get_encryption()
        self.network_utils = NetworkUtils()
        self.diagnostic = ConnectivityDiagnostic()
        self.stream_manager = get_stream_manager()

    def add_camera(self, data: Dict) -> Dict:
        """
        Adiciona nova câmera.

        Args:
            data: {name, host, port, username, password, manufacturer, ...}

        Returns:
            {success, camera, error}
        """
        try:
            # Criptografar senha
            password_encrypted = self.encryption.encrypt(data.get('password', ''))

            # Preparar dados para salvar
            camera_data = {
                **data,
                'password_encrypted': password_encrypted,
                'password': None  # Não salvar senha em texto
            }

            # Gerar template de URL RTSP
            camera_data['rtsp_url_template'] = self._build_rtsp_template(data)

            # Salvar no banco
            camera = CameraRepository.save(camera_data)

            # Criar evento
            CameraRepository.create_event(
                camera['id'],
                'created',
                {'name': camera['name']}
            )

            logger.info(f"Câmera {camera['id']} criada: {camera['name']}")
            return {'success': True, 'camera': camera}

        except Exception as e:
            logger.error(f"Erro ao criar câmera: {e}")
            return {'success': False, 'error': str(e)}

    def test_connection(self, data: Dict) -> ConnectionResult:
        """
        Testa conexão com câmera (5 camadas).

        Args:
            data: {host, port, username, password, manufacturer, channel, subtype}

        Returns:
            ConnectionResult com diagnóstico completo
        """
        try:
            # Resolver hostname (se necessário)
            host = data['host']
            try:
                ip, method = self.network_utils.resolve_host(host)
            except Exception as e:
                return ConnectionResult(
                    success=False,
                    error=f"Erro ao resolver host: {str(e)}"
                )

            # Construir URL RTSP
            rtsp_url = self._build_rtsp_url(
                data['manufacturer'],
                ip,
                data['port'],
                data['username'],
                data['password'],
                data.get('channel', 1),
                data.get('subtype', 0)
            )

            # Executar diagnóstico
            result = self.diagnostic.diagnose(
                ip, data['port'], data['username'], data['password'], rtsp_url
            )

            return ConnectionResult(
                success=result['success'],
                latency_ms=result.get('latency_ms'),
                snapshot_base64=result.get('snapshot_base64'),
                error=result.get('error'),
                diagnostics=result.get('details', {}),
                rtsp_url_used=rtsp_url
            )

        except Exception as e:
            logger.error(f"Erro no teste de conexão: {e}")
            return ConnectionResult(success=False, error=str(e))

    def get_dvr_channels(self, dvr_id: str) -> List[Channel]:
        """
        Descobre canais de um DVR.

        Args:
            dvr_id: ID do DVR

        Returns:
            Lista de canais encontrados
        """
        # TODO: Implementar descoberta real via protocol adapter
        # Pseudocódigo:
        # dvr = DVRRepository.find_by_id(dvr_id)
        # adapter = ProtocolAdapterFactory.get_adapter(dvr['manufacturer'])
        # channels = adapter.discover_channels(dvr['host'], dvr['rtsp_port'], ...)
        # return channels
        return []

    def import_dvr_channels(self, dvr_id: str, channel_numbers: List[int]) -> Dict:
        """
        Importa canais selecionados de um DVR como câmeras individuais.

        Args:
            dvr_id: ID do DVR
            channel_numbers: Lista de números dos canais

        Returns:
            {success, cameras, error}
        """
        # TODO: Implementar importação real
        # Pseudocódigo:
        # dvr = DVRRepository.find_by_id(dvr_id)
        # cameras = []
        # for ch in channel_numbers:
        #     camera_data = {
        #         'name': f"{dvr['name']} - Canal {ch}",
        #         'host': dvr['host'],
        #         'port': dvr['rtsp_port'],
        #         'username': dvr['username'],
        #         'password_encrypted': dvr['password_encrypted'],
        #         'channel': ch,
        #         'manufacturer': dvr['manufacturer'],
        #         'dvr_id': dvr['id']
        #     }
        #     camera = CameraRepository.save(camera_data)
        #     cameras.append(camera)
        # return {'success': True, 'cameras': cameras}
        return {'success': False, 'error': 'Não implementado'}

    def start_stream(self, camera_id: str) -> Dict:
        """
        Inicia stream HLS para uma câmera.

        Args:
            camera_id: ID da câmera

        Returns:
            {success, hls_url, error}
        """
        try:
            # Buscar câmera
            camera = CameraRepository.find_by_id(camera_id)
            if not camera:
                return {'success': False, 'error': 'Câmera não encontrada'}

            # Descriptografar senha
            password = self.encryption.decrypt(camera.get('password_encrypted', ''))

            # Construir URL RTSP
            rtsp_url = self._build_rtsp_url(
                camera['manufacturer'],
                camera['host'],
                camera['port'],
                camera['username'],
                password,
                camera['channel'],
                camera['subtype']
            )

            # Iniciar stream
            result = self.stream_manager.start_stream(camera_id, rtsp_url)

            if result['success']:
                # Atualizar status da câmera
                CameraRepository.update(camera_id, {
                    'status': 'streaming',
                    'hls_path': result['hls_url']
                })

            return result

        except Exception as e:
            logger.error(f"Erro ao iniciar stream: {e}")
            return {'success': False, 'error': str(e)}

    def discover_onvif(self) -> List[Dict]:
        """
        Descobre dispositivos ONVIF na rede local.

        Returns:
            Lista de dispositivos encontrados
        """
        # TODO: Implementar ONVIF discovery real
        # Pseudocódigo:
        # from cameras.protocols.onvif_client import ONVIFDiscovery
        # discovery = ONVIFDiscovery()
        # devices = discovery.discover()
        # return devices
        return []

    def _build_rtsp_template(self, data: Dict) -> str:
        """Gera template de URL RTSP para armazenamento (sem senha)."""
        return f"rtsp://{{username}}:{{password}}@{data['host']}:{data['port']}"

    def _build_rtsp_url(self, manufacturer: str, host: str, port: int,
                        username: str, password: str, channel: int,
                        subtype: int) -> str:
        """Constrói URL RTSP completa."""
        # Usar NetworkUtils para sugerir URLs
        urls = self.network_utils.get_suggested_rtsp_urls(
            manufacturer, host, port, username, password, channel, subtype
        )
        return urls[0] if urls else f"rtsp://{username}:{password}@{host}:{port}/stream"
