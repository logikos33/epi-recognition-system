#!/usr/bin/env python3
"""
Quick Test Script - Teste Rápido do Sistema
Execute este script para verificar se tudo está funcionando
"""
import sys
import cv2
import numpy as np
from pathlib import Path


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_success(message):
    """Print success message"""
    print(f"✅ {message}")


def print_error(message):
    """Print error message"""
    print(f"❌ {message}")


def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")


def test_python_version():
    """Test Python version"""
    print_header("1. Verificando Python")

    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 8:
        print_success("Python version OK")
        return True
    else:
        print_error("Python 3.8+ required")
        return False


def test_dependencies():
    """Test required dependencies"""
    print_header("2. Verificando Dependências")

    required_packages = [
        "cv2",
        "numpy",
        "ultralytics",
        "streamlit",
        "sqlalchemy",
        "pydantic"
    ]

    all_ok = True

    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package}: OK")
        except ImportError:
            print_error(f"{package}: FALTANDO")
            all_ok = False

    if all_ok:
        print_success("Todas as dependências instaladas")
    else:
        print_error("Instale as dependências: pip install -r requirements.txt")

    return all_ok


def test_yolo_model():
    """Test YOLO model"""
    print_header("3. Verificando Modelo YOLO")

    try:
        from ultralytics import YOLO

        print_info("Carregando modelo YOLOv8n...")

        model = YOLO('yolov8n.pt')

        print_success("Modelo carregado com sucesso")
        print_info(f"Classes: {len(model.names)}")

        return True, model

    except Exception as e:
        print_error(f"Erro ao carregar modelo: {e}")
        print_info("O modelo será baixado automaticamente na primeira execução")
        return False, None


def test_webcam():
    """Test webcam"""
    print_header("4. Testando Webcam")

    print_info("Tentando abrir webcam (ID 0)...")

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print_error("Não foi possível abrir a webcam")
        print_info("Alternativas:")
        print("  - Verifique se a webcam está conectada")
        print("  - Use câmera de celular (veja docs/CAMERA_SETUP.md)")
        return False, None

    print_success("Webcam aberta com sucesso")

    # Get webcam properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    print_info(f"Resolução: {width}x{height}")
    print_info(f"FPS: {fps}")

    # Capture a test frame
    ret, frame = cap.read()

    if not ret:
        print_error("Não foi possível capturar frame")
        cap.release()
        return False, None

    print_success("Frame capturado com sucesso")
    print_info(f"Shape: {frame.shape}")

    cap.release()

    return True, frame


def test_detection(model, frame):
    """Test object detection"""
    print_header("5. Testando Detecção de Objetos")

    if model is None or frame is None:
        print_error("Pulo do teste (modelo ou frame não disponível)")
        return False

    print_info("Processando frame...")

    try:
        results = model(frame, conf=0.5, verbose=False)

        print_success("Detecção realizada com sucesso")

        # Count detections
        if len(results) > 0:
            boxes = results[0].boxes
            if boxes is not None:
                num_detections = len(boxes)
                print_info(f"Objetos detectados: {num_detections}")

                # Show detected classes
                detected_classes = []
                for box in boxes:
                    cls_id = int(box.cls[0])
                    cls_name = results[0].names[cls_id]
                    conf = float(box.conf[0])
                    detected_classes.append(f"{cls_name} ({conf:.2f})")

                if detected_classes:
                    print("  Detectados:")
                    for cls in detected_classes[:5]:  # Show first 5
                        print(f"    - {cls}")
            else:
                print_info("Nenhum objeto detectado")
        else:
            print_info("Nenhum resultado")

        return True

    except Exception as e:
        print_error(f"Erro na detecção: {e}")
        return False


def test_database():
    """Test database connection"""
    print_header("6. Testando Banco de Dados")

    try:
        from services.database_service import get_database_service

        print_info("Conectando ao banco de dados...")

        db = get_database_service()

        print_success("Conexão OK")

        # Try to get cameras
        cameras = db.get_all_cameras()
        print_info(f"Câmeras configuradas: {len(cameras)}")

        return True

    except Exception as e:
        print_error(f"Erro no banco de dados: {e}")
        print_info("Usando SQLite para desenvolvimento")
        return False


def test_storage():
    """Test storage directories"""
    print_header("7. Verificando Diretórios de Armazenamento")

    storage_dirs = [
        "storage",
        "storage/images",
        "storage/annotated",
        "storage/reports"
    ]

    all_ok = True

    for dir_path in storage_dirs:
        path = Path(dir_path)
        if path.exists():
            print_success(f"{dir_path}: OK")
        else:
            print_info(f"Criando: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
            print_success(f"{dir_path}: CRIADO")

    return all_ok


def main():
    """Main test function"""
    print("\n" + "🧪" * 30)
    print("  EPI RECOGNITION SYSTEM - QUICK TEST")
    print("🧪" * 30)

    results = {}

    # Run tests
    results['python'] = test_python_version()
    results['dependencies'] = test_dependencies()
    results['yolo'], model = test_yolo_model()
    results['webcam'], frame = test_webcam()

    if model and frame:
        results['detection'] = test_detection(model, frame)

    results['database'] = test_database()
    results['storage'] = test_storage()

    # Summary
    print_header("RESUMO DOS TESTES")

    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name.upper():15} {status}")

    print("\n" + "=" * 60)
    print(f"  Total: {passed_tests}/{total_tests} testes passaram")
    print("=" * 60 + "\n")

    # Recommendations
    if passed_tests == total_tests:
        print_success("🎉 Todos os testes passaram! Sistema pronto para uso.")
        print("\nPróximos passos:")
        print("  1. Configure uma câmera: python main.py camera --camera-id 0")
        print("  2. Abra o dashboard: python main.py dashboard")
        print("  3. Ou use câmera de celular: veja docs/CAMERA_SETUP.md")
    else:
        print_error("Alguns testes falharam. Veja acima para detalhes.")

        if not results['dependencies']:
            print("\n💡 Execute: pip install -r requirements.txt")

        if not results['webcam']:
            print("\n💡 Verifique a webcam ou use câmera de celular")
            print("   Veja: docs/CAMERA_SETUP.md")

    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
