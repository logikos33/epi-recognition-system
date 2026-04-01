"""
State Machine para gerenciar estados das baias de carregamento.
Padrão State Design Pattern — estados e transições bem definidos.
"""
from enum import Enum
from typing import Optional
from datetime import datetime


class BayState(Enum):
    """Estados possíveis de uma baia de carregamento."""
    EMPTY = "empty"                   # Baia vazia, nenhum veículo
    TRUCK_PRESENT = "truck_present" # Caminhão detectado, sessão iniciada
    COUNTING = "counting"             # Contando produtos
    PENDING_VALIDATION = "pending_validation"  # Sessão encerrada, aguardando validação


class BayStateMachine:
    """
    Máquina de estados para gerenciar baia individual.

    Estado por baia (camera_id): BayState
    Histórico de últimos eventos para timeout de ausência
    """

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.state = BayState.EMPTY
        self.current_session_id: Optional[str] = None
        self.truck_last_seen: Optional[datetime] = None

    def transition_to(self, new_state: BayState, session_id: Optional[str] = None) -> bool:
        """
        Transiciona para novo estado se válido.

        Retorna True se transição foi executada, False caso contrário.
        """
        valid_transitions = {
            BayState.EMPTY: [BayState.TRUCK_PRESENT],
            BayState.TRUCK_PRESENT: [BayState.COUNTING, BayState.EMPTY],
            BayState.COUNTING: [BayState.TRUCK_PRESENT, BayState.PENDING_VALIDATION],
            BayState.PENDING_VALIDATION: [BayState.EMPTY]
        }

        if new_state in valid_transitions.get(self.state, []):
            old_state = self.state
            self.state = new_state
            if session_id:
                self.current_session_id = session_id
            return True

        return False

    def get_seconds_since_last_truck(self) -> Optional[int]:
        """Retorna segundos desde última detecção de caminhão."""
        if self.truck_last_seen is None:
            return None

        delta = datetime.now() - self.truck_last_seen
        return int(delta.total_seconds())

    def update_truck_detected(self):
        """Atualiza timestamp da última detecção de caminhão."""
        self.truck_last_seen = datetime.now()
