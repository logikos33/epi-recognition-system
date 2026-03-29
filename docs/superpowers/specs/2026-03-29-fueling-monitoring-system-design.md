# Sistema de Monitoramento de Abastecimento - Design Document

**Date:** 2026-03-29
**Version:** 1.0
**Status:** Design Aprovado
**Next:** Implementation Plan

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Backend API](#backend-api)
5. [Frontend Components](#frontend-components)
6. [Real-time Data Flow](#real-time-data-flow)
7. [OCR & License Plate Detection](#ocr--license-plate-detection)
8. [Scale Integration](#scale-integration)
9. [Dashboard & Analytics](#dashboard--analytics)
10. [Export & PowerBI Integration](#export--powerbi-integration)
11. [Hardware Button](#hardware-button)
12. [Implementation Phases](#implementation-phases)

---

## Overview

### Purpose

Complete real-time monitoring system for truck fueling operations with multiple camera feeds, automatic license plate detection, product counting, weight integration, and business intelligence dashboards.

### Key Features

1. **Dynamic Camera Grid** - 3 primary + 9 thumbnail cameras, resizable layout (up to 12 simultaneous)
2. **License Plate OCR** - Automatic session identification per truck
3. **Product Counting** - Hybrid YOLO + human confirmation with learning loop
4. **Scale Integration** - Real-time weight tracking via API polling
5. **Transparent Overlay** - All session info overlaid on video (plate, time, count, weight, status)
6. **Dashboard Modal** - Filters, KPIs, charts with Excel/CSV/API export
7. **Hardware Button** - Physical backup for session control
8. **Multi-bay Support** - Unlimited cameras, visualize selected subset

### Context

Extends existing YOLO Training MVP (Tasks 1-13) by adding production monitoring capabilities. Focuses on truck loading bays with EPI (Equipment Protection) detection + product counting.

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 15)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐         │
│  │ Tab 1:      │  │ Tab 2:       │  │ Tab 3:          │         │
│  │ Câmeras     │  │ Dashboard    │  │ Configurações   │         │
│  │             │  │ (Modal)      │  │                │         │
│  │ ┌─────────┐ │  │              │  │ Camera List     │         │
│  │ │ Grid    │ │  │              │  │ OCR Config     │         │
│  │ │ Dynâmico│ │  │              │  │ Scale Config    │         │
│  │ └─────────┘ │  │              │  │ Layout Save     │         │
│  └─────────────┘  └──────────────┘  └──────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                         WebSocket (Real-time)
                         HTTP REST API
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (Flask + PostgreSQL)                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Camera      │  │ OCR       │  │ Scale    │  │ Dashboard  │  │
│  │ Streams    │  │ Service   │  │ Service  │  │ Service    │  │
│  │ (3 prim.  + │  │ (Tesseract│  │(Polling) │  │ (Analytics) │  │
│  │ 9 thumbs.) │  │  /YOLO)   │  │          │  │            │  │
│  └─────────────┘  └───────────┘  └──────────┘  └─────────────┘  │
│  ┌─────────────┐  ┌───────────┐  ┌──────────┐                     │
│  │ Session     │  │ Product   │  │ Export   │                     │
│  │ Manager    │  │ Counter   │  │ Service  │                     │
│  └─────────────┘  └───────────┘  └──────────┘                     │
│  ┌───────────────────────────┐                                     │
│  │ WebSocket (Real-time)      │                                     │
│  └───────────────────────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌────────────────┴─────────────┐
                    │   Hardware                   │
                    ├────────────────────────────────┤
                    │ IP Cameras (RTSP)             │
                    │ Scale (API/Serial)           │
                    │ Physical Button (GPIO/ESP32)   │
                    └────────────────────────────────┘
```

---

## Database Schema

### New Tables

```sql
-- Bays (Áreas de abastecimento)
CREATE TABLE bays (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    scale_integration BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cameras (Câmeras do sistema)
CREATE TABLE cameras (
    id SERIAL PRIMARY KEY,
    bay_id INTEGER REFERENCES bays(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    rtsp_url VARCHAR(500),  -- URL do stream RTSP
    is_active BOOLEAN DEFAULT TRUE,
    position_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fueling Sessions (Sessões de abastecimento)
CREATE TABLE fueling_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bay_id INTEGER REFERENCES bays(id),
    camera_id INTEGER REFERENCES cameras(id),
    license_plate VARCHAR(20),
    truck_entry_time TIMESTAMP NOT NULL,
    truck_exit_time TIMESTAMP,
    duration_seconds INTEGER,
    products_counted JSONB,  -- {caixas: 120, pallets: 3, ...}
    final_weight FLOAT,
    status VARCHAR(20) DEFAULT 'active',  -- active, completed
    created_at TIMESTAMP DEFAULT NOW()
);

-- Counted Products (Produtos contados)
CREATE TABLE counted_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES fueling_sessions(id) ON DELETE CASCADE,
    product_type VARCHAR(100) NOT NULL,  -- "caixa", "pallet", "saco", etc.
    quantity INTEGER NOT NULL,
    confidence FLOAT,
    confirmed_by_user BOOLEAN DEFAULT FALSE,
    is_ai_suggestion BOOLEAN DEFAULT TRUE,
    corrected_to_type VARCHAR(100),  -- Se operador corrigeu tipo
    timestamp TIMESTAMP DEFAULT NOW()
);

-- User Layouts (Layouts salvos por usuário)
CREATE TABLE user_camera_layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    layout_name VARCHAR(100),
    selected_cameras INTEGER[],  -- Array of camera IDs
    camera_configs JSONB,  -- {cam_id: {size, position, ...}}
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes

```sql
CREATE INDEX idx_sessions_bay ON fueling_sessions(bay_id);
CREATE INDEX idx_sessions_plate ON fueling_sessions(license_plate);
CREATE INDEX idx_sessions_status ON fueling_sessions(status);
CREATE INDEX idx_sessions_entry ON fueling_sessions(truck_entry_time DESC);
CREATE INDEX idx_products_session ON counted_products(session_id);
CREATE INDEX idx_products_timestamp ON counted_products(timestamp);
```

---

## Backend API

### Camera Management

```python
GET    /api/cameras                    # List all cameras
POST   /api/cameras                    # Create camera
PUT    /api/cameras/<id>               # Update camera
DELETE /api/cameras/<id>               # Delete camera
GET    /api/cameras/by-bay/<bay_id>       # Get cameras by bay
```

### Session Management

```python
POST   /api/fueling/start              # Start session (OCR/manual plate)
GET    /api/fueling/sessions/active     # Get active sessions
GET    /api/fueling/sessions/<session_id> # Get session details
PUT    /api/fueling/sessions/<session_id> # Update session
POST   /api/fueling/sessions/<session_id>/complete # Complete session
GET    /api/fueling/sessions/by-bay/<bay_id> # Get sessions by bay
```

### Product Counting

```python
POST   /api/products/count            # Register counted product (AI suggestion)
PUT    /api/products/count/<id>         # Confirm/correct product
GET    /api/products/session/<session_id> # Get session products
DELETE /api/products/count/<id>       # Delete product entry
```

### Scale Integration

```python
GET    /api/scale/weight/<bay_id>        # Get current weight
POST   /api/scale/tare                  # Tare (zerar balança)
PUT    /api/scale/calibrate             # Calibrate scale
```

### Real-time Stream

```python
WS     /api/ws/fueling-updates         # WebSocket stream (dashboard updates)
```

### Dashboard & Export

```python
GET    /api/dashboard/kpis              # Get KPIs
GET    /api/dashboard/products-hourly    # Products per hour
POST   /api/export/csv                  # Export CSV
POST   /api/export/excel               # Export Excel (.xlsx)
GET    /api/fueling/sessions          # Get sessions (PowerBI)
```

---

## Frontend Components

### Page Structure

```
frontend/src/app/dashboard/monitoring/page.tsx
├── Tabs (Câmeras | Dashboard | Configurações)
├── CameraGrid (Tab 1)
│   ├── CameraContainer (3 primary)
│   ├── ThumbnailsList (9 thumbnails)
│   └── CameraListSidebar (all cameras)
├── DashboardModal (Tab 2 - overlay)
└── ConfigPanel (Tab 3)
```

### Key Components

#### 1. CameraGrid.tsx

```typescript
interface CameraGridConfig {
  primaryCameras: number[];      // IDs of 3 expanded cameras
  thumbnailCameras: number[];   // IDs of 9 thumbnails
  layout: CameraLayout[];        // Position/size for each
}

interface CameraLayout {
  cameraId: number;
  x: number;  y: number;
  width: number; height: number;
  zIndex: number;
}
```

**Features:**
- Drag & drop to reposition
- Resize handles on borders
- Double-click to expand/collapse
- Save layout to user profile
- Responsive (1/2/3 columns on mobile/tablet/desktop)

#### 2. InfoOverlay.tsx

```typescript
interface SessionInfo {
  licensePlate: string;
  entryTime: Date;
  elapsedTime: string;  // "12:45"
  productCount: number;
  currentWeight: number;
  status: 'active' | 'completed' | 'paused';
}
```

**Design:**
- Semi-transparent black background (70% opacity)
- Backdrop blur for readability
- 80px height top overlay (or corner overlay)
- Animated updates when data changes
- Auto-collapse when no session active

#### 3. DashboardModal.tsx

**Components:**
- Date range picker (last 24h, 7 days, custom)
- License plate search
- Bay selector
- Product type filter
- KPI cards (total sessions, avg duration, products/hour)
- Charts:
  - Line chart: Products per hour
  - Bar chart: Top 10 products
  - Pie chart: Distribution by product type
- Export buttons (CSV, Excel, Copy API URL)

#### 4. ProductConfirmationPanel.tsx

**Features:**
- Slide-up panel from bottom of video
- Shows AI-detected products
- Each row shows:
  - Product type (caixa, pallet, etc.)
  - AI confidence
  - Suggested quantity
  - Confirm/Reject buttons
  - Adjust (+/-) controls
  - Free text field for correction

**Learning Loop:**
- User correction → Add to training dataset
- Retrain YOLO with corrections
- Better suggestions over time

---

## Real-time Data Flow

### Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Truck enters bay                                          │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Camera detects plate (OCR)                                 │
│    - Tesseract / YOLO-OCR                                  │
│    - Returns: "ABC-1234"                                    │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend creates session                                     │
│    POST /api/fueling/start                                 │
│    - plate: "ABC-1234"                                      │
│    - bay_id: 1                                             │
│    - entry_time: NOW()                                       │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Frontend displays overlay (transparent)                     │
│    - Shows: plate, time, count, weight, status                │
│    - Updates in real-time                                   │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Product counting (YOLO + Human)                           │
│    a) YOLO detects objects → Suggests products                 │
│    b) Operator confirms/corrects                             │
│    c) Count updates in real-time                               │
│    d) Dashboard shows live graph                               │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Scale integration (polling every 5s)                        │
│    - GET /api/scale/weight/<bay_id>                          │
│    - Updates overlay weight                                   │
│    - Records final weight on completion                        │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Session completion detection                                 │
│    a) No frame for 5+ minutes → Complete                     │
│    b) New plate detected → Complete old, start new              │
│    c) Manual button press → Complete                          │
│    d) timeout: inactive for 5 minutes                         │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Finalize session                                            │
│    - Calculate total duration                                │
│    - Save final weight                                        │
│    - Mark status: 'completed'                                │
│    - Dashboard records complete session                       │
└──────────────────────────────────────────────────────────────┘
```

---

## OCR & License Plate Detection

### Implementation Options

#### Option A: Tesseract OCR (Recommended for Brazil)

**Pros:**
- Free, open-source
- Good for Brazilian plates
- Works offline
- Python package: `pytesseract`

**Cons:**
- Requires preprocessing (grayscale, thresholding)
- Lower accuracy than YOLO-OCR
- Requires bounding box detection first

#### Option B: YOLO-OCR (End-to-End)

**Pros:**
- Higher accuracy
- Detects plate + reads text in one pass
- Works on low resolution

**Cons:**
- Requires training dataset
- More resource-intensive
- Less mature than Tesseract

#### Recommendation: Hybrid Approach

1. **Use Tesseract initially** (faster to implement)
2. **Train YOLO-OCR later** (Task for Phase 2)
3. **Fallback:** Manual plate entry if OCR fails

### Backend Implementation

```python
# backend/ocr_service.py

import pytesseract
from PIL import Image
import cv2
import numpy as np

class OCRService:
    @staticmethod
    def detect_license_plate(frame: np.ndarray) -> str | None:
        """
        Detect and read license plate from frame.

        Args:
            frame: numpy array (BGR image from video)

        Returns:
            Plate string (e.g., "ABC-1234") or None
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply threshold
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Find contours (potential plates)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)

                # Brazilian plate: 4:1 aspect ratio (approx)
                if 2.0 < aspect_ratio < 5.0 and w > 80 and h > 20:
                    # Extract plate region
                    plate_region = gray[y:y+h, x:x+w]

                    # OCR with Tesseract
                    # Configure for Brazilian plates (Mercosul)
                    plate_text = pytesseract.image_to_string(
                        plate_region,
                        config='--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    )

                    # Clean and format (ABC-1234 format)
                    plate = self._format_plate(plate_text)

                    if plate:
                        logger.info(f"✅ Plate detected: {plate}")
                        return plate

            logger.warning("⚠️ No license plate detected")
            return None

        except Exception as e:
            logger.error(f"❌ OCR error: {e}")
            return None

    @staticmethod
    def _format_plate(raw_text: str) -> str | None:
        """Format raw OCR text to Brazilian plate format."""
        import re

        # Remove spaces and special characters
        text = re.sub(r'[^A-Za-z0-9]', '', raw_text)

        # Extract letters (3) and numbers (4)
        match = re.match(r'^([A-Za-z]{3})(\d{4})$', text)

        if match:
            letters, numbers = match.groups()
            return f"{letters.upper()}-{numbers}"

        return None
```

### API Endpoint

```python
# In api_server.py

@app.route('/api/ocr/detect-plate', methods=['POST'])
def detect_plate():
    """
    Detect license plate from frame image.

    Expects JSON:
    {
        "image": "data:image/jpeg;base64,...",
        "bay_id": 1
    }
    """
    data = request.get_json()

    # Decode image
    image_data = data['image'].split(',')[1]
    image_bytes = base64.b64decode(image_data)
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Detect plate
    plate = OCRService.detect_license_plate(frame)

    if plate:
        return jsonify({
            'success': True,
            'plate': plate,
            'confidence': 0.85  # Placeholder (calculate with YOLO-OCR)
        })
    else:
        return jsonify({
            'success': False,
            'plate': None
        })
```

---

## Scale Integration

### Hardware Options

1. **Rice Lake Scale** - HTTP REST API
2. **Toledo Scale** - Serial (RS232) or Modbus TCP
3. **Mettler Toledo** - Ethernet/Modbus
4. **Generic Scale** - Serial/USB with custom driver

### Backend Service

```python
# backend/scale_service.py

class ScaleService:
    @staticmethod
    def get_weight(bay_id: int, db: Session) -> dict:
        """
        Get current weight from scale.

        Returns:
            {"weight": 8450, "unit": "kg", "timestamp": "..."}
        """
        bay = get_bay(db, bay_id)

        if not bay.get('scale_integration'):
            # Mock weight if no scale
            return {"weight": 0, "unit": "kg", "timestamp": None}

        # TODO: Implement based on scale type
        # For now, return mock data
        import random
        return {
            "weight": 8000 + random.randint(-500, 500),
            "unit": "kg",
            "timestamp": datetime.now().isoformat()
        }
```

### API Endpoint

```python
@app.route('/api/scale/weight/<int:bay_id>', methods=['GET'])
def get_scale_weight(bay_id: int):
    """
    Get current weight from bay scale.
    Poll every 5 seconds from frontend.
    """
    db = next(get_db())
    weight_data = ScaleService.get_weight(bay_id, db)
    return jsonify(weight_data)
```

---

## Dashboard & Analytics

### KPIs Calculated

1. **Total Sessions Today** - Count of `fueling_sessions` where `truck_entry_time >= TODAY()`
2. **Average Duration** - AVG(`duration_seconds`) where `status = 'completed'`
3. **Products per Hour** - SUM(`products_counted`) / hours active
4. **Top Products** - GROUP BY product_type, ORDER BY SUM(quantity) DESC

### Dashboard Filters

1. **Date Range:** Last 24h, 7 days, 30 days, custom
2. **License Plate:** Fuzzy search (ABC-1234 matches ABC1234, abc-1234)
3. **Bay:** Multi-select dropdown
4. **Product Type:** Checkbox list (caixa, pallet, saco, etc.)

### Charts

1. **Products per Hour (Line Chart)**
   - X-axis: Hour (00:00, 01:00, ..., 23:00)
   - Y-axis: Total products counted
   - Series: Line with dots

2. **Top 10 Products (Bar Chart)**
   - X-axis: Product type
   - Y-axis: Total quantity

3. **Bay Utilization (Pie Chart)**
   - Labels: Bay names
   - Values: Percentage of time occupied

---

## Export & PowerBI Integration

### Export Formats

#### 1. CSV Export

**Endpoint:** `POST /api/export/csv`

```python
def export_sessions_to_csv(
    start_date: str,
    end_date: str,
    bay_ids: List[int] = None,
    format: str = "detailed"  # detailed, summary
):
    """
    Generate CSV file with session data.

    Returns:
        File download response
    """
```

**Columns:**
- Session ID
- Bay
- License Plate
- Entry Time
- Exit Time
- Duration (minutes)
- Product Types (JSON)
- Total Products
- Final Weight (kg)
- Status

#### 2. Excel Export (.xlsx)

**Libraries:** `openpyxl` or `xlsxwriter`

**Features:**
- Multiple sheets (Sessions, Products, Summary)
- Formatting (headers, colors, borders)
- Charts embedded
- Auto-column width

#### 3. PowerBI API

**Endpoint:** `GET /api/fueling/sessions?format=powerbi`

**Returns:**
```json
{
  "sessions": [
    {
      "id": "...",
      "bay_name": "Baia 1",
      "license_plate": "ABC-1234",
      "truck_entry_time": "2026-03-29T14:32:05Z",
      "truck_exit_time": "2026-03-29T14:45:00Z",
      "duration_minutes": 12,
      "products_counted": {"caixas": 120, "pallets": 3},
      "final_weight_kg": 8450,
      "status": "completed",
      "products": [
        {"type": "caixa", "quantity": 120, "confirmed": true},
        {"type": "pallet", "quantity": 3, "confirmed": true}
      ]
    }
  ]
}
```

**PowerBI Setup:**
1. Data Source: REST API
2. URL: `https://your-api.com/api/fueling/sessions?format=powerbi`
3. Authentication: Bearer token
4. Refresh: 1 minute (incremental updates)
5. Headers: Authorization header

---

## Hardware Button

### Options

#### Option A: ESP32 (Recommended for low cost)

**Pros:**
- Wi-Fi built-in
- Low power (battery or PoE)
- Easy to program (MicroPython)
- Cost: ~$10-20

**Cons:**
- Requires coding
- Battery needs replacement

#### Option B: Raspberry Pi + GPIO Button

**Pros:**
- Full Linux OS
- Easy to integrate with existing system
- Can run local services

**Cons:**
- More expensive ($40-60)
- Requires PoE hat

### Implementation (ESP32)

```cpp
// ESP32 Firmware
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
const char* serverUrl = "https://your-api.com/api/hardware/button";

const int BUTTON_PIN = 4;
int lastState = HIGH;

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(115200);
  WiFi.begin(ssid, password);
}

void loop() {
  int currentState = digitalRead(BUTTON_PIN);

  // Detect falling edge (press)
  if (currentState == LOW && lastState == HIGH) {
    sendButtonPress();
    delay(200); // Debounce
  }

  lastState = currentState;
}

void sendButtonPress() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);

    http.addHeader("Content-Type", "application/json");

    // Get bay_id from config or memory
    int bayId = 1;  // TODO: Load from config

    String payload = "{\"bay_id\": " + String(bayId) + "}";

    int httpCode = http.POST(payload);

    if (httpCode == 200) {
      Serial.println("✅ Button press sent");
    } else {
      Serial.println("❌ Button press failed");
    }

    http.end();
  }
}
```

### Backend Endpoint

```python
@app.route('/api/hardware/button-press', methods=['POST'])
def hardware_button_press():
    """
    Handle physical button press from ESP32.
    Toggles or creates session in the bay.
    """
    data = request.get_json()
    bay_id = data.get('bay_id')

    db = next(get_db())

    # Check for active session in bay
    active_session = get_active_session(db, bay_id)

    if active_session:
        # Complete existing session
        complete_fueling_session(db, active_session['id'])
        message = "Session completed via button"
    else:
        # Create new session (manual - no plate yet)
        session_id = create_manual_session(db, bay_id)
        message = "New session started via button"

    return jsonify({
        'success': True,
        'message': message,
        'session_id': str(session_id) if 'session_id' in locals() else None
    })
```

---

## Implementation Phases

### Phase 1: Foundation (Est. 4-6 hours)

**Goal:** Basic multi-camera grid without session management

1. Database migrations (fueling_sessions, cameras, bays tables)
2. Backend: CameraService (CRUD), dummy stream endpoints
3. Frontend: CameraGrid component (3 primary + 9 thumbnails)
4. Drag & drop layout (react-grid-layout or custom)
5. InfoOverlay component (static data for now)
6. Tab navigation

**Deliverable:**
- Grid com 3 câmeras expandidas
- 9 thumbnails laterais
- Redimensionamento de câmeras
- Tabs funcionais

### Phase 2: Session Management (Est. 6-8 hours)

**Goal:** Complete session lifecycle

1. Backend: SessionManager (create, update, complete)
2. Database: fueling_sessions table
3. API endpoints: /api/fueling/start, /get/active, /complete
4. Frontend: useFuelingSessions hook (React Query)
5. Session info in InfoOverlay (connect to real session data)
6. Auto-complete logic (5min timeout OR new plate)

**Deliverable:**
- Sessões criadas automaticamente (OCR ou manual)
- Overlay mostra dados reais da sessão
- Status muda automaticamente

### Phase 3: OCR Integration (Est. 4-6 hours)

**Goal:** License plate detection

1. Backend: OCRService with Tesseract
2. Training: Brazilian plate dataset
3. API endpoint: /api/ocr/detect-plate
4. Frontend: detectPlate() function called on video frames
5. Integration: SessionManager.start_session() with OCR

**Deliverable:**
- Placas detectadas automaticamente
- Sessões iniciadas sem intervenção manual
- Manual override disponível

### Phase 4: Product Counting (Est. 8-10 hours)

**Goal:** Hybrid YOLO + human confirmation

1. Extend YOLO model for product types (caixa, pallet, saco, etc.)
2. Backend: ProductCounter service
3. Database: counted_products table
4. API: /api/products/count, /confirm, /correct
5. Frontend: ProductConfirmationPanel
6. Learning loop: Corrections → training dataset

**Deliverable:**
- YOLO sugere produtos
- Operador confirma/corrige
- Contagem em tempo real no overlay
- Sistema melhora com feedback

### Phase 5: Scale Integration (Est. 4-6 hours)

**Goal:** Weight tracking

1. Backend: ScaleService (polling-based)
2. API: /api/scale/weight/<bay_id>
3. Frontend: useScaleWeight hook (5s polling)
4. Display in InfoOverlay
5. Record final weight on session completion

**Deliverable:**
- Peso atualizado em tempo real
- Histórico de pesos por sessão
- Final weight registrado

### Phase 6: Dashboard (Est. 8-10 hours)

**Goal:** Analytics modal

1. Backend: DashboardService (KPIs, aggregates)
2. API: /api/dashboard/kpis, /products-hourly, /export
3. Frontend: DashboardModal component
4. Filters: Date, plate, bay, product type
5. Charts: Line, Bar, Pie
6. Export: CSV, Excel

**Deliverable:**
- Dashboard modal funcional
- Filtros aplicáveis
- Gráficos interativos
- Exportação em 3 formatos

### Phase 7: Hardware Button (Est. 4-6 hours)

**Goal:** Physical control

1. ESP32 firmware (MicroPython)
2. Button integration with GPIO
3. Backend endpoint: /api/hardware/button-press
4. Backend logic: Toggle session in bay
5. Testing & deployment

**Deliverable:**
- Botão físico funcional
- Toggle de sessões por hardware
- Backup para falha de OCR

### Phase 8: Polish & Optimize (Est. 4-6 hours)

**Goal:** Production-ready

1. Performance optimization (lazy loading streams)
2. Error handling & recovery
3. Loading states
4. User documentation
5. Testing (manual + automated)
6. Deployment to Railway

**Deliverable:**
- Sistema completo testado
- Deployado em produção
- Documentação completa

---

## Summary

**Total Estimated Time:** 38-54 hours (across 8 phases)

**Key Components:**
- 5 new database tables
- 15+ backend API endpoints
- 10 frontend React components
- 3 new hooks (camera streams, sessions, scale)
- 1 WebSocket stream
- 2 export formats (CSV, Excel)
- PowerBI integration

**Tech Stack:**
- Backend: Flask + PostgreSQL + Tesseract + YOLOv8
- Frontend: Next.js 15 + TypeScript + Tailwind CSS + React Query
- Hardware: IP Cameras (RTSP), Scale (API/Serial), ESP32 Button
- BI: PowerBI (REST API integration)

---

**Ready for Implementation Plan creation.**
