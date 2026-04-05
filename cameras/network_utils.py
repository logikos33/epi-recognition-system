"""
EPI Monitor — Network Utilities for Camera Connections

Utilities for handling DNS resolution, network reachability, and RTSP URL
generation in industrial environments (Ambev, factories, etc.).

Supports:
- Direct IP addresses
- DNS hostnames
- mDNS/Bonjour (.local domains)
- Network segment detection
- Multi-layer connectivity testing
"""

import socket
import subprocess
import ipaddress
import time
from typing import Optional, Tuple, Dict, List


class NetworkUtils:
    """Utilitários de rede para conexão com câmeras IP industriais."""

    CONNECTION_TIMEOUT = 10  # segundos
    DNS_TIMEOUT = 3          # segundos para resolução DNS

    @staticmethod
    def resolve_host(host: str) -> Tuple[str, str]:
        """
        Resolve hostname para IP. Suporta:
        - IPs diretos (192.168.1.100) — retorna diretamente
        - Hostnames locais (dvr.local) — usa mDNS
        - Hostnames DNS (dvr.empresa.com) — usa DNS padrão

        Retorna: (ip_resolvido, metodo_usado)

        Levanta: ConnectionError se não conseguir resolver
        """
        # Verificar se já é um IP válido
        try:
            ipaddress.ip_address(host)
            return host, 'direct_ip'
        except ValueError:
            pass

        # Tentar resolução DNS com timeout curto
        try:
            socket.setdefaulttimeout(NetworkUtils.DNS_TIMEOUT)
            ip = socket.gethostbyname(host)
            return ip, 'dns'
        except socket.gaierror:
            pass

        # Tentar mDNS para domínios .local
        if host.endswith('.local'):
            try:
                result = subprocess.run(
                    ['avahi-resolve', '-n', host],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    ip = result.stdout.strip().split()[-1]
                    return ip, 'mdns'
            except (subprocess.SubprocessError, FileNotFoundError):
                # avahi não disponível — tentar getaddrinfo como fallback
                try:
                    infos = socket.getaddrinfo(host, None)
                    if infos:
                        return infos[0][4][0], 'mdns_fallback'
                except socket.gaierror:
                    pass

        raise ConnectionError(
            f"Não foi possível resolver '{host}'. "
            f"Verifique se o hostname está correto ou use o IP diretamente."
        )

    @staticmethod
    def validate_network_reachability(ip: str, port: int,
                                       timeout: int = 5) -> Dict:
        """
        Verifica alcançabilidade em duas camadas:
        1. ICMP ping (se disponível)
        2. TCP socket na porta especificada

        Retorna dict com resultados.
        """
        result = {
            'ip': ip,
            'port': port,
            'ping_success': False,
            'port_open': False,
            'latency_ms': None,
            'error': None
        }

        # Camada 1: ICMP Ping
        try:
            start = time.time()
            ping_result = subprocess.run(
                ['ping', '-c', '2', '-W', '2', ip],
                capture_output=True, timeout=8
            )
            result['ping_success'] = ping_result.returncode == 0
            result['latency_ms'] = round((time.time() - start) * 1000, 1)
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            result['ping_success'] = False

        # Camada 2: TCP Socket
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            connect_result = sock.connect_ex((ip, port))
            sock.close()
            result['port_open'] = connect_result == 0
            if not result['latency_ms']:
                result['latency_ms'] = round((time.time() - start) * 1000, 1)
        except Exception as e:
            result['port_open'] = False
            result['error'] = str(e)

        return result

    @staticmethod
    def detect_network_segment(ip: str) -> Dict:
        """
        Detecta informações sobre o segmento de rede da câmera.
        Útil para diagnóstico de problemas de roteamento.
        """
        try:
            ip_obj = ipaddress.ip_address(ip)
            info = {
                'ip': ip,
                'is_private': ip_obj.is_private,
                'is_loopback': ip_obj.is_loopback,
                'network_class': None,
                'likely_segment': None
            }

            # Detectar classe e segmento provável
            if ip.startswith('192.168.'):
                info['network_class'] = 'Class C Private'
                info['likely_segment'] = 'LAN doméstica/escritório'
            elif ip.startswith('10.'):
                info['network_class'] = 'Class A Private'
                info['likely_segment'] = 'Rede corporativa/industrial'
            elif ip.startswith('172.'):
                second_octet = int(ip.split('.')[1])
                if 16 <= second_octet <= 31:
                    info['network_class'] = 'Class B Private'
                    info['likely_segment'] = 'Rede corporativa'

            return info
        except ValueError:
            return {'ip': ip, 'error': 'IP inválido'}

    @staticmethod
    def get_suggested_rtsp_urls(manufacturer: str, ip: str, port: int,
                                 username: str, password: str,
                                 channel: int = 1,
                                 subtype: int = 0) -> List[str]:
        """
        Retorna lista de URLs RTSP a tentar, em ordem de prioridade,
        baseado no fabricante.
        """
        urls = []
        ch = channel
        sub = subtype

        if manufacturer.lower() in ['intelbras', 'dahua']:
            urls = [
                f"rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel={ch}&subtype={sub}",
                f"rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel={ch}&subtype=0",
            ]
        elif manufacturer.lower() == 'hikvision':
            ch_code = ch * 100 + (sub + 1)
            urls = [
                f"rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/{ch_code}",
                f"rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/{ch}01",
                f"rtsp://{username}:{password}@{ip}:{port}/h264/ch{ch}/{'main' if sub==0 else 'sub'}/av_stream",
            ]
        elif manufacturer.lower() == 'axis':
            urls = [
                f"rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp?videocodec=h264",
                f"rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp",
            ]
        else:
            # Genérico — testar URLs comuns em ordem
            urls = [
                f"rtsp://{username}:{password}@{ip}:{port}/stream1",
                f"rtsp://{username}:{password}@{ip}:{port}/stream",
                f"rtsp://{username}:{password}@{ip}:{port}/h264",
                f"rtsp://{username}:{password}@{ip}:{port}/live",
                f"rtsp://{username}:{password}@{ip}:{port}/video1",
                f"rtsp://{username}:{password}@{ip}:{port}/0",
                f"rtsp://{username}:{password}@{ip}:8554/stream",
            ]

        return urls
