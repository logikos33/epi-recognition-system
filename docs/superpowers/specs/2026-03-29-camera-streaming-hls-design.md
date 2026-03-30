# Camera Streaming System with HLS and YOLO Integration

**Date:** 2026-03-29
**Status:** Design Approved
**Author:** Claude (Superpowers Brainstorming)

## Overview

A complete IP camera management and real-time streaming system with integrated YOLO object detection. The system supports Intelbras and Hikvision IP cameras, processes RTSP streams via FFmpeg into HLS format for browser playback, and runs continuous YOLO detection for product/EPI counting.

**Key Features:**
- Support for 12 simultaneous camera streams (3 primary large views + 9 thumbnails)
- Real-time HLS streaming with <3 second latency
- Continuous YOLO detection at 5 FPS per camera
- Automatic reconnection with exponential backoff
- Browser-based playback with hls.js
- WebSocket synchronization of detection results

**Target:** 85%+ detection accuracy for products and EPIs during vehicle loading operations.

---

## Architecture

### System Diagram

```
┌─────────────┐
│ IP Camera   │ RTSP Stream
│ (Intelbras/ │──────────┐
│ Hikvision)  │          │
└─────────────┘          │
                          ▼
                   ┌─────────────┐
                   │   FFmpeg    │ Process video
                   │  subprocess │ ───► HLS segments
                   └─────────────┘       (disk)
                          │
                          ├──────────────────────┐
                          ▼                      ▼
                    ┌──────────┐          ┌──────────┐
                    │   HLS    │          │  Frames  │
                    │  Files    │          │  raw     │
                    └──────────┘          └──────────┘
                          │                      │
                          ▼                      ▼
                   ┌─────────────┐        ┌──────────┐
                   │ Frontend    │        │   YOLO   │ Detection
                   │ (hls.js)    │        │ Thread   │ continuous
                   └─────────────┘        └──────────┘
                          │                      │
                          │                      ▼
                   ┌─────────────┐        ┌──────────┐
                   │  Video +    │◄───────│ Bounding │
                   │  Overlay    │  WS/SSE│  boxes   │
                   └─────────────┘        └──────────┘
```

### Component Architecture

**Backend (Flask):**
- `StreamManager` - Manages FFmpeg subprocesses (start/stop/restart)
- `YOLOProcessor` - Thread-based continuous detection per camera
- `CameraService` (expanded) - CRUD + RTSP URL building
- `RTSPBuilder` - Generates camera-specific RTSP URLs

**Frontend (Next.js):**
- `HLSCameraFeed` - HLS player with YOLO overlay
- `CameraGrid` - 12-camera grid layout (3 primary + 9 thumbnails)
- `useHLSStream` - React hook for stream lifecycle management

**Communication:**
- HLS segments served via static files
- WebSocket (or SSE) for real-time detection results

---

## Database Schema

### cameras Table

```sql
CREATE TABLE cameras (
  id                  SERIAL PRIMARY KEY,
  user_id             UUID         NOT NULL REFERENCES users(id),
  name                VARCHAR(100) NOT NULL,
  manufacturer        VARCHAR(50)  NOT NULL, -- 'intelbras', 'hikvision', 'generic'
  type                VARCHAR(20)  NOT NULL DEFAULT 'ip', -- 'ip', 'dvr', 'nvr'
  ip                  VARCHAR(50)  NOT NULL,
  port                INTEGER      NOT NULL DEFAULT 554,
  username            VARCHAR(100),
  password            VARCHAR(100),
  channel             INTEGER      NOT NULL DEFAULT 1,
  subtype             INTEGER      NOT NULL DEFAULT 1, -- 0=main, 1=sub-stream
  rtsp_url            VARCHAR(500), -- Auto-generated (can be overridden)
  is_active           BOOLEAN      DEFAULT true,
  is_streaming        BOOLEAN      DEFAULT false, -- Runtime status (not persisted)
  last_connected_at   TIMESTAMP,
  connection_error    TEXT,
  created_at          TIMESTAMP    DEFAULT NOW(),

  CONSTRAINT cameras_user_id_fkey FOREIGN KEY (user_id)
    REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_cameras_user_id ON cameras(user_id);
CREATE INDEX idx_cameras_is_active ON cameras(is_active);
```

