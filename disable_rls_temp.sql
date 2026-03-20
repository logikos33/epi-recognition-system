-- Temporarily disable RLS for seeding
-- Run this in Supabase SQL Editor

ALTER TABLE cameras DISABLE ROW LEVEL SECURITY;
ALTER TABLE detections DISABLE ROW LEVEL SECURITY;
ALTER TABLE worker_status DISABLE ROW LEVEL SECURITY;
