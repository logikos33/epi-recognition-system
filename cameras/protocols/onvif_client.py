"""
EPI Monitor — ONVIF Discovery

Descoberta de câmeras ONVIF via WS-Discovery.
"""

import socket
import struct
import time
from typing import List, Dict
from cameras.models import Channel


class ONVIFDiscovery:
    """Descoberta de dispositivos ONVIF na rede local."""

    MULTICAST_ADDR = '239.255.255.250'
    MULTICAST_PORT = 3702
    TIMEOUT = 5

    def discover(self) -> List[Dict]:
        """
        Envia probe WS-Discovery e coleta respostas.

        Retorna lista de dispositivos encontrados com:
        - ip, port, name, manufacturer, rtsp_url
        """
        devices = []

        # Criar socket UDP multicast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                            socket.IPPROTO_UDP)
        sock.settimeout(self.TIMEOUT)

        # Probe WS-Discovery
        probe = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope"
                   xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
  <SOAP-ENV:Header>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
    <wsa:MessageID>urn:uuid:{time.time()}</wsa:MessageID>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
  </SOAP-ENV:Header>
  <SOAP-ENV:Body>
    <wsd:Probe xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery"/>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
""".encode()

        try:
            sock.sendto(probe, (self.MULTICAST_ADDR, self.MULTICAST_PORT))

            start_time = time.time()
            while time.time() - start_time < self.TIMEOUT:
                try:
                    data, addr = sock.recvfrom(65536)
                    # Parse resposta simplificada (extrair IP)
                    devices.append({
                        'ip': addr[0],
                        'port': 80,
                        'name': f'ONVIF Device {addr[0]}',
                        'manufacturer': 'ONVIF',
                        'rtsp_url': None
                    })
                except socket.timeout:
                    break
        except Exception as e:
            pass
        finally:
            sock.close()

        return devices
