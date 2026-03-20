#!/usr/bin/env python3
"""Teste simples de importação"""
import sys

print("Python version:", sys.version)
print("\n🧪 Testando imports...")

try:
    import flask
    print("✅ flask:", flask.__version__)
except Exception as e:
    print("❌ flask:", e)

try:
    import flask_cors
    print("✅ flask_cors")
except Exception as e:
    print("❌ flask_cors:", e)

try:
    import numpy as np
    print("✅ numpy:", np.__version__)
except Exception as e:
    print("❌ numpy:", e)

try:
    import cv2
    print("✅ opencv:", cv2.__version__)
except Exception as e:
    print("❌ opencv:", e)

try:
    from PIL import Image
    print("✅ PIL")
except Exception as e:
    print("❌ PIL:", e)

try:
    from ultralytics import YOLO
    print("✅ ultralytics YOLO")
except Exception as e:
    print("❌ ultralytics:", e)

try:
    from pydantic import BaseModel
    print("✅ pydantic")
except Exception as e:
    print("❌ pydantic:", e)

print("\n✨ Teste concluído!")
