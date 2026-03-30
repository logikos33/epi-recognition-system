-- EPI Recognition System - Railway PostgreSQL Database Schema
-- Complete Schema with Product Counting System
-- Version: 3.0 - Railway with Custom YOLO + DeepSORT
-- Execute in Railway PostgreSQL Query Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- EXISTING TABLES (from previous system)
-- ============================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company_name VARCHAR(255),
    phone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) DEFAULT 'user',
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- 2. CAMERAS TABLE
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    rtsp_url TEXT,
    brand VARCHAR(100),
    model VARCHAR(100),
    ip_address INET,
    port INTEGER,
    username VARCHAR(255),
    password VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cameras_user_id ON cameras(user_id);
CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);

-- 3. DETECTIONS TABLE (Generic YOLO detections)
CREATE TABLE IF NOT EXISTS detections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    image_url TEXT,
    objects_detected JSONB NOT NULL,
    total_objects INTEGER DEFAULT 0,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_detections_user_id ON detections(user_id);
CREATE INDEX IF NOT EXISTS idx_detections_camera_id ON detections(camera_id);
CREATE INDEX IF NOT EXISTS idx_detections_created_at ON detections(created_at DESC);

-- 4. ALERTS TABLE
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    detection_id UUID REFERENCES detections(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) DEFAULT 'warning',
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);

-- 5. SESSIONS TABLE (JWT authentication)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    refresh_token VARCHAR(500),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);

-- ============================================
-- NEW TABLES - PRODUCT COUNTING SYSTEM
-- ============================================

-- 6. PRODUCTS TABLE (Catalog of trainable product labels)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE,
    category VARCHAR(100),
    description TEXT,
    image_url TEXT,  -- Reference image for the product
    detection_threshold FLOAT DEFAULT 0.85,
    is_active BOOLEAN DEFAULT TRUE,
    volume_cm3 FLOAT,  -- Volume in cubic cm for logistics
    weight_g FLOAT,    -- Weight in grams
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);

-- 7. COUNTING SESSIONS TABLE (Vehicle loading sessions)
CREATE TABLE IF NOT EXISTS counting_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    vehicle_id VARCHAR(100),  -- Vehicle plate/license
    driver_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed, cancelled
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_products INTEGER DEFAULT 0,
    verified_products INTEGER DEFAULT 0,
    notes TEXT,
    counting_line_y INTEGER,  -- Y-coordinate of virtual counting line
    counting_direction VARCHAR(20) DEFAULT 'entering',  -- entering, exiting, both
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_counting_sessions_user_id ON counting_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_counting_sessions_camera_id ON counting_sessions(camera_id);
CREATE INDEX IF NOT EXISTS idx_counting_sessions_status ON counting_sessions(status);
CREATE INDEX IF NOT EXISTS idx_counting_sessions_started_at ON counting_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_counting_sessions_vehicle_id ON counting_sessions(vehicle_id);

