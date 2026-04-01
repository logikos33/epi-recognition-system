-- Migration 007: Camera Management System
-- Tabelas para sistema completo de gerenciamento de câmeras IP, DVRs e eventos

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabela de DVRs/NVRs (dispositivos com múltiplos canais)
CREATE TABLE IF NOT EXISTS dvrs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 80,
    rtsp_port INTEGER NOT NULL DEFAULT 554,
    username VARCHAR(255),
    password_encrypted TEXT,
    manufacturer VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    total_channels INTEGER,
    status VARCHAR(20) DEFAULT 'offline',
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de câmeras individuais
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    protocol VARCHAR(20) NOT NULL DEFAULT 'rtsp',
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 554,
    username VARCHAR(255),
    password_encrypted TEXT,
    channel INTEGER DEFAULT 1,
    subtype INTEGER DEFAULT 0,
    rtsp_url_template TEXT,
    manufacturer VARCHAR(50) DEFAULT 'generic',
    model VARCHAR(100),
    location VARCHAR(255),
    bay_id UUID,
    description TEXT,
    status VARCHAR(20) DEFAULT 'offline',
    last_seen_at TIMESTAMP,
    last_error TEXT,
    consecutive_failures INTEGER DEFAULT 0,
    resolution VARCHAR(20) DEFAULT '1280x720',
    fps INTEGER DEFAULT 15,
    stream_pid INTEGER,
    hls_path TEXT,
    dvr_id UUID REFERENCES dvrs(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabela de eventos de câmera (para diagnóstico)
CREATE TABLE IF NOT EXISTS camera_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    occurred_at TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);
CREATE INDEX IF NOT EXISTS idx_cameras_dvr ON cameras(dvr_id);
CREATE INDEX IF NOT EXISTS idx_cameras_active ON cameras(is_active);
CREATE INDEX IF NOT EXISTS idx_camera_events_camera ON camera_events(camera_id);
CREATE INDEX IF NOT EXISTS idx_camera_events_time ON camera_events(occurred_at DESC);
