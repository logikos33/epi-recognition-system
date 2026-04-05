"""
Repositórios para acesso a dados de Rules Engine.
Usa padrão com get_db_context() e raw SQL com sqlalchemy.text().
"""
from typing import List, Optional
from sqlalchemy import text
from backend.database import get_db_context

from .models import Rule, CountingSession, SessionEvent


class RulesRepository:
    """Repositório para regras de negócio."""

    @staticmethod
    def get_all(db) -> List[Rule]:
        """Retorna todas as regras."""
        result = db.execute(text("""
            SELECT id, name, description, template_type, event_type, event_config,
                   action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                   is_active, created_at, updated_at
            FROM rules
            ORDER BY template_type, name
        """))
        return [Rule.from_row(row) for row in result.fetchall()]

    @staticmethod
    def get_active(db, camera_id: Optional[str] = None) -> List[Rule]:
        """Retorna regras ativas. Se camera_id especificado, filtra por câmera."""
        if camera_id:
            result = db.execute(text("""
                SELECT id, name, description, template_type, event_type, event_config,
                       action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                       is_active, created_at, updated_at
                FROM rules
                WHERE is_active = TRUE
                  AND (camera_ids IS NULL OR :camera_id = ANY(camera_ids))
                ORDER BY template_type, name
            """), {'camera_id': camera_id})
        else:
            result = db.execute(text("""
                SELECT id, name, description, template_type, event_type, event_config,
                       action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                       is_active, created_at, updated_at
                FROM rules
                WHERE is_active = TRUE
                ORDER BY template_type, name
            """))
        return [Rule.from_row(row) for row in result.fetchall()]

    @staticmethod
    def get_by_id(db, rule_id: str) -> Optional[Rule]:
        """Retorna regra por ID."""
        result = db.execute(text("""
            SELECT id, name, description, template_type, event_type, event_config,
                   action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                   is_active, created_at, updated_at
            FROM rules
            WHERE id = :rule_id
        """), {'rule_id': rule_id})
        row = result.fetchone()
        return Rule.from_row(row) if row else None

    @staticmethod
    def get_templates(db) -> List[Rule]:
        """Retorna templates pré-configurados."""
        result = db.execute(text("""
            SELECT id, name, description, template_type, event_type, event_config,
                   action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                   is_active, created_at, updated_at
            FROM rules
            WHERE template_type IS NOT NULL
            ORDER BY template_type, name
        """))
        return [Rule.from_row(row) for row in result.fetchall()]

    @staticmethod
    def create(db, name: str, description: Optional[str], template_type: Optional[str],
                event_type: str, event_config: dict, action_type: str, action_config: dict,
                camera_ids: Optional[list], cooldown_seconds: int, min_confidence: float) -> Rule:
        """Cria nova regra."""
        import uuid
        rule_id = str(uuid.uuid4())
        result = db.execute(text("""
            INSERT INTO rules (id, name, description, template_type, event_type, event_config,
                                action_type, action_config, camera_ids, cooldown_seconds, min_confidence)
            VALUES (:id, :name, :description, :template_type, :event_type, :event_config::jsonb,
                    :action_type, :action_config::jsonb, :camera_ids, :cooldown_seconds, :min_confidence)
            RETURNING id, name, description, template_type, event_type, event_config,
                      action_type, action_config, camera_ids, cooldown_seconds, min_confidence,
                      is_active, created_at, updated_at
        """), {
            'id': rule_id,
            'name': name,
            'description': description,
            'template_type': template_type,
            'event_type': event_type,
            'event_config': event_config,
            'action_type': action_type,
            'action_config': action_config,
            'camera_ids': camera_ids,
            'cooldown_seconds': cooldown_seconds,
            'min_confidence': min_confidence
        })
        row = result.fetchone()
        db.commit()
        return Rule.from_row(row)

    @staticmethod
    def update(db, rule_id: str, **kwargs) -> Optional[Rule]:
        """Atualiza regra."""
        set_clauses = []
        params = {'rule_id': rule_id}

        for key, value in kwargs.items():
            if key in ['name', 'description', 'template_type', 'event_type', 'action_type']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            elif key in ['event_config', 'action_config']:
                set_clauses.append(f"{key} = :{key}::jsonb")
                params[key] = value
            elif key in ['camera_ids', 'cooldown_seconds', 'min_confidence', 'is_active']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

        if set_clauses:
            set_clauses.append("updated_at = NOW()")
            query = f"UPDATE rules SET {', '.join(set_clauses)} WHERE id = :rule_id RETURNING *"
            result = db.execute(text(query), params)
            db.commit()
            return RulesRepository.get_by_id(db, rule_id)
        return None

    @staticmethod
    def toggle(db, rule_id: str) -> Optional[Rule]:
        """Alterna is_active da regra."""
        result = db.execute(text("""
            UPDATE rules
            SET is_active = NOT is_active, updated_at = NOW()
            WHERE id = :rule_id
            RETURNING id, name, is_active, updated_at
        """), {'rule_id': rule_id})
        db.commit()
        row = result.fetchone()
        if row:
            return RulesRepository.get_by_id(db, rule_id)
        return None

    @staticmethod
    def delete(db, rule_id: str) -> bool:
        """Remove regra (DELETE)."""
        result = db.execute(text("DELETE FROM rules WHERE id = :rule_id RETURNING id"), {'rule_id': rule_id})
        db.commit()
        return result.rowcount > 0


