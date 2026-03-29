-- migrations/2026-03-29-fueling-monitoring.sql

-- Bays (Áreas de abastecimento)
CREATE TABLE IF NOT EXISTS bays (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(200),
    scale_integration BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add unique constraint for bays name
DO $$ BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS idx_bays_name ON bays(name);
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- Cameras (Câmeras do sistema)
-- ON DELETE CASCADE: When a bay is deleted, all associated cameras are automatically deleted
CREATE TABLE IF NOT EXISTS cameras (
    id SERIAL PRIMARY KEY,
    bay_id INTEGER REFERENCES bays(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    rtsp_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    position_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add unique constraint for cameras (bay_id + name)
DO $$ BEGIN
    CREATE UNIQUE INDEX IF NOT EXISTS idx_cameras_bay_name ON cameras(bay_id, name);
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- Fueling Sessions (Sessões de abastecimento)
-- ON DELETE CASCADE: When a session is deleted, all counted products are automatically deleted
CREATE TABLE IF NOT EXISTS fueling_sessions (
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
-- ON DELETE CASCADE: When a session is deleted, all counted products are automatically deleted
CREATE TABLE IF NOT EXISTS counted_products (
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
-- No CASCADE: User layouts should persist even if user is deleted (soft delete pattern)
CREATE TABLE IF NOT EXISTS user_camera_layouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    layout_name VARCHAR(100),
    selected_cameras INTEGER[],
    camera_configs JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_bay ON fueling_sessions(bay_id);
CREATE INDEX IF NOT EXISTS idx_sessions_plate ON fueling_sessions(license_plate);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON fueling_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_entry ON fueling_sessions(truck_entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_products_session ON counted_products(session_id);
CREATE INDEX IF NOT EXISTS idx_products_timestamp ON counted_products(timestamp);

-- Insert sample data (idempotent - won't duplicate if already exists)
DO $$
DECLARE
    bay1_id INTEGER;
    bay2_id INTEGER;
    bay3_id INTEGER;
BEGIN
    -- Insert bays and get their IDs
    INSERT INTO bays (name, location, scale_integration)
    VALUES ('Baia 1', 'Rua A, Setor 1', TRUE)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO bay1_id;

    INSERT INTO bays (name, location, scale_integration)
    VALUES ('Baia 2', 'Rua A, Setor 2', TRUE)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO bay2_id;

    INSERT INTO bays (name, location, scale_integration)
    VALUES ('Baia 3', 'Rua B, Setor 1', FALSE)
    ON CONFLICT (name) DO NOTHING
    RETURNING id INTO bay3_id;

    -- Only insert cameras if bays exist
    IF bay1_id IS NOT NULL THEN
        INSERT INTO cameras (bay_id, name, rtsp_url, is_active, position_order)
        VALUES
            (bay1_id, 'Câmera Baia 1 - Principal', 'rtsp://camera1.local/stream', TRUE, 1),
            (bay1_id, 'Câmera Baia 1 - Secundária', 'rtsp://camera2.local/stream', TRUE, 2)
        ON CONFLICT (bay_id, name) DO NOTHING;
    END IF;

    IF bay2_id IS NOT NULL THEN
        INSERT INTO cameras (bay_id, name, rtsp_url, is_active, position_order)
        VALUES
            (bay2_id, 'Câmera Baia 2 - Principal', 'rtsp://camera3.local/stream', TRUE, 3),
            (bay2_id, 'Câmera Baia 2 - Lateral', 'rtsp://camera4.local/stream', TRUE, 4)
        ON CONFLICT (bay_id, name) DO NOTHING;
    END IF;

    IF bay3_id IS NOT NULL THEN
        INSERT INTO cameras (bay_id, name, rtsp_url, is_active, position_order)
        VALUES
            (bay3_id, 'Câmera Baia 3 - Principal', 'rtsp://camera5.local/stream', TRUE, 5)
        ON CONFLICT (bay_id, name) DO NOTHING;
    END IF;
END
$$;