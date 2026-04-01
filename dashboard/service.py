"""
Dashboard Service - Queries agregadas para KPIs e gráficos.

Fornece dados estatísticos para o Dashboard:
- KPIs agregados por período
- Séries temporais para gráficos
- Distribuições e contagens
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from backend.database import get_db_context

import logging

logger = logging.getLogger(__name__)


class DashboardService:
    """Serviço para dados agregados do Dashboard."""

    @staticmethod
    def get_kpis(user_id: Optional[str] = None, period: str = "today") -> Dict[str, Any]:
        """
        Retorna KPIs agregados por período.

        Args:
            user_id: ID do usuário (opcional, para filtrar por usuário)
            period: Período de agregação (today, 7days, 30days, all)

        Returns:
            Dict com KPIs: sessions_total, products_total, trucks_total,
            avg_duration_minutes, pending_validation, active_sessions,
            accuracy_rate, period
        """
        with get_db_context() as db:
            # Determinar data limite baseada no período
            if period == "today":
                date_filter = "started_at >= CURRENT_DATE"
            elif period == "7days":
                date_filter = "started_at >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == "30days":
                date_filter = "started_at >= CURRENT_DATE - INTERVAL '30 days'"
            else:  # all
                date_filter = "1=1"

            user_filter = f"AND user_id = '{user_id}'" if user_id else ""

            # Query principal (sem FILTER, usando CASE WHEN)
            query = f"""
                SELECT
                    COUNT(CASE WHEN {date_filter} THEN 1 END) as sessions_total,
                    COALESCE(SUM(CASE WHEN {date_filter} THEN product_count ELSE 0 END), 0) as products_total,
                    COUNT(CASE WHEN {date_filter} THEN 1 END) as trucks_total,
                    COALESCE(AVG(CASE WHEN duration_seconds IS NOT NULL AND {date_filter} THEN duration_seconds ELSE NULL END) / 60, 0) as avg_duration_minutes,
                    COUNT(CASE WHEN status = 'pending_validation' THEN 1 END) as pending_validation,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_sessions
                FROM counting_sessions
                WHERE 1=1 {user_filter}
            """

            result = db.execute(text(query))
            row = result.fetchone()

            # Calcular accuracy rate (compara IA vs operador)
            accuracy_query = f"""
                SELECT
                    COUNT(CASE WHEN operator_count IS NOT NULL THEN 1 END) as total_validated,
                    COUNT(CASE WHEN operator_count IS NOT NULL AND ABS(operator_count - ai_count) <= 1 THEN 1 END) as accurate
                FROM counting_sessions
                WHERE status = 'validated' {user_filter} AND {date_filter}
            """

            accuracy_result = db.execute(text(accuracy_query))
            acc_row = accuracy_result.fetchone()

            accuracy_rate = 0.0
            if acc_row and acc_row[0] and acc_row[0] > 0:
                accuracy_rate = round((acc_row[1] / acc_row[0]) * 100, 1)

            return {
                "sessions_total": row[0] or 0,
                "products_total": int(row[1] or 0),
                "trucks_total": row[2] or 0,
                "avg_duration_minutes": int(row[3] or 0),
                "pending_validation": row[4] or 0,
                "active_sessions": row[5] or 0,
                "accuracy_rate": accuracy_rate,
                "period": period
            }

    @staticmethod
    def get_products_per_hour(target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Retorna contagem de produtos por hora para um dado dia.

        Args:
            target_date: Data alvo (default: hoje)

        Returns:
            Lista de dicts: [{ hour: 14, count: 47 }, ...]
        """
        with get_db_context() as db:
            date_str = target_date or date.today()

            query = """
                SELECT
                    EXTRACT(HOUR FROM started_at) as hour,
                    COALESCE(SUM(product_count), 0) as count
                FROM counting_sessions
                WHERE DATE(started_at) = :date
                GROUP BY hour
                ORDER BY hour
            """

            result = db.execute(text(query), {"date": date_str})

            return [
                {"hour": int(row[0]), "count": int(row[1] or 0)}
                for row in result.fetchall()
            ]

    @staticmethod
    def get_sessions_per_bay(user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna número de sessões por baia.

        Args:
            user_id: ID do usuário (opcional)
            limit: Número máximo de baias a retornar

        Returns:
            Lista de dicts: [{ bay_id: "Baia 1", sessions: 42 }, ...]
        """
        with get_db_context() as db:
            user_filter = f"AND user_id = '{user_id}'" if user_id else ""

            query = f"""
                SELECT
                    COALESCE(bay_id, 'Não identificada') as bay_id,
                    COUNT(*) as sessions
                FROM counting_sessions
                WHERE bay_id IS NOT NULL {user_filter}
                GROUP BY bay_id
                ORDER BY sessions DESC
                LIMIT :limit
            """

            result = db.execute(text(query), {"limit": limit})

            return [
                {"bay_id": row[0], "sessions": row[1]}
                for row in result.fetchall()
            ]

    @staticmethod
    def get_confidence_distribution() -> List[Dict[str, Any]]:
        """
        Retorna distribuição de confiança das detecções.

        Returns:
            Lista de dicts: [{ range: "90-100%", count: 1234 }, ...]
        """
        with get_db_context() as db:
            # Buscar confianças dos eventos
            query = """
                SELECT
                    CASE
                        WHEN confidence >= 0.9 THEN '90-100%'
                        WHEN confidence >= 0.7 THEN '70-90%'
                        WHEN confidence >= 0.5 THEN '50-70%'
                        ELSE '<50%'
                    END as range,
                    COUNT(*) as count
                FROM session_events
                WHERE confidence IS NOT NULL
                GROUP BY range
                ORDER BY
                    CASE range
                        WHEN '90-100%' THEN 1
                        WHEN '70-90%' THEN 2
                        WHEN '50-70%' THEN 3
                        ELSE 4
                    END
            """

            result = db.execute(text(query))

            return [
                {"range": row[0], "count": row[1]}
                for row in result.fetchall()
            ]

    @staticmethod
    def get_recent_alerts(limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna alertas recentes.

        NOTA: Por enquanto retorna placeholders.
        Implementação completa viria com sistema de alertas.

        Args:
            limit: Número máximo de alertas

        Returns:
            Lista de dicts: [{ id, time, camera, type, message }, ...]
        """
        # Placeholder - sistema de alertas não implementado ainda
        return [
            {
                "id": 1,
                "time": datetime.now().strftime("%H:%M"),
                "camera": "Sistema",
                "type": "info",
                "message": "Sistema de alertas em desenvolvimento"
            }
        ]

    @staticmethod
    def get_recent_validated_sessions(user_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retorna últimas sessões validadas.

        Args:
            user_id: ID do usuário (opcional)
            limit: Número máximo de sessões

        Returns:
            Lista de dicts com sessões validadas
        """
        with get_db_context() as db:
            user_filter = f"AND user_id = '{user_id}'" if user_id else ""

            query = f"""
                SELECT
                    id, truck_plate, bay_id, camera_id,
                    ai_count, operator_count,
                    validated_at, status
                FROM counting_sessions
                WHERE status = 'validated' {user_filter}
                ORDER BY validated_at DESC
                LIMIT :limit
            """

            result = db.execute(text(query), {"limit": limit})

            return [
                {
                    "id": str(row[0]),
                    "truck_plate": row[1],
                    "bay_id": row[2],
                    "camera_id": row[3],
                    "ai_count": row[4] or 0,
                    "operator_count": row[5],
                    "validated_at": row[6].isoformat() if row[6] else None,
                    "status": row[7]
                }
                for row in result.fetchall()
            ]
