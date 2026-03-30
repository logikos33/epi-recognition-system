# YOLO Training System - Design Document

**Date:** 2026-03-29
**Status:** Draft
**Author:** Claude (Sonnet 4.5)
**Stakeholder:** Vitoremanuel

---

## Executive Summary

Sistema completo de treinamento de modelos YOLOv8 customizados para o EPI Recognition System. O sistema permite treinar modelos especializados para detectar produtos específicos através de uma interface híbrida: upload de vídeos pré-gravados OU seleção de trechos ao vivo das câmeras.

**Key Features:**
- Upload e gerenciamento de vídeos de treinamento
- Anotação automática assistida por IA (YOLO base)
- Interface de revisão manual para casos duvidosos
- Configuração de hiperparâmetros de treinamento
- Monitoramento de progresso em tempo real
- Validação e deploy de modelos customizados

---

## 1. Architecture Overview

### 1.1 Frontend Components

```
/dashboard/training/
├── page.tsx                    # Main page - training projects list
├── [id]/
│   ├── page.tsx               # Training detail page
│   ├── annotate/page.tsx      # Annotation interface
│   └── train/page.tsx         # Training monitor
└── new/page.tsx               # Create new training project

/components/training/
├── training-project-card.tsx   # Project card in list
├── video-uploader.tsx          # Drag-drop video upload
├── frame-extractor.tsx         # Extract frames from video
├── annotation-canvas.tsx        # Canvas for drawing boxes
├── assisted-annotation.tsx     # AI-assisted annotation
├── training-config.tsx         # Hyperparameters form
├── training-progress.tsx       # Real-time training monitor
└── model-validator.tsx         # Validation interface

/hooks/
├── useTrainingProjects.ts      # Training projects CRUD
├── useAnnotation.ts            # Annotation state management
├── useTrainingProgress.ts      # WebSocket training updates
└── useModelValidation.ts       # Validation metrics
```

### 1.2 Backend API Endpoints

```python
# Training Projects
POST   /api/training/projects                    # Create project
GET    /api/training/projects                    # List projects
GET    /api/training/projects/:id                # Get project details
PUT    /api/training/projects/:id                # Update project
DELETE /api/training/projects/:id                # Delete project

# Training Videos & Frames
POST   /api/training/projects/:id/videos         # Upload video
GET    /api/training/projects/:id/videos         # List videos
DELETE /api/training/projects/:id/videos/:vid    # Delete video
GET    /api/training/projects/:id/frames         # Extract frames from video

# Annotations
POST   /api/training/projects/:id/annotations    # Create annotation
GET    /api/training/projects/:id/annotations    # List annotations
PUT    /api/training/projects/:id/annotations/:aid  # Update annotation
DELETE /api/training/projects/:id/annotations/:aid  # Delete annotation
POST   /api/training/projects/:id/annotations/auto  # AI-assisted annotation

# Training
POST   /api/training/projects/:id/train          # Start training
GET    /api/training/projects/:id/train/status   # Training status
POST   /api/training/projects/:id/train/stop     # Stop training

# Models
GET    /api/training/projects/:id/models         # List trained models
POST   /api/training/projects/:id/models/:mid/activate  # Activate model
GET    /api/training/projects/:id/models/:mid/metrics   # Validation metrics
```

### 1.3 Database Schema Updates