class SessionRepository:
    """Repositório para sessões de contagem."""

    @staticmethod
    def get_active(db, user_id: Optional[str] = None) -> List[CountingSession]:
        """Retorna sessões ativas."""
        if user_id:
            result = db.execute(text("""
                SELECT id, user_id, camera_id, bay_id, truck_plate, product_class_id,
                       product_count, ai_count, operator_count, started_at, ended_at,
                       duration_seconds, status, validated_by, validated_at, validation_notes, metadata
                FROM counting_sessions
                WHERE status = 'active' AND user_id = :user_id
                ORDER BY started_at DESC
            """), {'user_id': user_id})
        else:
            result = db.execute(text("""
                SELECT id, user_id, camera_id, bay_id, truck_plate, product_class_id,
                       product_count, ai_count, operator_count, started_at, ended_at,
                       duration_seconds, status, validated_by, validated_at, validation_notes, metadata
                FROM counting_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
            """))
        return [CountingSession.from_row(row) for row in result.fetchall()]

    @staticmethod
    def get_pending(db, user_id: str, limit: int = 50) -> List[CountingSession]:
        """Retorna sessões pendentes de validação."""
        result = db.execute(text("""
            SELECT id, user_id, camera_id, bay_id, truck_plate, product_class_id,
                   product_count, ai_count, operator_count, started_at, ended_at,
                   duration_seconds, status, validated_by, validated_at, validation_notes, metadata
            FROM counting_sessions
            WHERE status = 'pending_validation' AND user_id = :user_id
            ORDER BY started_at ASC
            LIMIT :limit
        """), {'user_id': user_id, 'limit': limit})
        return [CountingSession.from_row(row) for row in result.fetchall()]

    @staticmethod
    def get_by_id(db, session_id: str) -> Optional[CountingSession]:
        """Retorna sessão por ID."""
        result = db.execute(text("""
            SELECT id, user_id, camera_id, bay_id, truck_plate, product_class_id,
                   product_count, ai_count, operator_count, started_at, ended_at,
                   duration_seconds, status, validated_by, validated_at, validation_notes, metadata
            FROM counting_sessions
            WHERE id = :session_id
        """), {'session_id': session_id})
        row = result.fetchone()
        return CountingSession.from_row(row) if row else None

    @staticmethod
    def get_history(db, user_id: str, limit: int = 50, offset: int = 0,
                     status_filter: Optional[str] = None) -> List[CountingSession]:
        """Retorna histórico de sessões paginado."""
        params = {'user_id': user_id, 'limit': limit, 'offset': offset}
        status_clause = ""
        if status_filter:
            status_clause = "AND status = :status"
            params['status'] = status_filter

        result = db.execute(text(f"""
            SELECT id, user_id, camera_id, bay_id, truck_plate, product_class_id,
                   product_count, ai_count, operator_count, started_at, ended_at,
                   duration_seconds, status, validated_by, validated_at, validation_notes, metadata
            FROM counting_sessions
            WHERE user_id = :user_id {status_clause}
            ORDER BY started_at DESC
            LIMIT :limit OFFSET :offset
        """), params)
        return [CountingSession.from_row(row) for row in result.fetchall()]

    @staticmethod
    def create(db, user_id: str, camera_id: Optional[str] = None,
                bay_id: Optional[str] = None, **kwargs) -> CountingSession:
        """Cria nova sessão de contagem."""
        import uuid
        session_id = str(uuid.uuid4())

        result = db.execute(text("""
            INSERT INTO counting_sessions (id, user_id, camera_id, bay_id, status)
            VALUES (:id, :user_id, :camera_id, :bay_id, 'active')
            RETURNING id, user_id, camera_id, bay_id, status, started_at
        """), {'id': session_id, 'user_id': user_id, 'camera_id': camera_id, 'bay_id': bay_id})

        db.commit()
        return SessionRepository.get_by_id(db, session_id)

    @staticmethod
    def update(db, session_id: str, **kwargs) -> Optional[CountingSession]:
        """Atualiza sessão."""
        set_clauses = []
        params = {'session_id': session_id}

        for key, value in kwargs.items():
            if key in ['status', 'truck_plate', 'bay_id', 'validated_by', 'validation_notes']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            elif key in ['product_count', 'ai_count', 'operator_count', 'duration_seconds']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            elif key in ['ended_at', 'validated_at']:
                set_clauses.append(f"{key} = :{key}")
                params[key] = value

        if set_clauses:
            query = f"UPDATE counting_sessions SET {', '.join(set_clauses)} WHERE id = :session_id RETURNING *"
            result = db.execute(text(query), params)
            db.commit()
            return SessionRepository.get_by_id(db, session_id)
        return None

    @staticmethod
    def get_stats(db, user_id: str) -> dict:
        """Retorna estatísticas agregadas."""
        result = db.execute(text("""
            SELECT
                COUNT(CASE WHEN started_at >= CURRENT_DATE THEN 1 END) as total_today,
                COALESCE(SUM(CASE WHEN started_at >= CURRENT_DATE THEN product_count ELSE 0 END), 0) as products_today,
                COUNT(*) as trucks_today,
                COALESCE(AVG(CASE WHEN duration_seconds IS NOT NULL THEN duration_seconds ELSE NULL END) / 60, 0) as avg_duration_minutes,
                COUNT(CASE WHEN status = 'pending_validation' THEN 1 END) as pending_count,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_count
            FROM counting_sessions
            WHERE user_id = :user_id
        """), {'user_id': user_id})
        row = result.fetchone()
        return {
            'total_today': row[0] or 0,
            'products_today': row[1] or 0,
            'trucks_today': row[2] or 0,
            'avg_duration_minutes': int(row[3] or 0),
            'pending_count': row[4] or 0,
            'active_count': row[5] or 0
        }

    @staticmethod
    def add_event(db, session_id: str, event_type: str,
                   class_name: Optional[str] = None, confidence: Optional[float] = None,
                   details: dict = None) -> SessionEvent:
        """Adiciona evento à sessão."""
        import uuid
        event_id = str(uuid.uuid4())

        result = db.execute(text("""
            INSERT INTO session_events (id, session_id, event_type, class_name, confidence, details)
            VALUES (:id, :session_id, :event_type, :class_name, :confidence, :details::jsonb)
            RETURNING id, session_id, event_type, class_name, confidence, occurred_at
        """), {
            'id': event_id,
            'session_id': session_id,
            'event_type': event_type,
            'class_name': class_name,
            'confidence': confidence,
            'details': details or {}
        })
        db.commit()
        return SessionEvent.from_row(result.fetchone())
