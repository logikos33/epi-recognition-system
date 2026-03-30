# EPI Recognition System - HLS Streaming

Sistema de reconhecimento de EPI com **streaming HLS em tempo real** e **detecção YOLO**.

[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![Flask](https://img.shields.io/badge/Flask-2.0-green)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-black)]())
[![YOLOv8](https://img.shields.io/badge/YOLOv8-latest-orange)]())
[![Railway](https://img.shields.io/badge/Railway-deployed-purple)]()

## 🎯 Features

- **5-12 Câmeras IP Simultâneas** - Suporta Intelbras, Hikvision e Generic ONVIF
- **Streaming HLS em Tempo Real** - Latência < 3 segundos
- **Detecção YOLO Contínua** - 5 FPS com bounding boxes via WebSocket
- **Auto-Restart de Streams** - Recuperação automática de falhas
- **Health Monitoring** - Métricas detalhadas de todos os streams
- **Interface Web Responsiva** - Grid de 12 câmeras (3 grandes + 9 miniaturas)

## 🏗️ Arquitetura

```
IP Cameras (RTSP) → FFmpeg → HLS Segments → Browser (hls.js)
                        ↓
                    YOLO Detection (5 FPS)
                        ↓
                  WebSocket (Socket.IO)
                        ↓
            Frontend (React/Next.js + Overlay)
```

## 🚀 Quick Start

### Pré-requisitos

- Python 3.11+
- PostgreSQL 13+
- FFmpeg (para streaming)
- Node.js 18+ (para frontend)

### Instalação

```bash
# Clone repositório
git clone <repo-url>
cd "Repositorio Reconhecimento de EPI "

# Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install

# Configurar ambiente
cp .env.example .env
# Editar .env com DATABASE_URL e JWT_SECRET_KEY
```

### Executar Localmente

```bash
# Backend (Terminal 1)
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
python api_server.py

# Frontend (Terminal 2)
cd frontend
npm run dev
```

- **API**: http://localhost:5001
- **Frontend**: http://localhost:3000
- **Health Check**: http://localhost:5001/health

## 📦 Deploy no Railway

```bash
git push origin main
```

Railway automaticamente:
1. Detecta `nixpacks.toml`
2. Instala FFmpeg
3. Build com Nixpacks (2-3 min)
4. Inicia serviço

Ver documentação completa: [RAILWAY_FFMPEG_CONFIG.md](RAILWAY_FFMPEG_CONFIG.md)

## 🧪 Testing

### Testes Unitários

```bash
pytest tests/ -v
```

### Testes E2E

```bash
./run-e2e-tests.sh
```

Ou manualmente:
```bash
pytest tests/test_e2e_hls_streaming.py -v -s
```

## 📚 Documentação

- **CLAUDE.md** - Guia completa para desenvolvedores
- **RAILWAY_FFMPEG_CONFIG.md** - Configuração FFmpeg no Railway
- **docs/superpowers/implementation-report/hls-streaming-implementation-2026-03-29.md** - Relatório técnico completo

## 🔧 API Endpoints

### Autenticação
- `POST /api/auth/register` - Registrar usuário
- `POST /api/auth/login` - Login e obter token JWT

### Câmeras IP
- `GET /api/cameras` - Listar câmeras
- `POST /api/cameras` - Criar câmera (auto-gera RTSP URL)
- `GET /api/cameras/<id>` - Obter câmera
- `PUT /api/cameras/<id>` - Atualizar câmera
- `DELETE /api/cameras/<id>` - Deletar câmera
- `POST /api/cameras/test` - Testar conectividade RTSP

### Streams HLS
- `POST /api/cameras/<id>/stream/start` - Iniciar stream HLS + YOLO
- `POST /api/cameras/<id>/stream/stop` - Parar stream
- `GET /api/cameras/<id>/stream/status` - Status do stream
- `GET /api/streams/status` - Status de todos os streams
- `GET /streams/health` - Health report detalhado (Task 17)

### HLS Files
- `GET /streams/<camera_id>/stream.m3u8` - Playlist HLS
- `GET /streams/<camera_id>/<segment>.ts` - Segmentos de vídeo

## 🛠️ Development

### Backend Structure

```
api_server.py                 # Flask app com todos os endpoints
backend/
├── database.py               # SQLAlchemy connection pool
├── auth_db.py                # Autenticação JWT
├── ip_camera_service.py      # CRUD de câmeras IP
├── rtsp_builder.py           # Gerador URLs RTSP
├── stream_manager.py         # Gerenciador FFmpeg/HLS
└── yolo_processor.py        # Detecção YOLO contínua
```

### Frontend Structure

```
frontend/src/
├── components/
│   ├── hls-camera-feed.tsx   # Player HLS com overlay YOLO
│   └── camera-grid.tsx        # Grid de 12 câmeras
├── types/
│   └── camera.ts              # Interfaces TypeScript
├── hooks/
│   └── useCameraStreams.ts    # Hook para streams
└── lib/
    └── api.ts                 # Cliente REST API
```

## 🔒 Segurança

- **JWT Authentication** - Tokens assinados com expiração de 7 dias
- **Password Hashing** - bcrypt com salt
- **User Ownership** - Verificação de propriedade em todos os endpoints
- **Path Traversal Protection** - Validação de filenames
- **Input Validation** - Validação de IP, port, FPS
- **Password Masking** - Senhas mascaradas em respostas API

## 📊 Performance

**Configuração Atual (Low Latency):**
- **Latência**: 2-3 segundos
- **Throughput**: 5-12 câmeras simultâneas
- **YOLO FPS**: 5 FPS por câmera
- **HLS Segments**: 1 segundo
- **Playlist Size**: 3 segments (buffer de 3s)

**Trade-offs:**
- Maior qualidade = maior latência
- Mais câmeras = mais CPU
- FPS mais alto = mais CPU

## 🐛 Troubleshooting

### Stream não inicia

1. Verificar conectividade RTSP:
```bash
curl -X POST http://localhost:5001/api/cameras/test \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"ip":"192.168.1.100","port":554,"manufacturer":"generic"}'
```

2. Verificar se FFmpeg está instalado:
```bash
ffmpeg -version
```

3. Checar logs:
```bash
railway logs | grep ffmpeg
```

### WebSocket não conecta

1. Verificar se handler está ativo:
```bash
curl http://localhost:5001/ws/test
```

2. Checar token no browser console:
```javascript
localStorage.getItem('token')
```

### High CPU usage

Reduzir qualidade:
```bash
FFMPEG_RESOLUTION=640x360
FFMPEG_PRESET=ultrafast
```

Mais detalhes em: [CLAUDE.md](CLAUDE.md#troubleshooting)

## 📈 Status do Projeto

**✅ Implementado (Tasks 1-20):**
- ✅ Database schema (7 tabelas incluindo ip_cameras)
- ✅ JWT authentication
- ✅ **HLS Streaming System completo** (Tasks 1-19)
- ✅ YOLO detection em tempo real
- ✅ WebSocket real-time
- ✅ Error handling avançado
- ✅ Health monitoring
- ✅ E2E test suite
- ✅ Railway deployment configurado
- ✅ 87 testes passando

**🔜 Roadmap:**
- Training images upload
- Custom YOLO model training
- DeepSORT tracking
- Human verification queue

## 📄 Licença

Confidencial - Propriedade da CATH

## 👥 Contribuidores

- Vitore Emanuel - Desenvolvedor
- Claude Sonnet 4.5 - AI Assistant (Autonomous implementation: Tasks 4-20)

---

**Última atualização**: Março 2026
**Versão**: 2.0.0 (HLS Streaming System)
