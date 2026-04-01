"""
Dashboard Blueprint para EPI Monitor.

Fornece KPIs agregados, gráficos e exportação Excel.
"""
from .routes import dashboard_bp
from .service import DashboardService

__all__ = [
    'dashboard_bp',
    'DashboardService'
]