**Field Descriptions:**
- `manufacturer`: Determines RTSP URL pattern
- `channel`: DVR/NVR channel (1-32)
- `subtype`: 0 = main stream (high quality), 1 = sub-stream (low latency)
- `is_streaming`: Transient flag indicating current stream status

---

## Backend Implementation

### Module Structure

```
backend/
├── stream_manager.py      # NEW: FFmpeg subprocess management
├── yolo_processor.py      # NEW: Continuous YOLO detection thread
├── camera_service.py      # EXPANDED: CRUD + RTSP URL building
└── rtsp_builder.py        # NEW: Camera-specific URL generator
```

### StreamManager Class

**File:** `backend/stream_manager.py`

**Responsibilities:**
- Start/stop FFmpeg subprocesses for each camera
- Monitor stream health
- Manage HLS segment lifecycle
- Handle reconnection with exponential backoff
- Clean up resources on stop

**Key Methods:**
```python
class StreamManager:
    def __init__(self):
        self.active_streams: Dict[int, subprocess.Popen] = {}
        self.hls_base_dir = "./streams"

    def start_stream(self, camera_id: int, rtsp_url: str) -> Dict:
        """Start FFmpeg → HLS conversion"""

    def stop_stream(self, camera_id: int) -> bool:
        """Stop stream and clean up HLS files"""

    def get_stream_status(self, camera_id: int) -> Dict:
        """Get current stream status"""

    def restart_stream(self, camera_id: int) -> Dict:
        """Restart stream with error recovery"""

    def check_stream_health(self, camera_id: int) -> bool:
        """Verify stream is producing segments"""
```

**FFmpeg Command:**
```bash
ffmpeg -rtsp_transport tcp \
       -i rtsp://user:pass@ip:port/path \
       -c:v libx264 \
       -preset ultrafast \
       -tune zerolatency \
       -b:v 512k \
       -s 640x360 \
       -f hls \
       -hls_time 1 \
       -hls_list_size 3 \
       -hls_flags delete_segments \
       ./streams/{camera_id}/stream.m3u8
```

### YOLOProcessor Class

**File:** `backend/yolo_processor.py`

**Responsibilities:**
- Capture frames from FFmpeg stream
- Run YOLO detection at configurable FPS (default: 5)
- Publish results via WebSocket/SSE
- Thread lifecycle management

**Key Methods:**
```python
class YOLOProcessor(threading.Thread):
    def __init__(self, camera_id: int, rtsp_url: str, model, fps: int = 5):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model = model
        self.fps = fps
        self.detection_callback = None  # Send results via WebSocket

    def run(self):
        """Main detection loop"""
        while self.running:
            # 1. Capture frame from stream
            # 2. Run YOLO model.predict()
            # 3. Filter by confidence threshold
            # 4. Publish results via callback
            # 5. Sleep for 1/fps seconds

    def stop(self):
        """Graceful shutdown"""
```

### RTSPBuilder Class

**File:** `backend/rtsp_builder.py`

**Responsibilities:**
- Generate RTSP URLs based on manufacturer
- Support Intelbras, Hikvision, and generic ONVIF

**Implementation:**
```python
class RTSPBuilder:
    @staticmethod
    def build_url(camera: Dict) -> str:
        """Build RTSP URL from camera config"""
        auth = f"{camera['username']}:{camera['password']}"
        base = f"rtsp://{auth}@{camera['ip']}:{camera['port']}"

        if camera['manufacturer'] == 'intelbras':
            channel = camera['channel']
            subtype = camera['subtype']
            return f"{base}/cam/realmonitor?channel={channel}&subtype={subtype}"

        elif camera['manufacturer'] == 'hikvision':
            # Hikvision uses channel * 100 + (subtype == 0 ? 1 : 2)
            stream_id = (camera['channel'] * 100) + (1 if camera['subtype'] == 0 else 2)
            return f"{base}/Streaming/Channels/{stream_id}"

        else:  # generic ONVIF
            return f"{base}/stream{camera['channel']}"
```

### API Endpoints

**Camera Management:**
```
GET    /api/cameras                    # List user's cameras
POST   /api/cameras                    # Create camera
GET    /api/cameras/:id                # Get camera details
PUT    /api/cameras/:id                # Update camera
DELETE /api/cameras/:id                # Delete camera
```

**Connectivity Testing:**
```
POST   /api/cameras/test               # Test connection before saving
```
Request body: `{ rtsp_url: string }`
Response: `{ connected: boolean, message: string }`

