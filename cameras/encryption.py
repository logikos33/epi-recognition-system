"""
EPI Monitor — Camera Encryption

Criptografia de senhas de câmeras usando Fernet (AES-128).
"""

from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)


class CameraEncryption:
    """Adapter Pattern — criptografia de senhas de câmeras."""

    def __init__(self):
        key = os.environ.get('CAMERA_SECRET_KEY')
        if not key:
            raise ValueError("CAMERA_SECRET_KEY não definida no .env")
        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, password: str) -> str:
        """Criptografa senha."""
        if not password:
            return ''
        return self.fernet.encrypt(password.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Descriptografa senha."""
        if not encrypted:
            return ''
        return self.fernet.decrypt(encrypted.encode()).decode()


# Instância singleton segura
_encryption = None


def get_encryption() -> CameraEncryption:
    """Retorna instância singleton de CameraEncryption."""
    global _encryption
    if _encryption is None:
        _encryption = CameraEncryption()
    return _encryption
