"""
EPI Monitor — Camera Diagnostics

Módulos de diagnóstico de conectividade e mapeamento de erros.
"""

from .error_mapper import map_error_to_message, get_diagnostics_suggestions
from .connectivity import ConnectivityDiagnostic

__all__ = ['map_error_to_message', 'get_diagnostics_suggestions', 'ConnectivityDiagnostic']