**Stream Control:**
```
POST   /api/cameras/:id/stream/start   # Start HLS stream
POST   /api/cameras/:id/stream/stop    # Stop stream
GET    /api/cameras/:id/stream/status  # Get stream status
GET    /api/streams/status             # All active streams
```

**HLS Segment Serving (static):**
```
GET    /streams/:camera_id/stream.m3u8 # HLS playlist
GET    /streams/:camera_id/*.ts        # Video segments
```

**Real-time Detections:**
```
WS     /ws/detections/:camera_id       # WebSocket for bounding boxes
```
Message format:
```json
{
  "camera_id": 1,
  "timestamp": 1701234567,
  "frame_id": 12345,
  "detections": [
    {
      "class": "person",
      "confidence": 0.89,
      "bbox": [100, 150, 300, 450]
    }
  ]
}
```

---

## Frontend Implementation

### Component Structure

```typescript
frontend/src/
├── components/
│   ├── hls-camera-feed.tsx          # HLS player + YOLO overlay
│   └── camera-grid.tsx              # 12-camera grid layout
├── hooks/
│   └── useHLSStream.ts              # Stream lifecycle management
├── lib/
│   └── rtsp-builder.ts              # URL building helper
└── types/
    └── camera.ts                     # TypeScript interfaces
```

### HLSCameraFeed Component

**File:** `frontend/src/components/hls-camera-feed.tsx`

**Responsibilities:**
- Initialize hls.js player with backend HLS URL
- Connect to WebSocket for detection results
- Draw bounding box overlay synchronized with video
- Handle connection errors and auto-reconnect

**Key Features:**
```typescript
interface HLSCameraFeedProps {
  cameraId: number;
  mode: 'primary' | 'thumbnail';
}

// Features:
- hls.js initialization with low-latency config
- WebSocket subscription to /ws/detections/:camera_id
- Canvas overlay for bounding boxes
- Error handling with retry logic
- Connection status indicator
- FPS and latency metrics
```

**hls.js Configuration:**
```typescript
const hls = new Hls({
  maxBufferLength: 5,
  maxMaxBufferLength: 10,
  liveSyncDurationCount: 2,
  liveMaxLatencyDurationCount: 4,
  enableWorker: true,
  lowLatencyMode: true
});
```

### CameraGrid Component

**File:** `frontend/src/components/camera-grid.tsx`

**Layout:**
```
┌──────────┬──────────┬──────────┐
│ Camera 1 │ Camera 2 │ Camera 3 │  ← 3 Primary (large)
├──────────┼──────────┼──────────┤
│    4     │    5     │    6     │
├──────────┼──────────┼──────────┤
│    7     │    8     │    9     │  ← 9 Thumbnails (small)
├──────────┼──────────┼──────────┤
│   10     │   11     │   12     │
└──────────┴──────────┴──────────┘
```

**Features:**
- IntersectionObserver for lazy loading (only active streams for visible cameras)
- Drag and drop reordering
- Promote/demote cameras between primary and thumbnail
- Responsive layout (mobile: 1 column, tablet: 2, desktop: 3)

### TypeScript Interfaces

```typescript
interface Camera {
  id: number;
  user_id: string;
  name: string;
  manufacturer: 'intelbras' | 'hikvision' | 'generic';
  type: 'ip' | 'dvr' | 'nvr';
  ip: string;
  port: number;
  username: string;
  password: string;
  channel: number;
  subtype: number;
  rtsp_url: string;
  is_active: boolean;
  is_streaming: boolean;
  last_connected_at: string | null;
  connection_error: string | null;
  created_at: string;
}

interface Detection {
  camera_id: number;
  timestamp: number;
  frame_id: number;
  detections: Array<{
    bbox: [number, number, number, number];  // [x1, y1, x2, y2]
    class: string;
    confidence: number;
  }>;
}

interface StreamStatus {
  camera_id: number;
  status: 'idle' | 'starting' | 'streaming' | 'error';
  hls_url: string | null;
  error: string | null;
  started_at: string | null;
}
```

---

## Stream Lifecycle Management

### Stream States

