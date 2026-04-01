"""
EPI Monitor — Camera Routes

Flask Blueprint para endpoints de câmeras.
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

cameras_bp = Blueprint('cameras', __name__, url_prefix='/api/cameras')

# Config mode tokens em memória
_config_mode_tokens = {}


# ============================================================================
# CÂMERAS
# ============================================================================

@cameras_bp.route('', methods=['GET'])
def list_cameras():
    """Lista todas as câmeras."""
    # TODO: Implementar com CameraRepository
    return jsonify({'cameras': []})


@cameras_bp.route('', methods=['POST'])
def create_camera():
    """Cadastra nova câmera."""
    data = request.json
    # TODO: Implementar com CameraService
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>', methods=['GET'])
def get_camera(camera_id: str):
    """Retorna detalhes de uma câmera."""
    # TODO: Implementar com CameraRepository
    return jsonify({'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>', methods=['PUT'])
def update_camera(camera_id: str):
    """Atualiza câmera (não requer config mode para campos básicos)."""
    # TODO: Implementar com CameraService
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>', methods=['DELETE'])
def delete_camera(camera_id: str):
    """Soft delete de câmera (REQUER config mode)."""
    # TODO: Verificar config mode
    # TODO: Implementar com CameraRepository.soft_delete()
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/test-url', methods=['POST'])
def test_camera_url():
    """Testa conexão + snapshot (rate limit: 10/min)."""
    data = request.json
    # TODO: Implementar com CameraService.test_connection()
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>/snapshot', methods=['GET'])
def get_camera_snapshot(camera_id: str):
    """Captura frame atual da câmera."""
    # TODO: Implementar captura real
    return jsonify({'error': 'Não implementado'}), 501


# ============================================================================
# STREAMS
# ============================================================================

@cameras_bp.route('/<camera_id>/stream/start', methods=['POST'])
def start_stream(camera_id: str):
    """Inicia HLS stream."""
    # TODO: Implementar com CameraService.start_stream()
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>/stream/stop', methods=['POST'])
def stop_stream(camera_id: str):
    """Para HLS stream."""
    # TODO: Implementar com StreamManager.stop_stream()
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/<camera_id>/stream/status', methods=['GET'])
def get_stream_status(camera_id: str):
    """Retorna status do stream."""
    # TODO: Implementar com StreamManager.get_status()
    return jsonify({'error': 'Não implementado'}), 501


# ============================================================================
# DVRS
# ============================================================================

@cameras_bp.route('/dvrs', methods=['GET'])
def list_dvrs():
    """Lista todos os DVRs."""
    # TODO: Implementar com DVRRepository
    return jsonify({'dvrs': []})


@cameras_bp.route('/dvrs', methods=['POST'])
def create_dvr():
    """Cadastra novo DVR."""
    # TODO: Implementar com DVRRepository
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


@cameras_bp.route('/dvrs/<dvr_id>/channels', methods=['GET'])
def get_dvr_channels(dvr_id: str):
    """Descobre canais do DVR."""
    # TODO: Implementar com CameraService.get_dvr_channels()
    return jsonify({'channels': []})


@cameras_bp.route('/dvrs/<dvr_id>/import', methods=['POST'])
def import_dvr_channels(dvr_id: str):
    """Importa canais selecionados."""
    # TODO: Implementar com CameraService.import_dvr_channels()
    return jsonify({'success': False, 'error': 'Não implementado'}), 501


# ============================================================================
# ONVIF DISCOVERY
# ============================================================================

@cameras_bp.route('/discover/onvif', methods=['POST'])
def discover_onvif():
    """WS-Discovery na rede local."""
    # TODO: Implementar com CameraService.discover_onvif()
    return jsonify({'devices': []})


# ============================================================================
# CONFIG MODE
# ============================================================================

@cameras_bp.route('/config/enter', methods=['POST'])
def enter_config_mode():
    """Ativa modo configuração (10 min)."""
    # TODO: Gerar token, salvar em memória
    return jsonify({'token': 'demo-token', 'expires_in': 600})


@cameras_bp.route('/config/exit', methods=['POST'])
def exit_config_mode():
    """Desativa modo configuração."""
    # TODO: Remover token
    return jsonify({'success': True})


@cameras_bp.route('/config/status', methods=['GET'])
def get_config_status():
    """Retorna status do modo configuração."""
    # TODO: Verificar se há token ativo
    return jsonify({'active': False, 'seconds_remaining': 0})


# ============================================================================
# EVENTS
# ============================================================================

@cameras_bp.route('/<camera_id>/events', methods=['GET'])
def get_camera_events(camera_id: str):
    """Retorna histórico de eventos da câmera."""
    # TODO: Implementar com CameraRepository
    return jsonify({'events': []})