-- 8. COUNTED PRODUCTS TABLE (Each individual product counted)
CREATE TABLE IF NOT EXISTS counted_products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES counting_sessions(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    track_id VARCHAR(100),  -- DeepSORT track ID
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confidence FLOAT NOT NULL,
    bbox_data JSONB,  -- Bounding box: {x1, y1, x2, y2, width, height}
    frame_image_url TEXT,  -- Captured frame image
    verified_by_human BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMP WITH TIME ZONE,
    correction_notes TEXT,
    is_false_positive BOOLEAN DEFAULT FALSE,
    frame_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_counted_products_session_id ON counted_products(session_id);
CREATE INDEX IF NOT EXISTS idx_counted_products_product_id ON counted_products(product_id);
CREATE INDEX IF NOT EXISTS idx_counted_products_track_id ON counted_products(track_id);
CREATE INDEX IF NOT EXISTS idx_counted_products_detected_at ON counted_products(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_counted_products_verified_by_human ON counted_products(verified_by_human);
CREATE INDEX IF NOT EXISTS idx_counted_products_session_product ON counted_products(session_id, product_id);

-- 9. TRAINING IMAGES TABLE (Images for training custom YOLO model)
CREATE TABLE IF NOT EXISTS training_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,  -- NULL if multi-class image
    image_url TEXT NOT NULL,
    image_path VARCHAR(500),  -- Storage path
    width INTEGER,
    height INTEGER,
    annotation_data JSONB,  -- YOLO format annotations: [{class_id, x_center, y_center, width, height}]
    is_annotated BOOLEAN DEFAULT FALSE,
    used_in_training BOOLEAN DEFAULT FALSE,
    training_version VARCHAR(50),  -- Links to model version
    augmentation_applied BOOLEAN DEFAULT FALSE,
    quality_score FLOAT,  -- Image quality for training priority
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_images_user_id ON training_images(user_id);
CREATE INDEX IF NOT EXISTS idx_training_images_product_id ON training_images(product_id);
CREATE INDEX IF NOT EXISTS idx_training_images_is_annotated ON training_images(is_annotated);
CREATE INDEX IF NOT EXISTS idx_training_images_used_in_training ON training_images(used_in_training);
CREATE INDEX IF NOT EXISTS idx_training_images_training_version ON training_images(training_version);

-- 10. MODEL VERSIONS TABLE (Track trained model versions)
CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(50) UNIQUE NOT NULL,
    classes JSONB NOT NULL,  -- [{id: 0, name: "Coca-Cola Lata"}, ...]
    map_score FLOAT,  -- Mean Average Precision
    map_50 FLOAT,     -- mAP@0.5
    map_75 FLOAT,     -- mAP@0.75
    precision FLOAT,
    recall FLOAT,
    training_images_count INTEGER DEFAULT 0,
    training_epochs INTEGER,
    is_active BOOLEAN DEFAULT FALSE,
    model_path TEXT,  -- Storage path to model file
    config_data JSONB,  -- Training config: hyperparameters, augmentation settings
    base_model VARCHAR(100),  -- yolov8n.pt, yolov8s.pt, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_model_versions_version ON model_versions(version);
CREATE INDEX IF NOT EXISTS idx_model_versions_is_active ON model_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_model_versions_created_at ON model_versions(created_at DESC);

-- 11. TRAINING JOBS TABLE (Track training processes)
CREATE TABLE IF NOT EXISTS training_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_version_id UUID REFERENCES model_versions(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_epochs INTEGER,
    current_epoch INTEGER DEFAULT 0,
    progress FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    error_message TEXT,
    metrics JSONB,  -- Real-time metrics: {epoch, train_loss, val_loss, map, etc.}
    config_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_jobs_user_id ON training_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status);
CREATE INDEX IF NOT EXISTS idx_training_jobs_started_at ON training_jobs(started_at DESC);

-- 12. VERIFICATION QUEUE TABLE (Queue for human verification)
-- This is essentially a view/query over counted_products, but we can create
-- a materialized view or just query counted_products directly
-- For simplicity, we'll query counted_products with:
-- WHERE verified_by_human = FALSE AND confidence < 0.90

-- ============================================
-- STORAGE METADATA (Railway Volumes or S3)
-- ============================================

-- 13. STORAGE FILES TABLE (Track stored files)
CREATE TABLE IF NOT EXISTS storage_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename VARCHAR(500) NOT NULL,
    storage_path TEXT NOT NULL,  -- Path in Railway volume or S3
    file_type VARCHAR(50),  -- training_image, frame_capture, model_file, etc.
    mime_type VARCHAR(100),
    file_size_bytes BIGINT,
    entity_type VARCHAR(100),  -- training_image, counted_product, etc.
    entity_id UUID,  -- Reference to the entity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_storage_files_user_id ON storage_files(user_id);
CREATE INDEX IF NOT EXISTS idx_storage_files_entity ON storage_files(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_storage_files_file_type ON storage_files(file_type);

-- ============================================
-- FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cameras_updated_at ON cameras;
CREATE TRIGGER update_cameras_updated_at BEFORE UPDATE ON cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_training_images_updated_at ON training_images;
CREATE TRIGGER update_training_images_updated_at BEFORE UPDATE ON training_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to update counting_sessions total_products and verified_products
CREATE OR REPLACE FUNCTION update_session_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        UPDATE counting_sessions
        SET total_products = (
            SELECT COUNT(*)
            FROM counted_products
            WHERE session_id = NEW.session_id
            AND is_false_positive = FALSE
        ),
        verified_products = (
            SELECT COUNT(*)
            FROM counted_products
            WHERE session_id = NEW.session_id
            AND verified_by_human = TRUE
            AND is_false_positive = FALSE
        )
        WHERE id = NEW.session_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE counting_sessions
        SET total_products = (
            SELECT COUNT(*)
            FROM counted_products
            WHERE session_id = OLD.session_id
            AND is_false_positive = FALSE
        ),
        verified_products = (
            SELECT COUNT(*)
            FROM counted_products
            WHERE session_id = OLD.session_id
            AND verified_by_human = TRUE
            AND is_false_positive = FALSE
        )
        WHERE id = OLD.session_id;
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_counting_session_counts ON counted_products;
CREATE TRIGGER update_counting_session_counts
    AFTER INSERT OR UPDATE OR DELETE ON counted_products
    FOR EACH ROW EXECUTE FUNCTION update_session_counts();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- View: Active products ready for detection
CREATE OR REPLACE VIEW active_products AS
SELECT
    p.id,
    p.name,
    p.sku,
    p.category,
    p.image_url,
    p.detection_threshold,
    p.volume_cm3,
    p.weight_g,
    COUNT(DISTINCT ti.id) as training_images_count,
    COUNT(DISTINCT CASE WHEN ti.is_annotated = TRUE THEN ti.id END) as annotated_images_count
FROM products p
LEFT JOIN training_images ti ON ti.product_id = p.id
WHERE p.is_active = TRUE
GROUP BY p.id
ORDER BY p.name;

-- View: Verification queue (needs human verification)
CREATE OR REPLACE VIEW verification_queue AS
SELECT
    cp.id,
    cp.session_id,
    cs.vehicle_id,
    cp.product_id,
    p.name as product_name,
    p.sku,
    cp.track_id,
    cp.detected_at,
    cp.confidence,
    cp.bbox_data,
    cp.frame_image_url,
    cp.frame_number,
    u.full_name as session_user
FROM counted_products cp
JOIN counting_sessions cs ON cs.id = cp.session_id
JOIN products p ON p.id = cp.product_id
JOIN users u ON u.id = cs.user_id
WHERE cp.verified_by_human = FALSE
  AND cp.is_false_positive = FALSE
  AND cs.status != 'cancelled'
ORDER BY cp.confidence ASC, cp.detected_at DESC;

-- View: Session statistics
CREATE OR REPLACE VIEW session_statistics AS
SELECT
    cs.id,
    cs.user_id,
    u.full_name as user_name,
    cs.camera_id,
    c.name as camera_name,
    cs.vehicle_id,
    cs.driver_name,
    cs.status,
    cs.started_at,
    cs.completed_at,
    cs.total_products,
    cs.verified_products,
    COUNT(DISTINCT cp.product_id) as distinct_products_count,
    JSONB_AGG(
        JSONB_BUILD_OBJECT(
            'product_id', cp.product_id,
            'product_name', p.name,
            'count', COUNT(*)
        )
    ) as products_breakdown
FROM counting_sessions cs
LEFT JOIN users u ON u.id = cs.user_id
LEFT JOIN cameras c ON c.id = cs.camera_id
LEFT JOIN counted_products cp ON cp.session_id = cs.id AND cp.is_false_positive = FALSE
LEFT JOIN products p ON p.id = cp.product_id
GROUP BY cs.id, u.full_name, c.name
ORDER BY cs.started_at DESC;

-- View: Training progress by product
CREATE OR REPLACE VIEW product_training_status AS
SELECT
    p.id,
    p.name,
    p.sku,
    p.category,
    p.is_active,
    COUNT(DISTINCT ti.id) as total_images,
    COUNT(DISTINCT CASE WHEN ti.is_annotated = TRUE THEN ti.id END) as annotated_images,
    COUNT(DISTINCT CASE WHEN ti.used_in_training = TRUE THEN ti.id END) as used_in_training,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN ti.is_annotated = TRUE THEN ti.id END) / NULLIF(COUNT(DISTINCT ti.id), 0), 2) as annotation_progress_pct,
    MAX(mv.map_score) as best_map_score,
    MAX(mv.created_at) as last_trained_at
FROM products p
LEFT JOIN training_images ti ON ti.product_id = p.id
LEFT JOIN model_versions mv ON mv.created_at >= NOW() - INTERVAL '30 days'
GROUP BY p.id
ORDER BY p.name;

-- ============================================
-- INITIAL DATA - Default Model Version
-- ============================================

-- Insert default YOLOv8 COCO model as version 1.0.0
INSERT INTO model_versions (
    version,
    classes,
    map_score,
    is_active,
    base_model,
    model_path,
    config_data,
    created_at,
    deployed_at
) VALUES (
    '1.0.0-coco',
    '[
        {"id": 0, "name": "person"},
        {"id": 1, "name": "bicycle"},
        {"id": 2, "name": "car"},
        {"id": 3, "name": "motorcycle"},
        {"id": 4, "name": "airplane"},
        {"id": 5, "name": "bus"},
        {"id": 6, "name": "train"},
        {"id": 7, "name": "truck"},
        {"id": 8, "name": "boat"},
        {"id": 9, "name": "traffic light"},
        {"id": 10, "name": "fire hydrant"},
        {"id": 11, "name": "stop sign"},
        {"id": 12, "name": "parking meter"},
        {"id": 13, "name": "bench"},
        {"id": 14, "name": "bird"},
        {"id": 15, "name": "cat"},
        {"id": 16, "name": "dog"},
        {"id": 17, "name": "horse"},
        {"id": 18, "name": "sheep"},
        {"id": 19, "name": "cow"},
        {"id": 20, "name": "elephant"},
        {"id": 21, "name": "bear"},
        {"id": 22, "name": "zebra"},
        {"id": 23, "name": "giraffe"},
        {"id": 24, "name": "backpack"},
        {"id": 25, "name": "umbrella"},
        {"id": 26, "name": "handbag"},
        {"id": 27, "name": "tie"},
        {"id": 28, "name": "suitcase"},
        {"id": 29, "name": "frisbee"},
        {"id": 30, "name": "skis"},
        {"id": 31, "name": "snowboard"},
        {"id": 32, "name": "sports ball"},
        {"id": 33, "name": "kite"},
        {"id": 34, "name": "baseball bat"},
        {"id": 35, "name": "baseball glove"},
        {"id": 36, "name": "skateboard"},
        {"id": 37, "name": "surfboard"},
        {"id": 38, "name": "tennis racket"},
        {"id": 39, "name": "bottle"},
        {"id": 40, "name": "wine glass"},
        {"id": 41, "name": "cup"},
        {"id": 42, "name": "fork"},
        {"id": 43, "name": "knife"},
        {"id": 44, "name": "spoon"},
        {"id": 45, "name": "bowl"},
        {"id": 46, "name": "banana"},
        {"id": 47, "name": "apple"},
        {"id": 48, "name": "sandwich"},
        {"id": 49, "name": "orange"},
        {"id": 50, "name": "broccoli"},
        {"id": 51, "name": "carrot"},
        {"id": 52, "name": "hot dog"},
        {"id": 53, "name": "pizza"},
        {"id": 54, "name": "donut"},
        {"id": 55, "name": "cake"},
        {"id": 56, "name": "chair"},
        {"id": 57, "name": "couch"},
        {"id": 58, "name": "potted plant"},
        {"id": 59, "name": "bed"},
        {"id": 60, "name": "dining table"},
        {"id": 61, "name": "toilet"},
        {"id": 62, "name": "tv"},
        {"id": 63, "name": "laptop"},
        {"id": 64, "name": "mouse"},
        {"id": 65, "name": "remote"},
        {"id": 66, "name": "keyboard"},
        {"id": 67, "name": "cell phone"},
        {"id": 68, "name": "microwave"},
        {"id": 69, "name": "oven"},
        {"id": 70, "name": "toaster"},
        {"id": 71, "name": "sink"},
        {"id": 72, "name": "refrigerator"},
        {"id": 73, "name": "book"},
        {"id": 74, "name": "clock"},
        {"id": 75, "name": "vase"},
        {"id": 76, "name": "scissors"},
        {"id": 77, "name": "teddy bear"},
        {"id": 78, "name": "hair drier"},
        {"id": 79, "name": "toothbrush"}
    ]'::jsonb,
    0.50,
    TRUE,
    'yolov8n.pt',
    'models/yolov8n.pt',
    '{
        "input_size": 640,
        "confidence_threshold": 0.25,
        "iou_threshold": 0.45,
        "max_detections": 300
    }'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (version) DO NOTHING;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '✅ Railway PostgreSQL Schema Created Successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '📊 Existing Tables:';
    RAISE NOTICE '   - users';
    RAISE NOTICE '   - cameras';
    RAISE NOTICE '   - detections';
    RAISE NOTICE '   - alerts';
    RAISE NOTICE '   - sessions';
    RAISE NOTICE '';
    RAISE NOTICE '🆕 New Tables (Product Counting):';
    RAISE NOTICE '   - products (catalog of trainable products)';
    RAISE NOTICE '   - counting_sessions (vehicle loading sessions)';
    RAISE NOTICE '   - counted_products (individual counted items)';
    RAISE NOTICE '   - training_images (images for YOLO training)';
    RAISE NOTICE '   - model_versions (trained model tracking)';
    RAISE NOTICE '   - training_jobs (training process tracking)';
    RAISE NOTICE '   - storage_files (Railway volume/S3 metadata)';
    RAISE NOTICE '';
    RAISE NOTICE '🔍 Views Created:';
    RAISE NOTICE '   - active_products';
    RAISE NOTICE '   - verification_queue';
    RAISE NOTICE '   - session_statistics';
    RAISE NOTICE '   - product_training_status';
    RAISE NOTICE '';
    RAISE NOTICE '⚙️  Features:';
    RAISE NOTICE '   - Custom YOLO model support';
    RAISE NOTICE '   - DeepSORT tracking ready';
    RAISE NOTICE '   - Product counting without duplication';
    RAISE NOTICE '   - Human verification workflow';
    RAISE NOTICE '   - Training pipeline';
    RAISE NOTICE '   - CSV export ready';
    RAISE NOTICE '   - Railway deployment ready';
    RAISE NOTICE '========================================';
END $$;
