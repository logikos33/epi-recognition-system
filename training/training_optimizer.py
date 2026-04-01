"""
EPI Monitor — Gerenciador de recursos para treinamento YOLO.
Garante que o treinamento não trave o sistema operacional.

Design Pattern: Strategy — configuração adaptada à máquina atual.
"""

import os
import sys
import subprocess
import threading
from typing import Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class TrainingResourceManager:
    """Calcula configurações seguras para não travar a máquina durante o treino."""

    MAX_CPU_PERCENT = 60
    MAX_MEMORY_PERCENT = 70

    @staticmethod
    def get_safe_worker_count() -> int:
        """Retorna número de workers que deixa pelo menos 2 cores livres."""
        total = os.cpu_count() or 4
        return max(1, total // 2)

    @staticmethod
    def get_safe_batch_size(model_size: str) -> int:
        """Batch size conservador baseado na RAM disponível."""
        if HAS_PSUTIL:
            available_gb = psutil.virtual_memory().available / (1024 ** 3)
        else:
            available_gb = 4.0

        mapping = {
            'yolov8n': 8 if available_gb > 4 else 4,
            'yolov8s': 6 if available_gb > 6 else 4,
            'yolov8m': 4 if available_gb > 8 else 2,
        }
        return mapping.get(model_size, 4)

    @staticmethod
    def get_training_config(preset: str, model_size: str) -> dict:
        """
        Retorna configuração otimizada para o preset e modelo solicitados.
        Estima tempo baseado nos recursos reais da máquina.
        """
        workers = TrainingResourceManager.get_safe_worker_count()
        batch = TrainingResourceManager.get_safe_batch_size(model_size)

        configs = {
            'fast': {
                'epochs': 50,
                'workers': workers,
                'batch': batch,
                'imgsz': 640,
                'patience': 10,
                'cache': False,
                'amp': False,
                'estimated_minutes': max(10, workers * 8),
            },
            'balanced': {
                'epochs': 100,
                'workers': workers,
                'batch': batch,
                'imgsz': 640,
                'patience': 20,
                'cache': False,
                'amp': False,
                'estimated_minutes': max(20, workers * 15),
            },
            'quality': {
                'epochs': 150,
                'workers': workers,
                'batch': max(2, batch - 2),
                'imgsz': 640,
                'patience': 30,
                'cache': False,
                'amp': False,
                'estimated_minutes': max(40, workers * 25),
            },
        }
        return configs.get(preset, configs['balanced'])

    @staticmethod
    def set_process_low_priority(pid: Optional[int] = None):
        """Define prioridade baixa para não competir com outros processos."""
        if not HAS_PSUTIL:
            return
        try:
            process = psutil.Process(pid or os.getpid())
            if sys.platform == 'darwin':
                process.nice(10)
            elif sys.platform.startswith('linux'):
                process.nice(15)
                subprocess.run(
                    ['ionice', '-c', '3', '-p', str(process.pid)],
                    capture_output=True
                )
        except Exception:
            pass  # Não crítico — continuar mesmo sem prioridade baixa