```
IDLE → STARTING → STREAMING → STOPPING → IDLE

IDLE:
  - No FFmpeg subprocess
  - No YOLO thread
  - HLS files cleaned

STARTING:
  - FFmpeg subprocess started
  - Waiting for first .m3u8 segment
  - YOLO thread initializing

STREAMING:
  - FFmpeg processing video
  - YOLO detecting at 5 FPS
  - Frontend playing HLS
  - WebSocket sending detections

STOPPING:
  - Graceful FFmpeg shutdown
  - YOLO thread stopped
  - HLS files removed
  - WebSocket disconnected

IDLE (return):
  - Resources cleaned
  - Ready for next start
```

### Cleanup Sequence

```python
def cleanup_camera_resources(self, camera_id: int):
    """Complete resource cleanup for a camera"""
    # 1. Kill FFmpeg subprocess
    if camera_id in self.active_streams:
        self.active_streams[camera_id].kill()
        del self.active_streams[camera_id]

    # 2. Stop YOLO thread
    if camera_id in self.yolo_threads:
        self.yolo_threads[camera_id].stop()
        del self.yolo_threads[camera_id]

    # 3. Remove HLS files
    hls_dir = f"{self.hls_base_dir}/{camera_id}"
    if os.path.exists(hls_dir):
        shutil.rmtree(hls_dir)

    # 4. Close WebSocket connections
    self.close_websocket(camera_id)
```

### Health Monitoring

**Health Check Interval:** Every 30 seconds

**Checks:**
- FFmpeg subprocess still running?
- Last HLS segment < 5 seconds old?
- YOLO thread producing detections?
- WebSocket connections active?

**Recovery Actions:**
- Stream stale → restart FFmpeg
- FFmpeg crashed → restart with backoff
- No detections for 60s → log warning, continue
- Network error → mark camera offline, retry in 30s

---

## Error Handling & Reconnection

### Error Types

| Error | Recovery Strategy |
|-------|------------------|
| FFmpeg failed to start | Mark offline, retry in 30s |
| FFmpeg crashed mid-stream | Auto-restart with exponential backoff (1s, 2s, 4s, ..., max 30s) |
| No HLS segments for 10s | Restart stream |
| WebSocket disconnected | Auto-reconnect |
| YOLO OOM/failed | Log error, continue stream without detection |
| Camera network down | Mark offline, stop FFmpeg to save CPU |

### Exponential Backoff

```python
def reconnect_with_backoff(self, camera_id: int, attempt: int):
    delay = min(1000 * 2 ** attempt, 30000)  # Max 30s

    print(f"[Camera {camera_id}] Reconnecting in {delay}ms (attempt {attempt})")

    time.sleep(delay / 1000)

    if attempt > 10:
        self.mark_camera_offline(camera_id)
        return

    try:
        self.start_stream(camera_id)
    except Exception as e:
        self.reconnect_with_backoff(camera_id, attempt + 1)
```

### UI Error States

```typescript
type StreamStatus =
  | 'idle'          // No stream
  | 'connecting'    // Starting up
  | 'streaming'     // Live
  | 'error'         // Recoverable error
  | 'offline'       // Camera unreachable

// User Messages:
- "Conectando..." (spinning)
- "Ao Vivo" (green badge)
- "Reconectando..." (yellow, with retry counter)
- "Câmera Offline" (red, shows last error)
- "Erro no Stream" (yellow, error details)
```

---

## Configuration

### Environment Variables

```bash
# .env
FFMPEG_PATH=/usr/bin/ffmpeg
HLS_BASE_DIR=./streams
HLS_SEGMENT_DURATION=1         # 1 second per segment
HLS_LIST_SIZE=3                # Keep 3 segments in playlist
YOLO_DETECTION_FPS=5           # 5 detections per second
MAX_CONCURRENT_STREAMS=12       # Maximum simultaneous streams
STREAM_HEALTH_CHECK_INTERVAL=30 # Health check every 30s
RECONNECT_MAX_DELAY=30         # Max reconnection delay (seconds)
```

### Python Dependencies

```bash
# requirements.txt (add)
flask-socketio>=5.3.0
python-socketio>=5.10.0
eventlet>=0.33.0
```

### Frontend Dependencies

```bash
# package.json (add)
"hls.js": "^1.4.0"
```

### Railway Deployment (nixpacks.toml)

```toml
[phases.setup]
nixPkgs = ["ffmpeg", "python311"]

[phases.build]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "python api_server.py"
```

---

## Performance Considerations

### Resource Limits

