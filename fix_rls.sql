-- Temporarily allow anon key to insert data for seeding
-- Run this in Supabase SQL Editor

-- Drop existing policies and recreate with anon access for seeding
DROP POLICY IF EXISTS "Allow insert to authenticated users on cameras" ON cameras;
DROP POLICY IF EXISTS "Allow insert to service role on detections" ON detections;

-- Create new policies that allow anon access for seeding
CREATE POLICY "Allow insert to anon and authenticated users on cameras"
    ON cameras FOR INSERT
    WITH CHECK (auth.role() IN ('anon', 'authenticated', 'service_role'));

CREATE POLICY "Allow insert to anon and authenticated users on detections"
    ON detections FOR INSERT
    WITH CHECK (auth.role() IN ('anon', 'authenticated', 'service_role'));

-- Allow delete for seeding
CREATE POLICY "Allow delete to anon and authenticated users on cameras"
    ON cameras FOR DELETE
    USING (auth.role() IN ('anon', 'authenticated', 'service_role'));

CREATE POLICY "Allow delete to anon and authenticated users on detections"
    ON detections FOR DELETE
    USING (auth.role() IN ('anon', 'authenticated', 'service_role'));
