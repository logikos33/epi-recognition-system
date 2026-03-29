-- migrations/2026-03-29-fueling-monitoring.sql

-- Drop tables if they exist (for clean migration)
DROP TABLE IF EXISTS counted_products CASCADE;
DROP TABLE IF EXISTS fueling_sessions CASCADE;
DROP TABLE IF EXISTS cameras CASCADE;
DROP TABLE IF EXISTS bays CASCADE;
DROP TABLE IF EXISTS user_camera_layouts CASCADE;

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
    rtsp_url VARCHAR(500),
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
    products_counted JSONB,
    final_weight FLOAT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Counted Products (Produtos contados)
CREATE TABLE counted_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES fueling_sessions(id) ON DELETE CASCADE,
    product_type VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL,
    confidence FLOAT,
    confirmed_by_user BOOLEAN DEFAULT FALSE,
    is_ai_suggestion BOOLEAN DEFAULT TRUE,
    corrected_to_type VARCHAR(100),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- User Layouts (Layouts salvos por usuário)
CREATE TABLE user_camera_layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    layout_name VARCHAR(100),
    selected_cameras INTEGER[],
    camera_configs JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_sessions_bay ON fueling_sessions(bay_id);
CREATE INDEX idx_sessions_plate ON fueling_sessions(license_plate);
CREATE INDEX idx_sessions_status ON fueling_sessions(status);
CREATE INDEX idx_sessions_entry ON fueling_sessions(truck_entry_time DESC);
CREATE INDEX idx_products_session ON counted_products(session_id);
CREATE INDEX idx_products_timestamp ON counted_products(timestamp);

-- Insert sample data
INSERT INTO bays (name, location, scale_integration) VALUES
    ('Baia 1', 'Rua A, Setor 1', TRUE),
    ('Baia 2', 'Rua A, Setor 2', TRUE),
    ('Baia 3', 'Rua B, Setor 1', FALSE);

INSERT INTO cameras (bay_id, name, rtsp_url, is_active, position_order) VALUES
    (1, 'Câmera Baia 1 - Principal', 'rtsp://camera1.local/stream', TRUE, 1),
    (1, 'Câmera Baia 1 - Secundária', 'rtsp://camera2.local/stream', TRUE, 2),
    (2, 'Câmera Baia 2 - Principal', 'rtsp://camera3.local/stream', TRUE, 3),
    (2, 'Câmera Baia 2 - Lateral', 'rtsp://camera4.local/stream', TRUE, 4),
    (3, 'Câmera Baia 3 - Principal', 'rtsp://camera5.local/stream', TRUE, 5);