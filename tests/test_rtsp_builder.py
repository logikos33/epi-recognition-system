import pytest
from backend.rtsp_builder import RTSPBuilder

def test_build_intelbras_url():
    camera = {
        'manufacturer': 'intelbras',
        'ip': '192.168.1.100',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 1,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1'

def test_build_hikvision_url():
    camera = {
        'manufacturer': 'hikvision',
        'ip': '192.168.1.101',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 1,
        'subtype': 0
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.101:554/Streaming/Channels/101'

def test_build_generic_url():
    camera = {
        'manufacturer': 'generic',
        'ip': '192.168.1.102',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 2,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.102:554/stream2'

def test_missing_credentials():
    camera = {
        'manufacturer': 'intelbras',
        'ip': '192.168.1.100',
        'port': 554,
        'username': '',
        'password': '',
        'channel': 1,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert 'rtsp://' in url
    # When credentials are empty, @ should NOT be present (standard RTSP format)
    assert url == 'rtsp://192.168.1.100:554/cam/realmonitor?channel=1&subtype=1'