```sql
-- Training Projects
CREATE TABLE training_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_classes JSONB NOT NULL,  -- ["helmet", "vest", "gloves"]
    status VARCHAR(50) DEFAULT 'draft',  -- draft, annotating, training, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Training Videos
CREATE TABLE training_videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES training_projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,  -- MinIO path
    duration_seconds DECIMAL(10,2),
    frame_count INTEGER,
    fps DECIMAL(5,2),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Training Frames
CREATE TABLE training_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES training_videos(id) ON DELETE CASCADE,
    frame_number INTEGER NOT NULL,
    storage_path TEXT NOT NULL,  -- MinIO path
    is_annotated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Annotations
CREATE TABLE training_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    frame_id UUID NOT NULL REFERENCES training_frames(id) ON DELETE CASCADE,
    class_name VARCHAR(100) NOT NULL,
    bbox_x DECIMAL(10,2) NOT NULL,  -- Normalized 0-1
    bbox_y DECIMAL(10,2) NOT NULL,
    bbox_width DECIMAL(10,2) NOT NULL,
    bbox_height DECIMAL(10,2) NOT NULL,
    confidence DECIMAL(4,3),  -- AI confidence (null if manual)
    is_ai_generated BOOLEAN DEFAULT FALSE,
    is_reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- Trained Models
CREATE TABLE trained_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES training_projects(id),
    model_name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    storage_path TEXT NOT NULL,  -- .pt file path
    map50 DECIMAL(4,3),  -- Mean Average Precision @50
    map75 DECIMAL(4,3),
    map50_95 DECIMAL(4,3),
    precision DECIMAL(4,3),
    recall DECIMAL(4,3),
    training_epochs INTEGER,
    training_time_seconds INTEGER,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Training Jobs (background tasks)
CREATE TABLE training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES training_projects(id),
    status VARCHAR(50) DEFAULT 'queued',  -- queued, running, completed, failed
    progress DECIMAL(5,2) DEFAULT 0,  -- 0-100
    current_epoch INTEGER,
    total_epochs INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 2. User Flow

### 2.1 Create Training Project

1. User navigates to `/dashboard/training`
2. Clicks "Novo Projeto de Treinamento"
3. Fills form:
   - Project name
   - Description
   - Target classes (multi-select): e.g., "Capacete", "Colete", "Luvas"
   - Source type: Upload video OR Select from camera
4. Click "Criar Projeto"
5. Redirects to annotation interface

### 2.2 Annotation Flow (Híbrido Inteligente)

**Phase 1: Upload / Select Footage**

- **Upload Video:**
  - Drag & drop or file picker
  - Videos up to 500MB (MP4, AVI, MOV)
  - Progress bar during upload
  - Backend extracts frames automatically (1 frame/sec)

- **Select from Camera:**
  - User navigates to `/dashboard/live`
  - Clicks "Capturar para Treinamento"
  - Records 30-60 second clip
  - Clip is saved to training project

**Phase 2: AI-Assisted Annotation**

1. Backend runs base YOLO model on all frames
2. Creates draft annotations with `is_ai_generated=true, is_reviewed=false`
3. Frontend displays frames with AI boxes (yellow = unreviewed)
4. User reviews only low-confidence detections (<80%)

**Phase 3: Manual Review & Correction**

Interface features:
- **Keyboard shortcuts:**
  - `←` / `→` - Previous/next frame
  - `a` - Accept all AI boxes on frame
  - `d` - Delete selected box
  - `e` - Edit selected box
- **Mouse:**
  - Click & drag to draw new box
  - Click box to select
  - Drag handles to resize
  - Right-click to delete
- **Auto-advance:** Skip frames with 0 detections or all high-confidence (>90%)

**Phase 4: Export Dataset**

When annotation is complete:
1. User clicks "Finalizar Anotação"
2. Backend exports to YOLO format:
   ```
   dataset/
   ├── images/
   │   ├── train/
   │   └── val/
   ├── labels/
   │   ├── train/
   │   └── val/
   └── data.yaml
   ```
3. Dataset is compressed and ready for training

### 2.3 Training Configuration

User configures hyperparameters:

```yaml
Recommended defaults (editable):
- Epochs: 100
- Batch size: 16
- Image size: 640
- Learning rate: 0.01
- Optimizer: Adam
- Train/Val split: 80/20
- Augmentation: True
```

Advanced options (collapsible):
- Patience (early stopping): 10
- Weight decay: 0.0005
- Momentum: 0.937
- Warmup epochs: 3

### 2.4 Training Execution

1. User clicks "Iniciar Treinamento"
2. Backend:
   - Queues training job
   - Spawns background Python process
   - Runs YOLOv8 training with custom dataset
3. Frontend:
   - Shows real-time progress via WebSocket
   - Displays charts: Loss, mAP, Precision, Recall
   - Shows current epoch and estimated time remaining

4. On completion:
   - User receives notification
   - Model metrics are displayed
   - Option to validate or deploy

### 2.5 Model Validation

User runs validation on test images:

1. Upload test images OR use validation set
2. Backend runs inference with trained model
3. Display results side-by-side:
   - Original image
   - Detected boxes with confidence
   - Ground truth (if available)
   - Metrics: IoU, precision, recall per class

4. User can:
   - Approve model → Deploy to production
   - Reject model → Add more training data
   - Download model file (.pt)

---

## 3. Component Design

### 3.1 Training Projects List (`page.tsx`)

```tsx
// Layout:
- Header: "Projetos de Treinamento" + "Novo Projeto" button
- Grid of project cards:
  - Project name, description
  - Target classes (badges)
  - Status badge (draft, annotating, training, completed)
  - Progress bar (annotations: 45/100 frames)
  - Last updated
  - Actions: Edit, Delete, Continue