**Maximum Concurrent Streams:** 12
- 3 primary cameras @ 512kbps = 1.5 Mbps
- 9 thumbnail cameras @ 256kbps = 2.3 Mbps
- Total bandwidth: ~4 Mbps

**CPU Usage per Stream:**
- FFmpeg: ~5% CPU core
- YOLO detection @ 5 FPS: ~10% CPU core
- Total per camera: ~15% CPU core
- 12 cameras: ~1.8 CPU cores minimum

**Memory Usage:**
- FFmpeg per stream: ~50 MB
- YOLO per thread: ~100 MB
- HLS segments: ~10 MB
- Total per camera: ~160 MB
- 12 cameras: ~2 GB RAM

**Recommendation:** Railway instance with 2+ CPU cores and 4+ GB RAM

### Optimization Strategies

1. **Sub-stream for thumbnails:** Use `subtype=1` (low resolution) for thumbnail views
2. **Lazy loading:** Only start HLS streams for visible cameras (IntersectionObserver)
3. **Adaptive FPS:** Reduce YOLO FPS to 2-3 for thumbnail cameras
4. **Segment cleanup:** `delete_segments` flag prevents disk accumulation

---

## Testing Strategy

### Unit Tests

- `RTSPBuilder.build_url()` - Verify URL generation for each manufacturer
- `StreamManager.start_stream()` - Mock FFmpeg subprocess
- `StreamManager.stop_stream()` - Verify cleanup
- `CameraService.create_camera()` - Database operations

### Integration Tests

- Test FFmpeg command generation
- Mock RTSP source with test video
- Verify HLS segment creation
- WebSocket message flow

### End-to-End Tests

- Camera registration flow
- Start stream → Verify HLS playable
- Stop stream → Verify cleanup
- Reconnection after crash

---

## Security Considerations

1. **Authentication:** All API endpoints require JWT token
2. **Authorization:** Users can only access their own cameras
3. **Credentials:** Camera passwords encrypted in database (consider AES-256)
4. **WebSocket:** JWT token required in connection handshake
5. **CORS:** Restrict to frontend domain only
6. **Rate Limiting:** Max 12 concurrent streams per user
7. **Input Validation:** Sanitize IP addresses, port ranges

---

## Migration Strategy

### Phase 1: Backend Foundation (Week 1)
- Implement `RTSPBuilder`
- Expand `CameraService` with new schema
- Create `cameras` table migration
- Implement camera CRUD endpoints
- Add connectivity testing endpoint

### Phase 2: Streaming Infrastructure (Week 2)
- Implement `StreamManager`
- Add FFmpeg subprocess management
- Implement HLS serving
- Add stream control endpoints
- Test with 1-3 cameras

### Phase 3: YOLO Integration (Week 3)
- Implement `YOLOProcessor`
- Add WebSocket support to Flask
- Connect detection results to WebSocket
- Test YOLO detection on live streams
- Optimize detection frequency

### Phase 4: Frontend Implementation (Week 4)
- Install `hls.js` dependency
- Implement `HLSCameraFeed` component
- Implement `CameraGrid` layout
- Add WebSocket integration
- Test with 12 simultaneous streams

### Phase 5: Polish & Optimization (Week 5)
- Error handling and reconnection
- Performance tuning
- Resource cleanup verification
- Security hardening
- Documentation

---

## Success Criteria

- ✅ Support 12 simultaneous camera streams
- ✅ HLS latency < 3 seconds
- ✅ YOLO detection at 5 FPS per camera
- ✅ Auto-reconnection within 30 seconds of failure
- ✅ 85%+ detection accuracy for products/EPIs
- ✅ Zero resource leaks (verified with 24h test)
- ✅ Browser compatibility: Chrome, Firefox, Safari, Edge

---

## Open Questions

1. **Database storage:** Should we store detection results in DB for historical analysis?
2. **Alerts:** Should we add alerting for specific events (e.g., person detected without helmet)?
3. **Recording:** Should we add optional video recording to disk/database?
4. **Multi-tenancy:** Should cameras be shareable between users?

---

## References

- **hls.js Documentation:** https://github.com/video-dev/hls.js
- **FFmpeg HLS Guide:** https://trac.ffmpeg.org/wiki/Streaming/HLS
- **Flask-SocketIO:** https://flask-socketio.readthedocs.io/
- **Intelbras RTSP:** Manufacturer documentation
- **Hikvision RTSP:** Manufacturer documentation
