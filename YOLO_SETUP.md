# 🎯 YOLO Detecção REAL - Setup

## Arquitetura Implementada

```
Frontend (Next.js) ──► API Python (Flask) ──► YOLO Service ──► Bounding Boxes
         │                      │
    Captura Imagem        Processa com YOLOv8
    Envia base64         Retorna detecções JSON
    Desenha boxes        (classe, confiança, bbox)
```

## Como Usar

### 1. Iniciar o Backend Python

```bash
cd "/Users/vitoremanuel/Documents/Logikos/CATH/Repositorio Reconhecimento de EPI "
python api_server.py
```

Você deve ver:
```
╔═══════════════════════════════════════════════════════╗
║   EPI Recognition API Server                          ║
║   http://localhost:5000                               ║
╚═══════════════════════════════════════════════════════╝

🚀 Starting API server on http://localhost:5000
✅ YOLO service initialized successfully
```

### 2. Verificar API

Teste se a API está funcionando:
```bash
curl http://localhost:5000/health
```

Deve retornar:
```json
{
  "status": "healthy",
  "yolo_loaded": true
}
```

### 3. Iniciar o Frontend

```bash
cd "/Users/vitoremanuel/Documents/Logikos/CATH/Repositorio Reconhecimento de EPI /frontend"
npm run dev
```

### 4. Usar a Aplicação

1. Acesse: http://localhost:3000/dashboard/live
2. Clique em "Iniciar Câmera"
3. **YOLO detecta objetos reais!**

Você verá boxes como:
- 🔵 `person 92%` - Pessoas detectadas
- 🟢 `chair 87%` - Cadeiras
- 🟢 `laptop 95%` - Laptop
- 🟢 `cell phone 89%` - Celular

## O que o YOLO Detecta

YOLOv8 treinado no COCO dataset detecta **80 classes**:

### Pessoas e Animais
- person, bicycle, car, motorcycle, airplane, bus, train, truck, boat
- bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe

### Objetos
- backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard
- sports ball, kite, baseball bat, baseball glove, skateboard, surfboard
- tennis racket, bottle, wine glass, cup, fork, knife, spoon, bowl
- banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza
- donut, cake, chair, couch, potted plant, bed, dining table, toilet, tv
- laptop, mouse, remote, keyboard, cell phone, microwave, oven, toaster
- sink, refrigerator, book, clock, vase, scissors, teddy bear, hair drier
- toothbrush

## Troubleshooting

### API não responde
```bash
# Verificar se Python está rodando
ps aux | grep api_server

# Verificar logs
# Logs aparecem no terminal do Python
```

### Erro CORS
Se o frontend não conseguir conectar:
- Verifique se `flask-cors` está instalado
- A API tem `CORS(app)` habilitado

### YOLO não carrega
```bash
# Verificar se o modelo existe
ls models/*.pt

# O padrão é models/yolov8n.pt
# Baixar modelo se necessário:
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### Frontend não mostra boxes
1. Abra o console (F12)
2. Veja se há erros de fetch
3. Verifique se `http://localhost:5000/api/detect` está sendo chamado

## Performance

- **Backend Python**: ~50-100ms por frame (YOLOv8 nano)
- **Frontend**: Envia frame a cada 1 segundo
- **Latência total**: ~1-1.5 segundos entre captura e display

## Melhorias Futuras

- [ ] Streaming de vídeo RTSP ao invés de webcam
- [ ] Multiple cameras simultâneas
- [ ] Detecção de EPIs específicos (treinar modelo customizado)
- [ ] WebSocket para detecções em tempo real (sem polling)
- [ ] GPU acceleration para YOLO