Empty state:
- Icon + "Nenhum projeto ainda"
- CTA: "Criar primeiro projeto"
```

### 3.2 Annotation Interface (`annotate/page.tsx`)

```tsx
// Layout:
[Left Sidebar - 30%]          [Main Canvas - 70%]
├── Thumbnail strip            ├── Image/Video player
│   └── All frames             ├── Bounding boxes overlay
│   (annotated: green ✓)       ├── Zoom controls
│   (unannotated: gray)        └── Fullscreen button
├── Frame info                └──
│   ├── Frame 45/100          [Right Panel - 20%]
│   ├── Detections: 3         ├── Class selector
│   └── Confidence: 85%       ├── Annotations list
├── Controls:                    ├── Box: [x, y, w, h]
│   [◀] [▶] [record]            ├── Confidence: 85%
│   [Accept] [Delete]           └── Actions: [Edit] [Del]
└── Progress bar               └── AI suggestions
    Annotations: 45/100            (if low confidence)

Keyboard shortcuts displayed in tooltip
```

### 3.3 Training Progress Monitor (`train/page.tsx`)

```tsx
// Layout:
[Header]
├── Status: "Training - Epoch 45/100"
├── Progress bar: 45%
└── ETA: 15 minutes

[Charts - 2x2 grid]
├── Loss vs Epoch (line chart)
├── mAP vs Epoch (line chart)
├── Precision per Class (bar chart)
└── Recall per Class (bar chart)

[Real-time Logs - scrollable]
├── "Epoch 45/100"
├── "train_loss: 0.234"
├── "mAP50: 0.876"
└── "GPU: RTX 3080 - 67% utilization"

[Actions]
├── [Stop Training] [Pause]
└── [Download Checkpoint]
```

### 3.4 Model Validator (`model-validator.tsx`)

```tsx
// Layout:
[Header]
├── Model: "epi-detection-v1.pt"
└── Upload test images OR use val set

[Results Grid - 2 columns]
├── [Original Image]  |  [Predictions + Ground Truth]
│   product.jpg       │  ✅ Predicted: helmet (92%)
│                      │  ✅ Ground truth: helmet
│                      │  ✅ IoU: 0.89
├── [Next Image →]    │

[Metrics Summary]
├── Overall mAP@50: 0.87
├── Overall mAP@50-95: 0.72
├── Precision: 0.91
├── Recall: 0.84
└── Per-class breakdown table

[Actions]
├── [Deploy to Production]
├── [Download Model]
└── [Add More Training Data]
```

---

## 4. Backend Implementation Notes

### 4.1 Video Frame Extraction

```python
# Use OpenCV for frame extraction
import cv2

def extract_frames(video_path: str, output_dir: str, fps: int = 1):
    """Extract 1 frame per second from video"""
    video = cv2.VideoCapture(video_path)
    count = 0
    success = True

    while success:
        success, frame = video.read()
        if count % fps == 0:
            cv2.imwrite(f"{output_dir}/frame_{count}.jpg", frame)
        count += 1

    video.release()
