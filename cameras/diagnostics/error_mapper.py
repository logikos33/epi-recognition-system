"""
EPI Monitor — Camera Error Mapper

Mapeia exceções técnicas para mensagens em português.
"""

ERROR_MAP = {
    'Connection refused': 'Porta RTSP fechada. Verificar se DVR está ligado.',
    'Authentication failed': 'Usuário ou senha incorretos.',
    '401': 'Usuário ou senha incorretos.',
    '403': 'Acesso negado. Verificar permissões do usuário.',
    'timed out': 'Dispositivo não respondeu. Verificar IP e rede.',
    'Timeout': 'Dispositivo não respondeu. Verificar IP e rede.',
    'Invalid data': 'Stream em formato não suportado. Tentar outro protocolo.',
    'No route to host': 'Sem rota de rede. Verificar se câmera está na mesma rede.',
    'Name or service not known': 'Hostname não encontrado. Usar IP diretamente.',
    'Network unreachable': 'Rede não alcançável. Verificar configuração de rede.',
    'Connection reset': 'Conexão resetada pelo dispositivo.',
}


def map_error_to_message(error: Exception) -> str:
    """
    Retorna mensagem amigável em português para o erro.

    Tenta encontrar correspondência no ERROR_MAP.
    Se não encontrar, retorna mensagem genérica.
    """
    error_str = str(error)

    for key, message in ERROR_MAP.items():
        if key in error_str:
            return message

    # Mensagem genérica
    return f"Erro de conexão: {error_str}"


def get_diagnostics_suggestions(error_message: str) -> list:
    """
    Retorna sugestões de diagnóstico baseado na mensagem de erro.
    """
    suggestions = []

    if 'porta' in error_message.lower() or 'port' in error_message.lower():
        suggestions.append("Verificar se a porta RTSP está correta (padrão: 554)")
        suggestions.append("Verificar firewall no dispositivo ou na rede")

    if 'usuário' in error_message.lower() or 'senha' in error_message.lower() or 'auth' in error_message.lower():
        suggestions.append("Verificar credenciais no manual do DVR")
        suggestions.append("Tentar usuário 'admin' com senha em branco")

    if 'ip' in error_message.lower() or 'rede' in error_message.lower() or 'network' in error_message.lower():
        suggestions.append("Fazer ping no IP do dispositivo")
        suggestions.append("Verificar se está na mesma rede/VLAN")
        suggestions.append("Tentar acessar interface web do DVR")

    if len(suggestions) == 0:
        suggestions.append("Consultar manual do dispositivo")
        suggestions.append("Verificar logs do sistema")

    return suggestions
