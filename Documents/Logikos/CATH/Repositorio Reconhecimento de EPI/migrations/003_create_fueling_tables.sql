-- ============================================
-- Create Fueling Monitoring Tables
-- ============================================
-- Tables for fueling session monitoring and product counting

CREATE TABLE IF NOT EXISTS fueling_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bay_id INTEGER NOT NULL,
  camera_id INTEGER NOT NULL,
  license_plate VARCHAR(20) NOT NULL,
  truck_entry_time TIMESTAMP NOT NULL,
  truck_exit_time TIMESTAMP,
  duration_seconds INTEGER,
  final_weight NUMERIC(10, 2),
  status VARCHAR(20) DEFAULT 'active',
  products_counted JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS counted_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES fueling_sessions(id) ON DELETE CASCADE,
  product_type VARCHAR(100) NOT NULL,
  quantity INTEGER NOT NULL,
  confidence NUMERIC(3, 2),
  confirmed_by_user BOOLEAN DEFAULT FALSE,
  is_ai_suggestion BOOLEAN DEFAULT FALSE,
  corrected_to_type VARCHAR(100),
  timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_fueling_sessions_bay ON fueling_sessions(bay_id);
CREATE INDEX idx_fueling_sessions_status ON fueling_sessions(status);
CREATE INDEX idx_counted_products_session ON counted_products(session_id);
CREATE INDEX idx_counted_products_timestamp ON counted_products(timestamp);

-- Comments for documentation
COMMENT ON TABLE fueling_sessions IS 'Fueling session monitoring for truck loading/unloading';
COMMENT ON TABLE counted_products IS 'Products counted during fueling sessions (AI or manual)';