```

### 4.2 AI-Assisted Annotation

```python
# Use base YOLOv8 model for initial annotation
from ultralytics import YOLO

model = YOLO('yolov8n.pt')  # Base model

def auto_annotate_frames(frames_dir: str):
    """Run base YOLO on all frames"""
    results = model(frames_dir, stream=True)

    annotations = []
    for r in results:
        for box in r.boxes:
            annotations.append({
                'class': model.names[int(box.cls)],
                'bbox': box.xywhn[0].tolist(),  # normalized
                'confidence': float(box.conf)
            })

    return annotations
```

### 4.3 Training Job Queue

Use Celery or Redis Queue for background training:

```python
# tasks.py
@celery.task
def train_yolo_model(project_id: str, config: dict):
    """Background YOLO training task"""
    project = get_project(project_id)

    # Load YOLO
    model = YOLO('yolov8n.pt')

    # Train
    results = model.train(
        data=project.dataset_path,
        epochs=config['epochs'],
        batch=config['batch_size'],
        device='0' if torch.cuda.is_available() else 'cpu'
    )

    # Save model
    model_path = f"models/{project_id}/best.pt"
    results.save(model_path)

    # Update project status
    mark_training_complete(project_id, model_path)
```

### 4.4 WebSocket for Real-time Updates

```python
# training_progress.py
from flask_socketio import SocketIO, emit

socketio = SocketIO()

def broadcast_training_progress(job_id: str, progress: float, epoch: int):
    """Broadcast training progress to frontend"""
    socketio.emit('training_progress', {
        'job_id': job_id,
        'progress': progress,
        'epoch': epoch,
        'timestamp': datetime.now().isoformat()
    })
```

---

## 5. Technical Considerations

### 5.1 Storage (MinIO)

- Videos stored in: `training-videos/{project_id}/{video_id}.mp4`
- Frames stored in: `training-frames/{project_id}/{frame_id}.jpg`
- Models stored in: `trained-models/{project_id}/v{version}.pt`

**Estimated storage per project:**
- 10 videos @ 50MB each = 500MB
- 10,000 frames @ 200KB each = 2GB
- 3 model checkpoints @ 50MB each = 150MB
- **Total: ~2.65GB per project**

### 5.2 Performance Optimizations

1. **Lazy loading frames:** Only load frames visible in viewport
2. **Thumbnail generation:** Create 100px thumbnails for fast scrolling
3. **Progressive upload:** Stream large videos in chunks
4. **Caching:** Cache AI annotations in Redis
5. **Background processing:** Extract frames & annotate in background jobs

### 5.3 Security

- Only project owner can access their projects
- Videos and models are private (not publicly accessible)
- MinIO presigned URLs with expiration
- Rate limiting on training jobs (max 2 concurrent per user)

---

## 6. Success Metrics

**User Experience:**
- Time from video upload to ready-to-train: <5 minutes
- Annotation speed with AI assist: ~10 sec/frame (vs 1-2 min manual)
- Training time for 1000 images: ~30 minutes on GPU

**Technical:**
- mAP@50 > 0.85 on validation set
- Training completes without errors
- WebSocket latency <500ms
- Video upload success rate >99%

---

## 7. Future Enhancements (Out of Scope)

- Active learning: Model suggests most informative frames to annotate
- Data augmentation preview: Show augmented samples before training
- Model versioning: Rollback to previous model versions
- A/B testing: Compare models in production
- Transfer learning: Fine-tune existing models instead of training from scratch
- Multi-GPU training: Distributed training for large datasets

---

## 8. Implementation Priority

**Phase 1 (MVP):**
1. Database schema & migrations
2. Training projects CRUD (list, create, delete)
3. Video upload & frame extraction
4. Manual annotation interface (bounding boxes)
5. Export to YOLO format
6. Training configuration UI
7. Basic training execution (no real-time progress)

**Phase 2 (Polish):**
8. AI-assisted annotation
9. Review workflow for low-confidence detections
10. Real-time training progress (WebSocket)
11. Training metrics charts
12. Model validation interface

**Phase 3 (Advanced):**
13. Live capture from cameras
14. Model deployment to production
15. Multi-model management
16. Advanced hyperparameter tuning

---

## Appendix A: API Response Examples

### Create Training Project

**Request:**
```http
POST /api/training/projects
Authorization: Bearer <token>

