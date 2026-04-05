#!/usr/bin/env python3
"""
EPI Monitor — Worker de treinamento YOLOv8 isolado.

Executa em subprocess separado com prioridade baixa (nice -n 15).
NÃO importa Flask — processo completamente independente do servidor.
Comunicação com o processo pai via arquivo JSON de progresso.
"""

import sys
import os
import json
import time


def run_training(config_path: str):
    """Executa o treinamento YOLO com recursos controlados."""

    with open(config_path) as f:
        config = json.load(f)

    job_id = config['job_id']
    progress_file = config['progress_file']
    os.makedirs(os.path.dirname(progress_file), exist_ok=True)

    def update(epoch: int, total: int, metrics: dict = None, status: str = 'running'):
        data = {
            'job_id': job_id,
            'status': status,
            'current_epoch': epoch,
            'total_epochs': total,
            'progress': int((epoch / total) * 100) if total > 0 else 0,
            'metrics': metrics or {},
            'updated_at': time.time(),
        }
        with open(progress_file, 'w') as f:
            json.dump(data, f)

    try:
        # Prioridade baixa — sistema continua responsivo
        try:
            os.nice(15)
        except (AttributeError, PermissionError):
            pass

        # Limitar threads do PyTorch/numpy para não usar todos os cores
        workers = config.get('workers', 2)
        os.environ['OMP_NUM_THREADS'] = str(workers)
        os.environ['MKL_NUM_THREADS'] = str(workers)
        os.environ['OPENBLAS_NUM_THREADS'] = str(workers)

        import torch
        torch.set_num_threads(workers)

        from ultralytics import YOLO

        epochs = config['epochs']
        model = YOLO(f"{config['model_size']}.pt")
        update(0, epochs, status='running')

        def on_epoch_end(trainer):
            metrics = {
                'mAP50': float(trainer.metrics.get('metrics/mAP50(B)', 0)),
                'precision': float(trainer.metrics.get('metrics/precision(B)', 0)),
                'recall': float(trainer.metrics.get('metrics/recall(B)', 0)),
                'box_loss': float(trainer.metrics.get('train/box_loss', 0)),
            }
            update(trainer.epoch + 1, epochs, metrics)

        model.add_callback('on_train_epoch_end', on_epoch_end)

        results = model.train(
            data=config['dataset_yaml'],
            epochs=epochs,
            batch=config.get('batch', 4),
            workers=workers,
            imgsz=config.get('imgsz', 640),
            device='cpu',
            patience=config.get('patience', 20),
            cache=False,
            amp=False,
            project=config['output_dir'],
            name=job_id,
            exist_ok=True,
            verbose=False,
        )

        best_pt = os.path.join(config['output_dir'], job_id, 'weights', 'best.pt')
        final_metrics = {
            'mAP50': float(results.results_dict.get('metrics/mAP50(B)', 0)),
            'precision': float(results.results_dict.get('metrics/precision(B)', 0)),
            'recall': float(results.results_dict.get('metrics/recall(B)', 0)),
        }

        with open(progress_file, 'r') as f:
            data = json.load(f)
        data.update({
            'status': 'completed',
            'current_epoch': epochs,
            'progress': 100,
            'metrics': final_metrics,
            'model_path': best_pt,
            'updated_at': time.time(),
        })
        with open(progress_file, 'w') as f:
            json.dump(data, f)

    except Exception as e:
        with open(progress_file, 'w') as f:
            json.dump({
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
                'updated_at': time.time(),
            }, f)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python train_worker.py <config.json>")
        sys.exit(1)
    run_training(sys.argv[1])
