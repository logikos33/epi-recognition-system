"""
Rules Engine — Máquina de estados para processamento de detecções YOLO.

Chamado pelo YOLOProcessor a cada frame processado.
Gerencia sessões de contagem, cooldowns e estado das baias.

Design Pattern: State Machine + Observer
"""
import threading
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import text
from backend.database import get_db_context

from .models import Rule
from .repository import RulesRepository, SessionRepository
from .state_machine import BayStateMachine, BayState

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Máquina de estados para processamento de detecções YOLO.

    Gerencia:
    - Estado por câmera (BayStateMachine)
    - Sessões ativas por câmera
    - Cooldowns por regra+câmera
    - Execução de ações (iniciar/encerrar sessão, contar produtos)

    Thread-safe com locks para ambiente multi-thread.
    """

    # Estado global: { camera_id: BayStateMachine }
    _bay_states: Dict[str, BayStateMachine] = {}
    # Sessões ativas: { camera_id: session_id }
    _active_sessions: Dict[str, str] = {}

    # Cooldowns: { (rule_id, camera_id): last_triggered_timestamp }
    _cooldowns: Dict[tuple, str] = {}

    # Lock para thread-safety
    _lock = threading.Lock()

    def __init__(self):
        self._logger = logger

    def process_detections(self, camera_id: str, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa lista de detecções de um frame.

        Chamado pelo YOLOProcessor a cada frame processado.

        detections: [{ class_name, confidence, bbox }]
        Retorna: lista de ações executadas [{ action_type, details }]
        """
        with self._lock:
            actions = []

            # Obter ou criar state machine para esta câmera
            if camera_id not in self._bay_states:
                self._bay_states[camera_id] = BayStateMachine(camera_id)

            state_machine = self._bay_states[camera_id]

            # Obter regras ativas para esta câmera
            with get_db_context() as db:
                active_rules = RulesRepository.get_active(db, camera_id)

            # Processar cada regra
            for rule in active_rules:
                # Verificar cooldown
                rule_key = (rule.id, camera_id)
                if rule_key in self._cooldowns:
                    last_triggered = self._cooldowns[rule_key]
                    if time.time() - last_triggered < rule.cooldown_seconds:
                        continue  # Ainda em cooldown

                if rule.event_type == 'detection':
                    action = self._process_detection_rule(rule, camera_id, detections, state_machine)
                    if action:
                        actions.append(action)
                        self._set_cooldown(rule.id, camera_id, rule.cooldown_seconds)

                elif rule.event_type == 'no_detection':
                    action = self._process_no_detection_rule(rule, camera_id, detections, state_machine)
                    if action:
                        actions.append(action)
                        self._set_cooldown(rule.id, camera_id, rule.cooldown_seconds)

            return actions

    def _process_detection_rule(self, rule: Rule, camera_id: str,
                                  detections: List[Dict[str, Any]], state_machine: BayStateMachine) -> Optional[Dict]:
        """Processa regra de detecção."""
        target_class = rule.event_config.get('class_name')
        min_confidence = rule.min_confidence

        # Encontrar detecções que correspondem
        matching = [
            d for d in detections
            if d.get('class_name') == target_class and d.get('confidence', 0) >= min_confidence
        ]

        if not matching:
            return None

        detection = matching[0]  # Usar primeira detecção correspondente

        # Executar ação baseada no action_type
        if rule.action_type == 'start_session':
            return self._action_start_session(camera_id, rule, detection, state_machine)

        elif rule.action_type == 'count_product':
            return self._action_count_product(camera_id, detection, rule)

        elif rule.action_type == 'associate_plate':
            return self._action_associate_plate(camera_id, detection)

        elif rule.action_type == 'alert':
            return self._action_create_alert(camera_id, detection, rule)

        return None

    def _process_no_detection_rule(self, rule: Rule, camera_id: str,
                                   detections: List[Dict[str, Any]], state_machine: BayStateMachine) -> Optional[Dict]:
        """Processa regra de ausência (ex: baia vazia por 30s)."""
        target_class = rule.event_config.get('class_name')

        # Verificar se classe alvo está presente
        present = any(d.get('class_name') == target_class for d in detections)

        if present:
            # Classe detectada — reset timer de ausência
            return None
        else:
            # Classe não detectada — verificar timeout
            absence_seconds = rule.event_config.get('absence_seconds', 30)
            seconds_since_last = state_machine.get_seconds_since_last_truck()

            if seconds_since_last is not None and seconds_since_last >= absence_seconds:
                # Timeout atingido — encerrar sessão
                return self._action_end_session(camera_id, rule, state_machine)

        return None

    def _action_start_session(self, camera_id: str, rule: Rule, detection: Dict,
                             state_machine: BayStateMachine) -> Dict:
        """Ação: Iniciar nova sessão de contagem."""
        # Verificar se já existe sessão ativa
        if camera_id in self._active_sessions:
            return {'action_type': 'session_already_exists', 'camera_id': camera_id}

        # Criar nova sessão
        with get_db_context() as db:
            # Obter user_id da câmera
            user_result = db.execute(text("""
                SELECT user_id FROM cameras WHERE id = :camera_id
                UNION
                SELECT user_id FROM ip_cameras WHERE id = :camera_id
                LIMIT 1
            """), {'camera_id': camera_id})
            user_row = user_result.fetchone()

            if not user_row:
                return {'action_type': 'error', 'error': 'Camera not found or no user associated'}

            user_id = str(user_row[0])

            # Criar sessão
            session = SessionRepository.create(db, user_id=user_id, camera_id=camera_id)

        # Atualizar state machine
        state_machine.update_truck_detected()
        state_machine.transition_to(BayState.TRUCK_PRESENT, session.id)

        # Registrar sessão ativa
        self._active_sessions[camera_id] = session.id

        # Adicionar evento de sessão iniciada
        with get_db_context() as db:
            SessionRepository.add_event(
                db, session.id, 'session_started',
                details={'detection': detection, 'rule_id': rule.id}
            )

        self._logger.info(f"✅ Session started: {session.id} for camera {camera_id}")

        return {
            'action_type': 'session_started',
            'session_id': session.id,
            'camera_id': camera_id,
            'rule_id': rule.id
        }

    def _action_end_session(self, camera_id: str, rule: Rule, state_machine: BayStateMachine) -> Dict:
        """Ação: Encerrar sessão de contagem."""
        session_id = self._active_sessions.get(camera_id)

        if not session_id:
            return {'action_type': 'no_active_session', 'camera_id': camera_id}

        # Atualizar sessão para pending_validation
        with get_db_context() as db:
            # Calcular duração
            session_result = db.execute(text("""
                SELECT started_at FROM counting_sessions WHERE id = :session_id
            """), {'session_id': session_id})

            row = session_result.fetchone()
            if row:
                started_at = row[0]
                duration_seconds = int((datetime.now() - started_at).total_seconds())

                # Calcular contagem final
                count_result = db.execute(text("""
                    SELECT product_count FROM counting_sessions WHERE id = :session_id
                """), {'session_id': session_id})

                product_count = count_result.scalar() or 0

                # Atualizar sessão
                SessionRepository.update(
                    db, session_id,
                    status='pending_validation',
                    ended_at=datetime.now(),
                    duration_seconds=duration_seconds,
                    product_count=product_count
                )

        # Adicionar evento de sessão encerrada
        with get_db_context() as db:
            SessionRepository.add_event(
                db, session_id, 'session_ended',
                details={'reason': 'absence_timeout', 'rule_id': rule.id}
            )

        # Remover da lista de ativas e resetar state machine
        del self._active_sessions[camera_id]
        state_machine.transition_to(BayState.EMPTY)

        self._logger.info(f"✅ Session ended: {session_id} for camera {camera_id}")

        return {
            'action_type': 'session_ended',
            'session_id': session_id,
            'camera_id': camera_id,
            'duration_seconds': duration_seconds,
            'product_count': product_count
        }

    def _action_count_product(self, camera_id: str, detection: Dict, rule: Rule) -> Dict:
        """Ação: Contar produto detectado."""
        session_id = self._active_sessions.get(camera_id)

        if not session_id:
            return {'action_type': 'no_active_session', 'camera_id': camera_id}

        # Incrementar contagem
        with get_db_context() as db:
            # Obter contagem atual
            result = db.execute(text("""
                SELECT product_count FROM counting_sessions WHERE id = :session_id
            """), {'session_id': session_id})

            current_count = result.scalar() or 0
            new_count = current_count + 1

            # Atualizar
            SessionRepository.update(
                db, session_id,
                product_count=new_count,
                ai_count=new_count  # IA contou
            )

            # Adicionar evento de contagem
            SessionRepository.add_event(
                db, session_id, 'count',
                class_name=detection.get('class_name'),
                confidence=detection.get('confidence'),
                details={'detection': detection, 'rule_id': rule.id}
            )

        self._logger.debug(f"📦 Product counted: session={session_id}, count={new_count}")

        return {
            'action_type': 'product_counted',
            'session_id': session_id,
            'camera_id': camera_id,
            'count': new_count
        }

    def _action_associate_plate(self, camera_id: str, detection: Dict) -> Dict:
        """Ação: Associar placa à sessão ativa."""
        session_id = self._active_sessions.get(camera_id)

        if not session_id:
            return {'action_type': 'no_active_session', 'camera_id': camera_id}

        # Extrair placa da detecção (OCR ou detecção direta)
        # Por enquanto, usar class_name como placa
        plate = detection.get('class_name', 'UNKNOWN')

        with get_db_context() as db:
            SessionRepository.update(
                db, session_id,
                truck_plate=plate
            )

            SessionRepository.add_event(
                db, session_id, 'plate_captured',
                class_name=plate,
                confidence=detection.get('confidence'),
                details={'detection': detection}
            )

        self._logger.info(f"🚛 Plate associated: session={session_id}, plate={plate}")

        return {
            'action_type': 'plate_associated',
            'session_id': session_id,
            'camera_id': camera_id,
            'plate': plate
        }

    def _action_create_alert(self, camera_id: str, detection: Dict, rule: Rule) -> Dict:
        """Ação: Criar alerta (placeholder para EPI compliance)."""
        # Por enquanto, apenas logar
        self._logger.warning(f"⚠️  Alert triggered: camera={camera_id}, detection={detection}")

        return {
            'action_type': 'alert_created',
            'camera_id': camera_id,
            'detection': detection,
            'rule_id': rule.id
        }

    def _set_cooldown(self, rule_id: str, camera_id: str, seconds: int):
        """Define cooldown para regra+câmera."""
        self._cooldowns[(rule_id, camera_id)] = time.time()


# Singleton instance
_rules_engine_instance: Optional[RulesEngine] = None


def get_rules_engine() -> RulesEngine:
    """Retorna instância singleton do RulesEngine."""
    global _rules_engine_instance
    if _rules_engine_instance is None:
        _rules_engine_instance = RulesEngine()
    return _rules_engine_instance
