-- migrations/002_create_cameras_table.sql

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_cameras (
  id                  SERIAL PRIMARY KEY,
  user_id             UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name                VARCHAR(100) NOT NULL,
  manufacturer        VARCHAR(50)  NOT NULL,
  type                VARCHAR(20)  NOT NULL DEFAULT 'ip',
  ip                  VARCHAR(50)  NOT NULL,
  port                INTEGER      NOT NULL DEFAULT 554,
  username            VARCHAR(100),
  password            VARCHAR(100),
  channel             INTEGER      NOT NULL DEFAULT 1,
  subtype             INTEGER      NOT NULL DEFAULT 1,
  rtsp_url            VARCHAR(500),
  is_active           BOOLEAN      DEFAULT true,
  last_connected_at   TIMESTAMP,
  connection_error    TEXT,
  created_at          TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ip_cameras_user_id ON ip_cameras(user_id);
CREATE INDEX IF NOT EXISTS idx_ip_cameras_is_active ON ip_cameras(is_active);

COMMENT ON COLUMN ip_cameras.manufacturer IS 'Camera manufacturer: intelbras, hikvision, generic';
COMMENT ON COLUMN ip_cameras.type IS 'Camera type: ip, dvr, nvr';
COMMENT ON COLUMN ip_cameras.subtype IS 'Stream type: 0=main stream, 1=sub-stream (low latency)';
COMMENT ON COLUMN ip_cameras.password IS 'WARNING: Stored in plain text for RTSP authentication. Consider encryption for production.';