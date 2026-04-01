"""
Blueprint Flask para Rules Engine.

Endpoints:
- /api/rules (6 endpoints): gerenciar regras
- /api/sessions (7 endpoints): gerenciar sessões de contagem
"""
from flask import Blueprint, request, jsonify
import logging

from backend.database import get_db_context
from .models import Rule, CountingSession
from .repository import RulesRepository, SessionRepository
from .service import get_rules_engine

logger = logging.getLogger(__name__)

# Create blueprints
rules_bp = Blueprint('rules', __name__, url_prefix='/api/rules')
sessions_bp = Blueprint('sessions', __name__, url_prefix='/api/sessions')


# ============================================================================
# /api/rules endpoints
# ============================================================================

@rules_bp.route('/', methods=['GET'])
def list_rules():
    """Lista todas as regras."""
    try:
        with get_db_context() as db:
            rules = RulesRepository.get_all(db)
            return jsonify({
                'success': True,
                'rules': [
                    {
                        'id': r.id,
                        'name': r.name,
                        'description': r.description,
                        'template_type': r.template_type,
                        'event_type': r.event_type,
                        'action_type': r.action_type,
                        'camera_ids': r.camera_ids,
                        'cooldown_seconds': r.cooldown_seconds,
                        'min_confidence': r.min_confidence,
                        'is_active': r.is_active
                    }
                    for r in rules
                ]
            })
    except Exception as e:
        logger.error(f"❌ List rules error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rules_bp.route('/templates', methods=['GET'])
def get_templates():
    """Retorna templates pré-configurados."""
    try:
        with get_db_context() as db:
            templates = RulesRepository.get_templates(db)
            return jsonify({
                'success': True,
                'templates': [
                    {
                        'id': t.id,
                        'name': t.name,
                        'description': t.description,
                        'template_type': t.template_type,
                        'event_type': t.event_type,
                        'action_type': t.action_type,
                        'is_active': t.is_active
                    }
                    for t in templates
                ]
            })
    except Exception as e:
        logger.error(f"❌ Get templates error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rules_bp.route('/', methods=['POST'])
def create_rule():
    """Cria nova regra customizada."""
    try:
        data = request.get_json()

        # Validar campos obrigatórios
        required = ['name', 'event_type', 'action_type']
        for field in required:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        with get_db_context() as db:
            rule = RulesRepository.create(
                db,
                name=data['name'],
                description=data.get('description'),
                template_type=data.get('template_type'),
                event_type=data['event_type'],
                event_config=data.get('event_config', {}),
                action_type=data['action_type'],
                action_config=data.get('action_config', {}),
                camera_ids=data.get('camera_ids'),
                cooldown_seconds=data.get('cooldown_seconds', 0),
                min_confidence=data.get('min_confidence', 0.5)
            )

            return jsonify({
                'success': True,
                'rule': {
                    'id': rule.id,
                    'name': rule.name
                }
            })

    except Exception as e:
        logger.error(f"❌ Create rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rules_bp.route('/<rule_id>', methods=['PUT'])
def update_rule(rule_id: str):
    """Atualiza regra existente."""
    try:
        data = request.get_json()

        with get_db_context() as db:
            rule = RulesRepository.update(db, rule_id, **data)
            if not rule:
                return jsonify({'success': False, 'error': 'Rule not found'}), 404

            return jsonify({
                'success': True,
                'rule': {
                    'id': rule.id,
                    'name': rule.name,
                    'is_active': rule.is_active
                }
            })

    except Exception as e:
        logger.error(f"❌ Update rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rules_bp.route('/<rule_id>', methods=['DELETE'])
def delete_rule(rule_id: str):
    """Remove regra (DELETE)."""
    try:
        with get_db_context() as db:
            deleted = RulesRepository.delete(db, rule_id)
            if not deleted:
                return jsonify({'success': False, 'error': 'Rule not found'}), 404

            return jsonify({'success': True, 'message': 'Rule deleted'})

    except Exception as e:
        logger.error(f"❌ Delete rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@rules_bp.route('/<rule_id>/toggle', methods=['POST'])
def toggle_rule(rule_id: str):
    """Ativa/desativa regra."""
    try:
        with get_db_context() as db:
            rule = RulesRepository.toggle(db, rule_id)
            if not rule:
                return jsonify({'success': False, 'error': 'Rule not found'}), 404

            return jsonify({
                'success': True,
                'rule': {
                    'id': rule.id,
                    'name': rule.name,
                    'is_active': rule.is_active
                }
            })

    except Exception as e:
        logger.error(f"❌ Toggle rule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# /api/sessions endpoints
# ============================================================================

@sessions_bp.route('/active', methods=['GET'])
def get_active_sessions():
    """Retorna sessões ativas."""
    try:
        with get_db_context() as db:
            sessions = SessionRepository.get_active(db)
            return jsonify({
                'success': True,
                'sessions': [
                    {
                        'id': s.id,
                        'user_id': s.user_id,
                        'camera_id': s.camera_id,
                        'bay_id': s.bay_id,
                        'truck_plate': s.truck_plate,
                        'product_count': s.product_count,
                        'ai_count': s.ai_count,
                        'started_at': s.started_at.isoformat() if s.started_at else None
                    }
                    for s in sessions
                ]
            })
    except Exception as e:
        logger.error(f"❌ Get active sessions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/pending', methods=['GET'])
def get_pending_sessions():
    """Fila de validação — sessões com status='pending_validation'."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        # TODO: Verify token (importar verify_token do backend)

        with get_db_context() as db:
            sessions = SessionRepository.get_pending(db, user_id='dummy-user-id')  # TODO: pegar user_id do token
            return jsonify({
                'success': True,
                'sessions': [
                    {
                        'id': s.id,
                        'user_id': s.user_id,
                        'camera_id': s.camera_id,
                        'bay_id': s.bay_id,
                        'truck_plate': s.truck_plate,
                        'ai_count': s.ai_count,
                        'started_at': s.started_at.isoformat() if s.started_at else None
                    }
                    for s in sessions
                ]
            })
    except Exception as e:
        logger.error(f"❌ Get pending sessions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/history', methods=['GET'])
def get_session_history():
    """Histórico de sessões com paginação."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        # TODO: Verify token

        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')  # optional filter

        with get_db_context() as db:
            sessions = SessionRepository.get_history(
                db, user_id='dummy-user-id',  # TODO: pegar do token
                limit=limit,
                offset=offset,
                status_filter=status
            )

            # Contar total
            count_result = db.execute(text("""
                SELECT COUNT(*) FROM counting_sessions WHERE user_id = :user_id
            """), {'user_id': 'dummy-user-id'})  # TODO
            total = count_result.scalar()

            return jsonify({
                'success': True,
                'sessions': [
                    {
                        'id': s.id,
                        'user_id': s.user_id,
                        'camera_id': s.camera_id,
                        'bay_id': s.bay_id,
                        'truck_plate': s.truck_plate,
                        'ai_count': s.ai_count,
                        'operator_count': s.operator_count,
                        'status': s.status,
                        'started_at': s.started_at.isoformat() if s.started_at else None,
                        'ended_at': s.ended_at.isoformat() if s.ended_at else None,
                        'validated_at': s.validated_at.isoformat() if s.validated_at else None
                    }
                    for s in sessions
                ],
                'total': total,
                'limit': limit,
                'offset': offset
            })
    except Exception as e:
        logger.error(f"❌ Get session history error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/<session_id>', methods=['GET'])
def get_session_details(session_id: str):
    """Detalhes + eventos da sessão."""
    try:
        with get_db_context() as db:
            session = SessionRepository.get_by_id(db, session_id)
            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            # Buscar eventos da sessão
            events_result = db.execute(text("""
                SELECT id, event_type, class_name, confidence, details, occurred_at
                FROM session_events
                WHERE session_id = :session_id
                ORDER BY occurred_at ASC
            """), {'session_id': session_id})

            events = []
            for row in events_result.fetchall():
                events.append({
                    'id': str(row[0]),
                    'event_type': row[1],
                    'class_name': row[2],
                    'confidence': float(row[3]) if row[3] else None,
                    'details': row[4] or {},
                    'occurred_at': row[5].isoformat() if row[5] else None
                })

            return jsonify({
                'success': True,
                'session': {
                    'id': session.id,
                    'user_id': session.user_id,
                    'camera_id': session.camera_id,
                    'bay_id': session.bay_id,
                    'truck_plate': session.truck_plate,
                    'product_count': session.product_count,
                    'ai_count': session.ai_count,
                    'operator_count': session.operator_count,
                    'status': session.status,
                    'started_at': session.started_at.isoformat() if session.started_at else None,
                    'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                    'duration_seconds': session.duration_seconds,
                    'validated_by': session.validated_by,
                    'validated_at': session.validated_at.isoformat() if session.validated_at else None,
                    'validation_notes': session.validation_notes,
                    'metadata': session.metadata
                },
                'events': events
            })
    except Exception as e:
        logger.error(f"❌ Get session details error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/<session_id>/validate', methods=['POST'])
def validate_session(session_id: str):
    """Valida sessão — operador confirma ou corrige contagem da IA."""
    try:
        data = request.get_json()

        validated_by = data.get('validated_by', 'operador')
        operator_count = data.get('operator_count')  # opcional
        notes = data.get('notes')

        with get_db_context() as db:
            # Buscar sessão
            session = SessionRepository.get_by_id(db, session_id)
            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            # Atualizar status
            update_data = {
                'status': 'validated',
                'validated_by': validated_by,
                'validated_at': datetime.now()
            }

            if operator_count is not None:
                update_data['operator_count'] = operator_count

            if notes:
                update_data['validation_notes'] = notes

            SessionRepository.update(db, session_id, **update_data)

            return jsonify({
                'success': True,
                'message': 'Session validated successfully'
            })
    except Exception as e:
        logger.error(f"❌ Validate session error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/<session_id>/reject', methods=['POST'])
def reject_session(session_id: str):
    """Rejeita sessão — marca como inválida."""
    try:
        data = request.get_json()

        validated_by = data.get('validated_by', 'operador')
        notes = data.get('notes')

        with get_db_context() as db:
            # Buscar sessão
            session = SessionRepository.get_by_id(db, session_id)
            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            # Atualizar status
            SessionRepository.update(
                db, session_id,
                status='rejected',
                validated_by=validated_by,
                validation_notes=notes
            )

            return jsonify({
                'success': True,
                'message': 'Session rejected'
            })
    except Exception as e:
        logger.error(f"❌ Reject session error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/stats', methods=['GET'])
def get_session_stats():
    """Retorna estatísticas agregadas de sessões."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        # TODO: Verify token e extrair user_id

        with get_db_context() as db:
            stats = SessionRepository.get_stats(db, user_id='dummy-user-id')  # TODO
            return jsonify({
                'success': True,
                'stats': stats
            })
    except Exception as e:
        logger.error(f"❌ Get session stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sessions_bp.route('/export', methods=['GET'])
def export_sessions():
    """Exporta sessões para Excel (placeholder por enquanto)."""
    try:
        # Placeholder — implementação completa na FASE 5
        return jsonify({
            'success': False,
            'error': 'Excel export será implementado na FASE 5'
        }), 501
    except Exception as e:
        logger.error(f"❌ Export sessions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