{
  "name": "EPI Detection Model",
  "description": "Detect safety equipment",
  "target_classes": ["helmet", "vest", "gloves", "goggles"]
}
```

**Response:**
```json
{
  "success": true,
  "project": {
    "id": "uuid-123",
    "name": "EPI Detection Model",
    "description": "Detect safety equipment",
    "target_classes": ["helmet", "vest", "gloves", "goggles"],
    "status": "draft",
    "created_at": "2026-03-29T14:00:00Z"
  }
}
```

### AI-Assisted Annotation

**Request:**
```http
POST /api/training/projects/uuid-123/annotations/auto
Authorization: Bearer <token>

{
  "frame_ids": ["frame-1", "frame-2", "frame-3"],
  "confidence_threshold": 0.5
}
```

**Response:**
```json
{
  "success": true,
  "annotations": [
    {
      "id": "anno-1",
      "frame_id": "frame-1",
      "class_name": "helmet",
      "bbox": [0.45, 0.32, 0.15, 0.20],
      "confidence": 0.87,
      "is_ai_generated": true,
      "is_reviewed": false
    }
  ]
}
```

### Training Status

**Request:**
```http
GET /api/training/projects/uuid-123/train/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "status": "running",
  "progress": 45.5,
  "current_epoch": 45,
  "total_epochs": 100,
  "metrics": {
    "loss": 0.234,
    "map50": 0.876,
    "precision": 0.91,
    "recall": 0.84
  },
  "eta_seconds": 900,
  "started_at": "2026-03-29T14:30:00Z"
}
```

---

## Appendix B: UI Mockups (Text-based)

### Training Projects List

```
┌─────────────────────────────────────────────────────────────────┐
│ EPI Recognition System           [Dashboard] [Live] [Training] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Projetos de Treinamento                    [+ Novo Projeto]    │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ EPI Detection Model                          [Concluir]     ││
│ │ Detect safety equipment: helmet, vest, gloves               ││
│ │ Status: 🟡 Anotando  Progress: ████████░░░░ 45%            ││
│ │ Last updated: 2 hours ago                                   ││
│ └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Product Counter v2                             [Continuar]   ││
│ │ Count products on conveyor belt                             ││
│ │ Status: 🟢 Treinando  Progress: ███████████░ 90%            ││
│ │ ETA: 15 minutes                                            ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Annotation Interface

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Training: EPI Detection Model                   [Salvar][Exit]│
├──────────┬──────────────────────────────────────┬──────────────┤
│ Frames   │                                      │ Annotations  │
│ [Thumb1] │                                      │              │
│ [Thumb2] │      ┌────────────────────┐         │ Helmet (92%) │
│ [Thumb3] │      │  ┌──────────┐      │         │ [Edit] [Del] │
│ [Thumb4] │      │  │   👷    │      │         │              │
│ [Thumb5] │      │  └──────────┘      │         │ Vest (87%)   │
│          │      │                    │         │ [Edit] [Del] │
│ Frame 45 │      │   [product box]    │         │              │
│ 3 detects│      │                    │         │ ┌───────────┐ │
│          │      └────────────────────┘         │ │ + Add New │ │
│ [<] [>]  │      [Zoom: 100%] [Fullscreen]     │ └───────────┘ │
│ [Rec]    │                                      │              │
│          │      AI suggestions:                 │ Class:       │
│ 45/100   │      ✅ Helmet (92%) - ACCEPTED     │ [Helmet ▼]   │
│ ████████ │      ⚠️  Vest (67%) - Review        │              │
│          │                                      │              │
└──────────┴──────────────────────────────────────┴──────────────┘
```

---

**End of Design Document**
