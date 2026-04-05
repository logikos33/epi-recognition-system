# YOLO Training Module - Complete Design Specification

**Date:** 2026-03-29
**Status:** Approved for Implementation
**Version:** 1.0

---

## Executive Summary

Transform the decorative training page into a fully functional YOLO training pipeline with 8 integrated stages: video processing, frame extraction, AI-assisted annotation, real YOLO training, state-machine rules engine, operator validation, dashboard KPIs, and Excel export - all with pixel-perfect consistency to the existing monitoring interface.

**Implementation Scope:** All 8 stages in a single comprehensive release.
**Design Principle:** Reuse 100% of existing components and design tokens. No new design system.

---

## Table of Contents

1. [Design Decisions Summary](#design-decisions-summary)
2. [Section 1: Video Processing & Frame Extraction](#section-1-video-processing--frame-extraction)
3. [Section 2: Annotation Interface](#section-2-annotation-interface-bounding-box-tool)
4. [Section 3: Training Configuration & Execution](#section-3-training-configuration--execution)
5. [Section 4: Rules Engine](#section-4-rules-engine-state-machine)
6. [Section 5: Operator Validation Interface](#section-5-operator-validation-interface)
7. [Section 6: Dashboard KPIs & Excel Export](#section-6-dashboard-kpis--excel-export)
8. [Section 7: Design System Consistency](#section-7-design-system-consistency)
9. [Implementation Order](#implementation-order)
10. [Final Checklist](#final-checklist)

---

## Design Decisions Summary

### Q2: Video Processing Workflow
**Decision:** Hybrid (Option C) with customizations
- Videos > 10min: Visual timeline/ruler for user to select max 10min segment
- Videos ≤ 10min: Use entire video automatically
- Extraction: 10 chunks of 1 minute each, 2 frames/second per chunk
- Three data sources: Video upload (priority 1), direct images (priority 2), monitoring cuts (priority 3)

### Q4: Training Configuration
**Decision:** Basic customization (Option B)
- 3 presets: Fast (yolov8n, 50ep), Balanced (yolov8s, 100ep), Quality (yolov8m, 150ep)
- Manual adjustments: epochs (25-200), batch (8/16/32), image (640/960/1280), model (n/s/m)
- Fixed internally: lr0=0.01, optimizer=auto, augment=True, device=auto

### Q5: Rules Engine
**Decision:** Complex event sequences (Option C) with templates
- State machine per bay/session: IDLE → TRUCK_DETECTED → PLATE_CAPTURED → COUNTING → TRUCK_DEPARTED → PENDING_VALIDATION → VALIDATED/REJECTED
- Time rules: bay empty 30s → end, no product 2min → alert, session >4h → alert
- Cooldown: same product counts again only after 3s interval
- 6 templates with toggles (Bay Control, Product Count, Plate Capture, EPI Alert, Session Timeout, Long Session)

### Q6: Operator Validation
**Decision:** Detailed review with corrections (Option B)
- Pending sessions list with filters (bay, camera, date, status)
- Session detail: summary, event timeline, snapshots, class breakdown
- Editable count (AI vs operator), false positives markable
- Actions: Validate, Correct count, Reject (mandatory reason)
- Save auto_count and manual_count separately in database

### Q7: Dashboard KPIs
**Decision:** Operational metrics (Option B) + Excel export
- KPIs: sessions today, products counted, trucks processed, avg duration, AI accuracy, cameras online
- Charts: products/hour, sessions/bay, confidence distribution, EPI compliance
- Filters: period, camera, bay
- Excel: 5 tabs (Summary, Sessions, Alerts, By Hour, By Bay)
- Polling: KPIs every 30s, charts every 2min

### Q8: Design System Consistency
**Decision:** Pixel-perfect consistency (Option C)
- Reuse 100% existing components (Modal, Toast, Cards, Buttons, StatusBadge)
- Design tokens: --bg, --card, --border, --text, --muted, --accent
- Fonts: DM Sans (text), DM Mono (data)
- Border-radius: 6-8px (small), 14-16px (cards)
- Status colors: green #22c55e, yellow #f59e0b, red #ef4444
- NO new colors, fonts, or patterns

---

## Section 1: Video Processing & Frame Extraction

### Backend API Endpoints

```python
# Video management
POST   /api/training/videos/upload          # Multipart video upload
GET    /api/training/videos                  # List user's videos
DELETE /api/training/videos/<id>             # Delete video and frames
GET    /api/training/videos/<id>/frames      # List extracted frames
POST   /api/training/videos/<id>/extract     # Extract with start/end params

# Image upload
POST   /api/training/images/upload           # Direct image upload (.jpg/.png)
GET    /api/training/images                  # List uploaded images
DELETE /api/training/images/<id>             # Delete image

# Future (not implemented now)
GET    /api/training/monitoring/segments     # List monitoring recordings
POST   /api/training/monitoring/<id>/import  # Import segment
```

### Extract Endpoint Parameters

```json
POST /api/training/videos/<id>/extract
{
  "start_seconds": 120,   // User-selected start (optional, default 0)
  "end_seconds": 720      // User-selected end (optional, max 600 from start)
}
```

### Video Processing Logic

**If video > 10 minutes:**
1. Return metadata (duration, size, fps) to frontend
2. Frontend displays timeline selector
3. User selects 10-minute segment (start, end)
4. Frontend sends start_seconds, end_seconds to extract endpoint
5. Process only selected segment

**If video ≤ 10 minutes:**
1. Auto-extract entire video in background
2. Process in 1-minute chunks
3. Each chunk: extract 2 frames per second
4. Total: ~1200 frames from 10 minutes

### Storage Layout

```
storage/
├── training_videos/           # Uploaded videos
│   └── {video_id}/
│       └── original.{ext}
└── training_frames/           # Extracted frames
    └── {video_id}/
        ├── chunk_00_frame_00000.jpg
        ├── chunk_00_frame_00002.jpg
        └── ...
```

### Database Schema

**training_videos table:**
```sql
CREATE TABLE training_videos (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  filename VARCHAR(255) NOT NULL,
  original_path VARCHAR(500) NOT NULL,
  original_duration INTEGER NOT NULL,        -- Total video duration in seconds
  selected_start INTEGER,                    -- User-selected start (nullable)
  selected_end INTEGER,                      -- User-selected end (nullable)
  total_chunks INTEGER NOT NULL,             -- Total 1-minute chunks
  processed_chunks INTEGER DEFAULT 0,        -- Processed chunks (for progress)
  frame_count INTEGER,                       -- Total frames extracted
  status VARCHAR(20) DEFAULT 'uploading',    -- uploading, extracting, completed, failed
  created_at TIMESTAMP DEFAULT NOW()
);
```

**frames table:**
```sql
CREATE TABLE frames (
  id UUID PRIMARY KEY,
  video_id UUID REFERENCES training_videos(id) ON DELETE CASCADE,
  frame_number INTEGER NOT NULL,
  chunk_number INTEGER NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  is_annotated BOOLEAN DEFAULT FALSE,
  annotation_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(video_id, frame_number)
);
```

### Frontend Structure

**NO new routes** - Use tabs within existing Training page:

```jsx
// In App.tsx, page === 'training' renders:
<TrainingPage>
  <Tabs>
    <Tab id="videos">Vídeos & Dados</Tab>
    <Tab id="annotate">Anotar</Tab>
    <Tab id="train">Treinar</Tab>
    <Tab id="history">Histórico</Tab>
  </Tabs>

  {activeTab === 'videos' && <VideosDataTab />}
  {activeTab === 'annotate' && <AnnotateTab />}
  {activeTab === 'train' && <TrainTab />}
  {activeTab === 'history' && <HistoryTab />}
</TrainingPage>
```

**Vídeos & Dados Tab:**
- Upload zone with drag & drop
- Timeline slider for videos > 10min
- Video list with metadata
- Progress bar for extraction
- Frame count and status

**Upload Component Design:**
- Dashed border (2px dashed var(--border))
- Border-radius: 14px
- Hover: border-color var(--accent), background var(--accent) 5%
- Progress bar inside card during upload
- Matches existing card styles

---

## Section 2: Annotation Interface (Bounding Box Tool)

### Backend API Endpoints

```python
GET    /api/training/frames/<id>                    # Get frame metadata + image URL
GET    /api/training/frames/<id>/annotations        # Get annotations (YOLO format)
POST   /api/training/frames/<id>/annotations        # Save annotations (bulk replace)
POST   /api/training/frames/<id>/predict            # Run YOLO pre-detection
POST   /api/training/frames/<id>/copy-from/<fid>    # Copy from previous frame
```

### Annotation Storage

**frame_annotations table:**
```sql
CREATE TABLE frame_annotations (
  id UUID PRIMARY KEY,
  frame_id UUID REFERENCES frames(id) ON DELETE CASCADE,
  class_id INTEGER REFERENCES classes_yolo(id),
  x_center DECIMAL(10,8) NOT NULL,      -- Normalized 0-1
  y_center DECIMAL(10,8) NOT NULL,
  width DECIMAL(10,8) NOT NULL,
  height DECIMAL(10,8) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**YOLO Format:** `class_id x_center y_center width height` (all normalized 0-1)

### Pre-detection Endpoint

```python
@app.route('/api/training/frames/<id>/predict', methods=['POST'])
def predict_frame_annotations(frame_id):
    frame = get_frame(frame_id)
    image_path = frame.storage_path

    # Run current YOLO model
    results = model(image_path)

    # Convert to YOLO format (NORMALIZED)
    annotations = []
    for r in results:
        for box in r.boxes:
            # Use xywhn (normalized) NOT xywh (pixels)
            annotations.append({
                'class_id': int(box.cls),
                'x_center': float(box.xywhn[0][0]),  # Normalized 0-1
                'y_center': float(box.xywhn[0][1]),
                'width': float(box.xywhn[0][2]),
                'height': float(box.xywhn[0][3]),
                'confidence': float(box.conf)
            })

    return jsonify({'annotations': annotations})
```

### Annotation Canvas Component

**Props (simplified):**
```jsx
<AnnotationCanvas
  frameId={frameId}
  imageUrl={frame.image_url}
  annotations={annotations}
  classes={classes}
  onSave={handleSave}
  onNavigate={direction}
/>
```

**Internal state (not props):**
- tool: 'draw' | 'select' | 'delete'
- zoom: number
- pan: {x, y}
- selectedClass: classId
- selectedBox: boxId
- history: array of annotation snapshots (max 50)

### Canvas Implementation

**MUST use HTML5 Canvas** (not divs/SVGs):
- Image as canvas background
- Boxes drawn on canvas
- Real-time rendering at 60fps
- Zoom/pan via canvas transforms

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| 1-9 | Select class by index |
| Delete | Remove selected box |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| ← / → | Navigate prev/next frame (auto-saves) |
| Space | Toggle Draw/Select mode |
| Escape | Deselect / Cancel drawing |
| A | Auto-detect with YOLO |

**Auto-save:** When navigating frames, save current frame automatically before loading next.

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar: [Draw●] [Select] [Delete] [Undo] [Redo] [Auto-Det] │
├─────────────────────────────────────────────────────────────┤
│ Classes: ○ Helmet(green)  ○ Vest(orange)  ○ Glove(blue)    │
├──────────────────────────────┬──────────────────────────────┤
│                              │                              │
│                              │   Frame List (scrollable)    │
│         Canvas Area          │                              │
│      (zoomable, pannable)    │  ● frame_00001              │
│                              │  ○ frame_00002              │
│                              │  ✓ frame_00003              │
│                              │  ...                         │
├──────────────────────────────┴──────────────────────────────┤
│ Frame: 3/1200 | Zoom: 100% | Selected: Helmet | Boxes: 2   │
└─────────────────────────────────────────────────────────────┘
```

**Design System Consistency:**
- Toolbar: background #161b22, same style as monitoring toolbar
- Class panel: background #161b22, colored radio buttons
- Frame list: ● (annotated), ○ (pending), ✓ (reviewed), thumbnails
- Status bar: background #161b22, DM Mono font

### Implementation Priority

1. Canvas with drawing + save + navigation
2. Select mode (move and resize boxes)
3. Keyboard shortcuts (1-9, Delete, arrows)
4. Copy from previous frame
5. Undo/redo (Ctrl+Z)
6. Zoom/pan
7. Pre-detection with YOLO (second iteration)

### Performance Optimizations

- **Cache-Control:** Max-age 1 year for frame images
- **Pre-loading:** Load frame N+1 while user annotates frame N
- **Virtualization:** Render only visible frames if >200

---

## Section 3: Training Configuration & Execution

### Backend API Endpoints (Simplified)

```python
# Training control
POST   /api/training/start                    # Start YOLO training
GET    /api/training/status                   # Get active training status
POST   /api/training/stop                     # Stop training job

# Training history
GET    /api/training/history                  # List all training runs
GET    /api/training/models/<id>              # Get model details

# Model management
POST   /api/training/models/<id>/activate     # Set model as active
GET    /api/training/models/active            # Get current active model

# Dataset
POST   /api/training/dataset/export           # Export dataset to YOLO format
GET    /api/training/dataset/stats            # Get dataset statistics
GET    /api/training/dataset/download         # Download dataset .zip
```

**Note:** NO separate "projects" concept for now. Simplified to training runs.

### Dataset Stats Endpoint

```python
GET /api/training/dataset/stats

Response:
{
  "total_frames": 1200,
  "annotated_frames": 1150,
  "pending_frames": 50,
  "annotation_percentage": 95.8,
  "classes": [
    { "id": 1, "name": "Capacete", "annotation_count": 2340 },
    { "id": 2, "name": "Colete", "annotation_count": 1876 },
    ...
  ],
  "total_annotations": 8450,
  "train_split": 920,
  "val_split": 230,
  "ready_to_train": true,
  "issues": ["50 frames pending annotation"]
}
```

### Training Configuration Schema

```json
{
  "preset": "fast" | "balanced" | "quality",
  "epochs": 100,           // 25-200 slider
  "batch_size": 16,        // 8 | 16 | 32
  "image_size": 640,       // 640 | 960 | 1280
  "base_model": "yolov8s.pt"  // yolov8n.pt | yolov8s.pt | yolov8m.pt
}
```

### Presets Configuration

| Preset | Model | Epochs | Batch | Image | Est. Time | Use Case |
|--------|-------|--------|-------|-------|-----------|----------|
| Fast | yolov8n | 50 | 16 | 640 | ~15 min | Initial testing |
| Balanced | yolov8s | 100 | 16 | 640 | ~45 min | Recommended |
| Quality | yolov8m | 150 | 8 | 1280 | ~2 hours | Production |

### Validation Before Training

**Minimum requirements:**
- 50 annotated frames
- At least 2 classes with annotations
- Dataset exported to YOLO format

If not met: Disable "Start" button with tooltip explaining what's missing.

### Training Progress (INLINE, not modal)

**Rendered in "Treinar" tab, replaces configuration form:**

```
┌─────────────────────────────────────────────────────────────┐
│ Training in Progress...                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Epoch 47/100                                              │ │
│ │ [━━━━━━━━━━━━━━━━━━○━━━━━━━━━━] 47%                     │ │
│ │                                                           │ │
│ │ mAP50: 0.8234 | Precision: 0.9123 | Recall: 0.8745       │ │
│ │ Loss: 0.0234                                               │ │
│ │                                                           │ │
│ │ Started: 14:23  |  Elapsed: 24m  |  ETA: 14:58          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 2026-03-29 14:23:01 INFO     YOLO training started        │ │
│ │ 2026-03-29 14:23:02 INFO     Using GPU: NVIDIA RTX 3080   │ │
│ │ 2026-03-29 14:23:05 INFO     Epoch 1/100: loss 2.3456     │ │
│ │ 2026-03-29 14:24:12 INFO     Epoch 2/100: loss 1.9876     │ │
│ │ ...                                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│                              [Stop Training]                 │
└─────────────────────────────────────────────────────────────┘
```

**Design:**
- Progress bar, metrics in cards
- Terminal-style log: background #0d1117, DM Mono, green text
- "Stop Training" red button
- Polling every 3 seconds
- Animated badge on "Treinamento" sidebar item when active

### Training History

**Comparison with active model:**
- Green badge: "Melhor que o atual (+4% mAP)"
- Yellow badge: "Inferior ao atual (-2% mAP)"

**Model activation confirmation:**
```
"Substituir modelo em produção?
Detecções usarão o novo modelo."
[Confirmar] [Cancelar]
```

**Side-by-side comparison:**
```
Atual: mAP 0.85 | Precisão 0.91
Novo:  mAP 0.89 | Precisão 0.93 (+4% / +2%)
```

### Background Job Implementation

**Before implementing:**
```bash
# Check existing implementation
grep -n "Thread\|thread\|subprocess\|celery\|background" backend/yolo_trainer.py
```

**Options:**
- `threading.Thread` - Works but GIL may block requests
- `subprocess.Popen` - Better, isolates in separate process
- `Celery` - Ideal if configured

**Recommendation:** Use existing YOLOTrainer implementation. Report findings before implementing.

### Implementation Priority

1. Dataset stats endpoint
2. Training start + progress polling (inline)
3. Training stop
4. Training history + model list
5. Model activation with confirmation
6. Presets with auto-fill
7. Download .pt file

---

## Section 4: Rules Engine (State Machine)

### State Machine Definition

**States per bay/session:**
```
IDLE → TRUCK_DETECTED → PLATE_CAPTURED → COUNTING → TRUCK_DEPARTED
→ PENDING_VALIDATION → VALIDATED / REJECTED
```

### State Transitions

| From | To | Trigger | Condition |
|------|-----|---------|-----------|
| IDLE | TRUCK_DETECTED | YOLO detects "truck" | Bay has truck |
| TRUCK_DETECTED | PLATE_CAPTURED | YOLO detects "plate" | Plate associated |
| TRUCK_DETECTED | COUNTING | Timeout | No plate in 2min |
| PLATE_CAPTURED | COUNTING | Automatic | After plate |
| COUNTING | COUNTING | YOLO detects "product" | Cooldown 3s elapsed |
| COUNTING | TRUCK_DEPARTED | Timeout | Bay empty 30s |
| TRUCK_DEPARTED | PENDING_VALIDATION | Automatic | Session ended |
| PENDING_VALIDATION | VALIDATED | Operator action | Validate button |
| PENDING_VALIDATION | REJECTED | Operator action | Reject + reason |

### Time-Based Rules

- **Bay empty 30s:** End session automatically
- **No product 2min:** Pause and alert during COUNTING
- **Session >4 hours:** Alert for long session
- **Plate timeout 2min:** Mark "plate not read"
- **Count cooldown:** Same product counts again only after 3s

### Conditional Rules

- **"sem_epi" detected:** Generate critical alert (don't stop counting)
- **Confidence <60%:** Don't count, register as "uncertain"
- **Variance >20%:** Flag for review if AI count differs from manual

### Pre-configured Templates

**6 templates with on/off toggles:**

1. **Controle de Baia** - Complete state machine
2. **Contagem de Produtos** - Increment counter by detection
3. **Captura de Placa** - Associate plate with active session
4. **Alerta de EPI** - Generate alert when sem_epi detected
5. **Timeout de Sessão** - End if bay empty for N seconds
6. **Alerta de Sessão Longa** - Notify if session > N hours

**Configurable per template:**
- Cameras (multiselect)
- Thresholds (time, confidence, count)
- Severity (info/warning/critical)
- Active/inactive (toggle)

### Database Schema

**counting_sessions table:**
```sql
CREATE TABLE counting_sessions (
  id UUID PRIMARY KEY,
  camera_id UUID REFERENCES cameras(id),
  bay_id INTEGER,
  state VARCHAR(30) DEFAULT 'IDLE',  -- IDLE, TRUCK_DETECTED, etc
  truck_plate VARCHAR(20),
  product_count INTEGER DEFAULT 0,
  started_at TIMESTAMP DEFAULT NOW(),
  ended_at TIMESTAMP,
  last_detection_at TIMESTAMP,
  status VARCHAR(20) DEFAULT 'active',  -- active, pending_validation, validated, rejected
  validated_by VARCHAR(100),
  validated_at TIMESTAMP,
  validation_notes TEXT,
  auto_count INTEGER,
  manual_count INTEGER,
  rejection_reason TEXT
);
```

**session_events table:**
```sql
CREATE TABLE session_events (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES counting_sessions(id) ON DELETE CASCADE,
  from_state VARCHAR(30),
  to_state VARCHAR(30) NOT NULL,
  trigger_type VARCHAR(50),  -- detection, timeout, manual
  details JSONB,  -- {class, confidence, bbox, snapshot_url}
  created_at TIMESTAMP DEFAULT NOW()
);
```

**rule_configs table:**
```sql
CREATE TABLE rule_configs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  rule_template VARCHAR(50) NOT NULL,  -- bay_control, product_count, etc
  camera_ids UUID[],
  config JSONB,  -- {thresholds, timeouts, severity}
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Implementation Order

1. State machine for ONE bay
2. Test complete flow (truck → count → exit → validate)
3. Expand to multiple bays/cameras
4. Add template toggles
5. Add configuration UI

---

## Section 5: Operator Validation Interface

### Backend API Endpoints

```python
GET    /api/validation/sessions              # List pending sessions
GET    /api/validation/sessions/<id>          # Get session details
POST   /api/validation/sessions/<id>/validate # Validate session
POST   /api/validation/sessions/<id>/reject   # Reject session
GET    /api/validation/sessions/<id>/events   # Get event timeline
GET    /api/validation/sessions/<id>/snapshots # Get key snapshots
```

### Pending Sessions List

**Filters:**
- Bay
- Camera
- Date range
- Status (pending, validated, rejected)

**Counters:**
"X pendentes · Y validadas hoje · Z rejeitadas"

**Session cards:**
- Plate (large, DM Mono)
- Bay
- AI count
- Duration
- Camera
- Timestamp
- Status badge

### Session Detail Screen

**Sections:**

1. **Header (Summary):**
   - Plate (large, DM Mono)
   - Bay
   - AI count (large number)
   - Editable "Corrected count" field
   - Duration (start → end)
   - Camera

2. **Timeline (chronological events):**
   - 14:02:15 — Caminhão detectado na Baia 3
   - 14:02:28 — Placa ABC-1234 capturada (with snapshot)
   - 14:02:45 — Contagem iniciada
   - 14:03:01 — Produto detectado (#1) confiança 94%
   - ...
   - 14:25:30 — Sessão encerrada: 47 produtos

   - Low confidence (<70%) highlighted in yellow
   - Click event to view snapshot

3. **Key Snapshots Gallery:**
   - Truck entry
   - Plate capture
   - 3-5 product counting frames
   - Exit / empty bay

4. **Class Breakdown:**
   - Caixa grande: 30
   - Caixa pequena: 12
   - Palete: 5
   - Total: 47
   - Each count editable

5. **Suspicious Detections:**
   - Detections <70% confidence
   - Each with frame, class, confidence, bbox
   - Operator marks as "confirmed" or "false_positive"
   - False positives auto-subtract from total

### Actions

- **"Validar"** (green) - Confirms count (corrected or original)
- **"Rejeitar"** (red) - Opens mandatory reason field
- **"Observações"** (optional textarea)
- Toast confirmation, return to list

### AI vs Comparison Display

When operator edits count:
```
IA: 45 → Operador: 47 (diferença: +2)
```

Save both `auto_count` and `manual_count` to database.

### Database Updates

**counting_sessions additions:**
- `auto_count INTEGER` - Original AI count
- `manual_count INTEGER` - Operator correction
- `final_count COMPUTED` - manual_count if exists, else auto_count
- `rejection_reason TEXT` - Mandatory when rejected
- `validated_by VARCHAR` - Operator name/email
- `validated_at TIMESTAMP`
- `validation_notes TEXT`

**session_events additions:**
- `operator_verdict VARCHAR` - 'confirmed', 'false_positive', null

---

## Section 6: Dashboard KPIs & Excel Export

### Backend API Endpoints

```python
GET    /api/dashboard/kpis                     # Get all KPIs
GET    /api/dashboard/charts/products-by-hour  # Products per hour data
GET    /api/dashboard/charts/sessions-by-bay   # Sessions by bay data
GET    /api/dashboard/charts/confidence-dist   # Confidence distribution
GET    /api/dashboard/charts/epi-compliance    # EPI compliance rate
GET    /api/dashboard/alerts                   # Recent alerts
GET    /api/dashboard/validated-sessions       # Recent validated sessions
GET    /api/dashboard/common-false-positives   # Most common errors
POST   /api/dashboard/export                   # Generate Excel .xlsx
GET    /api/dashboard/export/<id>              # Download generated file
```

### KPIs (Top Cards)

- **Sessões hoje:** X concluídas / Y pendentes validação
- **Produtos contados hoje:** total
- **Caminhões processados hoje:** X
- **Tempo médio por sessão:** mm:ss
- **Precisão da IA:** % (auto_count vs manual_count)
- **Câmeras online:** X de Y

### Charts (using recharts)

1. **Products per hour** (bar chart, last 12h)
   - Shows volume throughout day
   - Identifies peak hours

2. **Sessions by bay** (bar chart)
   - Which bays are most active
   - Load balancing

3. **Confidence distribution** (histogram)
   - Shows model confidence level
   - If many <70%, model needs retraining

4. **EPI compliance rate** (gauge or percentage)
   - % frames with all EPIs detected
   - vs frames with violations

### Lists

1. **Recent alerts**
   - Severity icon (info/warning/critical)
   - Connect to real alert data

2. **Recent validated sessions**
   - Plate, bay, count, validator, timestamp
   - Link to session detail

3. **Common false positives**
   - Which classes AI most errors on
   - Informs retraining decisions

### Filters

- **Period:** today / last 7 days / last 30 days / custom
- **Camera:** select
- **Bay:** select
- Filters apply to ALL KPIs and charts

### Excel Export

**Button:** "Exportar" top-right

**Generated .xlsx with tabs:**

1. **Resumo** - KPIs consolidados do período
2. **Sessões** - Lista completa (data, baia, placa, contagem IA, contagem operador, duração, status, validado por)
3. **Alertas** - Lista de alertas do período
4. **Por Hora** - Contagem de produtos por hora
5. **Por Baia** - Totais por baia

**Filename:** `EPI_Monitor_Relatorio_YYYY-MM-DD.xlsx`

### Data Updates

- **KPIs and lists:** Poll every 30 seconds
- **Charts:** On period change or every 2 minutes
- **No WebSocket** needed for dashboard (not real-time critical)

### Design

- KPIs in top cards (existing structure, connect real data)
- Charts using recharts
- Maintain existing color palette
- Charts: transparent background, subtle grid, DM Sans font
- Export button follows existing button styles

---

## Section 7: Design System Consistency

### Reuse Existing Components (DO NOT recreate)

- ✅ Modal
- ✅ Toast
- ✅ Cards
- ✅ Buttons (primary, secondary, danger)
- ✅ Inputs/Forms (CameraForm style)
- ✅ StatusBadge
- ✅ StatCard
- ✅ Loading/Error/Empty states

### Design Tokens (DO NOT create new)

**Colors:**
- `--bg` - Background
- `--card` - Card background
- `--border` - Border color
- `--text` - Text color
- `--muted` - Muted text
- `--accent` - Accent color (#2563eb)

**Status colors:**
- Green: #22c55e
- Yellow: #f59e0b
- Red: #ef4444

**Fonts:**
- Text: DM Sans
- Data/numbers: DM Mono

**Border-radius:**
- Small elements: 6-8px
- Cards: 14-16px

**Animations:**
- fadeUp - Entry animations
- pulse - Active indicators
- slideIn - Side panels

**Transitions:**
- Hover states: 0.15s
- Openings: 0.3s

### New Components (must follow system)

1. **Upload Zone**
   - Dashed border: 2px dashed var(--border)
   - Border-radius: 14px
   - Hover: border-color var(--accent), background var(--accent) 5%

2. **Annotation Canvas**
   - Toolbar: background #161b22
   - Buttons: same style as grid selectors
   - Active button: background rgba(37,99,235,0.8), color #fff

3. **Event Timeline**
   - Vertical list with connector line
   - Colored dots by event type
   - Event cards follow alert card style

4. **Rule Cards**
   - Follow YOLO class cards style
   - Toggle switch for activate/deactivate
   - Same hover effect as existing cards

5. **Charts**
   - Transparent background
   - Grid: var(--border) with 50% opacity
   - Data colors: use existing status palette
   - Tooltip: background var(--card), border var(--border), border-radius 8px, DM Sans

### What NOT To Do

- ❌ Create new style guide documentation
- ❌ Uplift existing design
- ❌ Use external component libraries (Material UI, Ant Design)
- ❌ Invent new colors, fonts, or animation patterns
- ❌ Make layout "optimized for task" differently
- ❌ Alter existing components

### Consistency Test

Before delivering any new page:

1. Open Cameras page side-by-side with new page
2. Compare visually: fonts, colors, spacing, cards, buttons
3. If anything looks "different", adjust until identical
4. Navigate between all pages rapidly - should seem like the same system

---

## Implementation Order

### Phase 1: Data Pipeline
1. **Section 1:** Video upload + frame extraction + tabs
   - Upload endpoint with progress
   - Timeline selection for >10min videos
   - Chunked extraction (1min chunks, 2fps)
   - Database tables (training_videos, frames)
   - Frontend: Vídeos & Dados tab

2. **Section 2:** Annotation interface (canvas + drawing + save)
   - Annotation endpoints (get, save, predict)
   - HTML5 Canvas implementation
   - Drawing, select, delete modes
   - Keyboard shortcuts
   - Copy from previous frame
   - Frontend: Anotar tab

### Phase 2: Training Pipeline
3. **Section 3:** Training config + execution + history
   - Dataset stats endpoint
   - Training start/stop/status endpoints
   - Presets with auto-fill
   - Inline progress with polling
   - Training history with model comparison
   - Frontend: Treinar and Histórico tabs

### Phase 3: Business Logic
4. **Section 5:** Rules engine (state machine + templates)
   - State machine implementation
   - Database tables (counting_sessions, session_events, rule_configs)
   - Time-based and conditional rules
   - Template toggles
   - One bay → test → expand to multiple

5. **Section 6:** Operator validation interface
   - Pending sessions list
   - Session detail with timeline
   - Editable counts, false positive marking
   - Validate/reject actions
   - AI vs operator comparison

### Phase 4: Monitoring & Reporting
6. **Section 7:** Dashboard KPIs + Excel export
   - KPI endpoints (real-time)
   - Chart endpoints (recharts)
   - Alert and session lists
   - Excel export with 5 tabs
   - Polling implementation

7. **Section 8:** Polish visual consistency
   - Side-by-side comparison test
   - Adjust until pixel-perfect match
   - Responsive verification
   - Performance optimization

---

## Final Checklist

### Video Processing
- [ ] Video upload works with progress bar
- [ ] Timeline ruler appears for videos > 10min
- [ ] Frames extracted in 1min chunks, 2fps
- [ ] Individual image upload works
- [ ] Async processing with progress polling
- [ ] Database: training_videos, frames tables created

### Annotation
- [ ] Canvas draws, moves, resizes, deletes boxes
- [ ] Keyboard shortcuts work (1-9, Delete, arrows, Space, Escape, A)
- [ ] Copy from previous frame works
- [ ] Auto-save on navigate
- [ ] Pre-detection YOLO pre-fills boxes
- [ ] Undo/redo (max 50 actions)
- [ ] Zoom/pan functional
- [ ] Database: frame_annotations table created

### Training
- [ ] Dataset stats shows breakdown by class
- [ ] Validation prevents training without minimum data
- [ ] Presets auto-fill configuration
- [ ] Training starts with inline real progress
- [ ] Badge animates on sidebar during training
- [ ] Training continues if leaving page
- [ ] History compares new vs active model
- [ ] Model activation asks for confirmation
- [ ] Database: trained_models table exists

### Rules Engine
- [ ] State machine works for complete bay flow
- [ ] All transitions fire correctly
- [ ] Time-based rules (30s, 2min, 4h timeouts)
- [ ] Cooldown (3s) prevents duplicate counts
- [ ] Templates activate/deactivate with toggle
- [ ] Configurable thresholds per template
- [ ] Database: counting_sessions, session_events, rule_configs created

### Validation
- [ ] Pending sessions appear in list with filters
- [ ] Session detail shows timeline correctly
- [ ] Operator can correct counts
- [ ] False positives markable
- [ ] Validate/reject buttons work
- [ ] Mandatory reason on reject
- [ ] Auto_count and manual_count saved separately
- [ ] Toast notifications work

### Dashboard
- [ ] All KPIs show real data
- [ ] Charts render with recharts
- [ ] Design system consistency (transparent bg, subtle grid)
- [ ] Filters work (period, camera, bay)
- [ ] Excel exports with all 5 tabs
- [ ] Filename has correct date format
- [ ] Polling: KPIs 30s, charts 2min

### Design System
- [ ] NO existing component was altered
- [ ] ALL new components match existing styles
- [ ] Side-by-side comparison test passes
- [ ] Responsiveness works on all new pages
- [ ] DM Sans for text, DM Mono for data
- [ ] Correct border-radius (6-8px small, 14-16px cards)
- [ ] Correct status colors (green/yellow/red)
- [ ] Animations (fadeUp, pulse, slideIn) match

### Performance
- [ ] Frame images have Cache-Control headers
- [ ] Next frame pre-loads in background
- [ ] Frame list virtualizes if >200 items
- [ ] Training polling doesn't block UI
- [ ] Dashboard polling efficient
- [ ] No memory leaks in canvas

---

## Implementation Notes

### Before Starting Each Section

1. **Map existing code:**
   ```bash
   grep -rn "class YOLOTrainer" backend/
   grep -rn "class YOLOExporter" backend/
   grep -rn "training" api_server.py
   ```

2. **Check database tables:**
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name LIKE '%training%';
   ```

3. **Verify existing models:**
   ```bash
   ls -la models/*.pt
   ls -la storage/
   ```

### Testing Strategy

1. **Unit test each endpoint** with curl/Postman
2. **Integration test** each workflow end-to-end
3. **Visual consistency test** after each UI component
4. **Performance test** with large datasets (1000+ frames)
5. **User acceptance test** with real operator

### Rollback Plan

Each section should be commit independently:
```bash
git commit -m "feat(section1): video upload and frame extraction"
```

If issues arise, rollback to last known good state.

---

## Approval

**Design Review:** ✅ Approved by user 2026-03-29
**Ready for Implementation Plan:** Yes
**Estimated Complexity:** High (8 stages, pixel-perfect consistency)
**Recommended Approach:** Implement section-by-section, test thoroughly, commit frequently.

---

**Next Step:** Invoke `writing-plans` skill to create detailed implementation plan.
