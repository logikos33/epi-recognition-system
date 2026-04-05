# 📋 DIAGNÓSTICO COMPLETO - Módulo de Treinamento YOLO

Data: 30 de Março de 2026

---

## ✅ **O QUE JÁ EXISTE NO BACKEND**

### **1. Arquivos Python de Treinamento:**

| Arquivo | Status | Descrição |
|--------|--------|-----------|
| `backend/training_db.py` | ✅ COMPLETO | TrainingProjectDB - CRUD de projetos, videos, frames, anotações |
| `backend/yolo_trainer.py` | ✅ COMPLETO | YOLOTrainer - Executa treinamento YOLO real |
| `backend/yolo_exporter.py` | ✅ COMPLETO | Exporta dataset para formato YOLO (train/val split) |
| `backend/yolo_processor.py` | ✅ EXISTE | Processador YOLO (multi-threading) |
| `backend/video_processor.py` | ✅ EXISTE | Processador de vídeos e extração de frames |
| `backend/annotation_db.py` | ✅ EXISTE | Operações de anotação |

### **2. Tabelas no Banco de Dados:**

| Tabela | Status | Campos |
|--------|--------|---------|
| `training_images` | ✅ EXISTE | id, user_id, product_id, image_url, is_annotated, created_at |
| `classes_yolo` | ✅ DEFINIDA | id, nome, descricao, valor_unitario, unidade, cor_hex, class_index |
| `contagens_deteccao` | ✅ DEFINIDA | id, camera_id, classe_id, quantidade, valor_total, sessao_id, detectado_em |
| `versoes_modelo` | ✅ DEFINIDA | id, versao, classes_json, epochs, map50, arquivo_weights, ativo, treinado_em |
| `imagens_treinamento` | ✅ DEFINIDA | id, classe_id, caminho, anotacao_yolo, validada, conjunto (train/val/test) |

**OBS**: As tabelas foram DEFINIDAS na migration 003_create_yolo_training_tables.sql mas podem não estar CRIADAS no banco Railway ainda.

### **3. YOLO:**

| Componente | Status | Detalhes |
|-----------|--------|----------|
| **YOLO instalado** | ✅ SIM | Ultralytics instalado no venv |
| **Modelo base** | ✅ EXISTE | yolov8n.pt (6.2MB) - modelo pré-treinado |
| **YOLOTrainer** | ✅ PRONTO | Classe completa para treinamento |
| **YOLOProcessor** | ✅ PRONTO | Multi-threading para inferência |

### **4. Carência de Rotas REST:**

❌ **NÃO EXISTEM** endpoints REST para:
- Upload de vídeos
- Lista de vídeos
- Extração de frames
- Gerenciamento de anotações
- Início/parada de treinamento
- Exportação de dataset
- Download de dataset

---

## ❌ **O QUE FALTA IMPLEMENTAR**

### **ETAPA 1 - API Endpoints (Prioridade CRÍTICA)**

Precisamos criar as rotas REST que faltam no `api_server.py`:

```python
# ─── Vídeos ────────────────────────────────────────────────
POST   /api/training/videos/upload          # Upload de vídeo
GET    /api/training/videos               # Listar vídeos
DELETE /api/training/videos/{id}         # Excluir vídeo
GET    /api/training/videos/{id}/frames    # Listar frames
POST   /api/training/videos/{id}/extract  # Iniciar extração de frames

# ─── Anotações ───────────────────────────────────────────
GET    /api/training/frames/{id}/annotations  # Obter anotações
POST   /api/training/frames/{id}/annotations  # Salvar anotações
POST   /api/training/frames/{id}/copy-from/{source_id}  # Copiar anotações

# ─── Dataset ────────────────────────────────────────────────
GET    /api/training/datasets/export      # Exportar dataset YOLO
POST   /api/training/datasets/download     # Download .zip com dataset

# ─── Treinamento ────────────────────────────────────────
POST   /api/training/start                # Iniciar treinamento
GET    /api/training/status               # Status do treinamento
POST   /api/training/stop                 # Parar treinamento
POST   /api/training/{id}/activate        # Ativar modelo treinado
GET    /api/training/history              # Histórico de treinamentos
```

### **ETAPA 2 - Upload de Vídeos**

- Endpoint: `POST /api/training/videos/upload`
- Aceita: multipart/form-data
- Salva vídeo em: `storage/training_videos/`
- Inicia job de extração de frames em background
- Extração: 1 frame a cada 2 segundos
- Salva frames em: `storage/training_frames/{video_id}/`

### **ETAPA 3 - Extração de Frames**

Usar OpenCV:
```python
import cv2

def extract_frames(video_path, output_dir, interval_seconds=2):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval = int(fps * interval_seconds)
    frame_count = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_count % interval == 0:
            cv2.imwrite(f"{output_dir}/frame_{saved:05d}.jpg", frame)
            saved += 1
        frame_count += 1
    cap.release()
    return saved
```

### **ETAPA 4 - Interface de Anotação**

- Canvas HTML5 sobre a imagem do frame
- Mouse events para desenhar bounding boxes
- Formato YOLO: `class_id x_center y_center width height` (normalizado 0-1)
- Salvar no banco: `imagens_treinamento`
- Copiar anotações de frame anterior para acelerar

### **ETAPA 5 - Treinamento YOLO Real**

JÁ existe `YOLOTrainer` - só precisamos EXPOR via API.

```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
results = model.train(
    data='datasets/epi_monitor/data.yaml',
    epochs=50,
    batch=16,
    imgsz=640,
    project='runs/train',
    name='epi_monitor',
)
```

### **ETAPA 6 - Motor de Regras**

Tabelas a criar:
- `rules` - Regras de negócio configuráveis
- `counting_sessions` - Sessões de contagem
- `session_events` - Eventos das sessões

Engine de regras roda a cada detecção YOLO.

### **ETAPA 7 - Validação do Operador**

Tela para revisar sessões encerradas:
- Validar contagem
- Corrigir se necessário
- Aprovar/rejeitar

### **ETAPA 8 - Exportação Excel**

Usar `openpyxl` para gerar Excel com sessões.

---

## 🎯 **PRÓXIMA AÇÃO RECOMENDADA**

**OPÇÃO 1 (Completa mas demorada):**
1. Criar endpoints REST para vídeos/frames/anotações/treinamento
2. Implementar upload de vídeos com extração de frames
3. Criar ferramenta de anotação (canvas)
4. Conectar YOLOTrainer à API
5. Implementar motor de regras
6. Criar sistema de validação
7. Exportação Excel

**OPÇÃO 2 (Incremental - começa pelo upload):**
1. Criar endpoint POST /api/training/videos/upload
2. Implementar extração automática de frames
3. Criar página frontend para gerenciar vídeos
4. Seguir com anotação depois

---

## 📊 **RESUMO**

### ✅ **Backlog Pronto ( Backend):**
- ✅ Classes YOLO definidas no banco
- ✅ YOLO instalado e funcionando
- ✅ yolov8n.pt disponível
- ✅ YOLOTrainer implementado
- ✅ YOLOExporter implementado
- ✅ TrainingProjectDB implementado
- ✅ Tabelas de treinamento definidas

### ❌ **Faltam:**
- ❌ Endpoints REST para treinamento/videos/frames
- ❌ Upload de vídeos
- ❌ Extração de frames
- ❌ Interface de anotação
- ❌ Conexão do YOLOTrainer à API
- ❌ Motor de regras
- ❌ Validação de operador
- ❌ Exportação Excel
- ❌ Tabelas regras/sessões/events (precisam ser criadas)

---

**Posso começar implementando agora? Qual abordagem você prefere?**
