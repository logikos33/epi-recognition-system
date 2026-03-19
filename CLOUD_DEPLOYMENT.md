# Deploy 100% Cloud - EPI Recognition System

## Overview

This guide walks you through deploying the EPI Recognition System entirely in the cloud using:
- **Streamlit Cloud** (Dashboard UI - Free)
- **Render** (Worker - Free)
- **Supabase** (Database - Free)

## Architecture

```
User (Desktop/Mobile)
    ↓ HTTPS
Streamlit Cloud (Dashboard UI)
    ↓ Poll (2s)
Supabase (Database)
    ↓ Read/Write
Render Worker (YOLO Processing)
    ↓ RTSP
IP Cameras (Public IP)
```

## Prerequisites

1. **IP Cameras** with public IP addresses
2. **GitHub account** (for deployment)
3. **Supabase account** (free tier)
4. **Render account** (free tier)
5. **Streamlit account** (free tier)

## Step 1: Setup Supabase Database (~15 minutes)

### 1.1 Create Supabase Project

1. Go to https://supabase.com
2. Click "Start your project"
3. Sign in/up with GitHub
4. Click "New Project"
5. Fill in:
   - Name: `EPI Monitoring`
   - Database Password: (generate and save securely)
   - Region: Choose closest to your cameras

### 1.2 Run SQL Schema

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the contents of `supabase_schema.sql` in this repo
4. Paste and click **Run** (or press Cmd+Enter)

### 1.3 Get Credentials

1. Go to **Project Settings** → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public**: `eyJhbGc...`
   - **service_role** (secret!): `eyJhbGc...`

## Step 2: Add Cameras to Supabase (~10 minutes)

### Option A: Using SQL Editor

```sql
INSERT INTO cameras (name, location, ip_address, rtsp_username, rtsp_password, rtsp_port, camera_brand, is_active)
VALUES
    ('Câmera Entrada', 'Fábrica - Linha A', '189.0.0.100', 'admin', 'password123', 554, 'hikvision', true);
```

### Option B: Using Dashboard (Recommended)

1. Deploy the dashboard first (Steps 4-5)
2. Access the dashboard
3. Go to "Gerenciar Câmeras"
4. Add cameras using the web interface

## Step 3: Prepare GitHub Repository (~5 minutes)

1. Push your code to GitHub (or fork this repo)
2. Make sure these files exist:
   - `cloud_worker.py`
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - `.env.example`

## Step 4: Deploy Worker to Render (~10 minutes)

### 4.1 Create Render Account

1. Go to https://render.com
2. Sign up with GitHub

### 4.2 Deploy Worker

1. Click **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `epi-recognition-worker`
   - **Region**: Oregon (or closest to your cameras)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python cloud_worker.py`

4. Add Environment Variables (click **Advanced** → **Add Environment Variable**):

   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key
   WORKER_ID=worker-1
   CAMERA_RANGE_START=0
   CAMERA_RANGE_END=999
   FRAME_RATE=5
   FRAMES_PER_BATCH=10
   ```

5. Click **Create Web Service**

6. Wait for deployment (~3-5 minutes)
7. Check logs: Click on your service → **Logs**

## Step 5: Deploy Dashboard to Streamlit Cloud (~10 minutes)

### 5.1 Create Streamlit Account

1. Go to https://streamlit.io/cloud
2. Click **Sign up**
3. Sign in with GitHub/Email

### 5.2 Deploy Dashboard

1. Click **New app**
2. Connect your GitHub repository
3. Configure:
   - **Main file path**: `app.py`
   - **Repository**: Your repo
   - **Branch**: `main`

4. Add Secrets (click **Advanced Settings** → **Secrets**):

   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   ```

5. Click **Deploy**

6. Access your dashboard at: `https://your-app-name.streamlit.app`

## Step 6: Verify Deployment (~5 minutes)

### Check Worker Status

1. Go to Render dashboard
2. Click on your worker service
3. Check **Logs** tab - you should see:
   ```
   CloudWorker worker-1 initialized (cameras 0-999)
   Main loop started
   Processing N camera(s)
   ```

### Check Dashboard

1. Go to your Streamlit app
2. You should see:
   - System status: ✅ Sistema Operacional
   - Cameras count: matching your database
   - Recent detections updating

### Check Supabase

1. Go to Supabase **Table Editor**
2. Check **worker_status** table:
   - status: "active"
   - last_heartbeat: recent timestamp
3. Check **detections** table:
   - New rows appearing every few seconds

## Step 7: Add Your Cameras (~15 minutes)

### Using the Dashboard

1. Access your Streamlit app
2. Click **Gerenciar Câmeras** in the sidebar (or navigate to cameras page)
3. Click **➕ Adicionar Câmera**
4. Fill in:
   - **Nome**: Ex: "Câmera Entrada Principal"
   - **Localização**: Ex: "Fábrica - Linha A"
   - **Marca da Câmera**: Select brand (Hikvision, Dahua, Intelbras, etc.)
   - **Endereço IP**: Public IP of your camera
   - **Porta RTSP**: Default 554
   - **Usuário RTSP**: Camera username
   - **Senha RTSP**: Camera password

5. Click **Adicionar Câmera**

6. The worker will automatically pick up the new camera within 10 seconds

### RTSP URL Templates

The system automatically builds RTSP URLs based on camera brand:

| Brand | Main Stream URL |
|-------|-----------------|
| Hikvision | `rtsp://user:pass@IP:554/Streaming/Channels/101` |
| Dahua | `rtsp://user:pass@IP:554/cam/realmonitor?channel=1&subtype=0` |
| Intelbras | `rtsp://user:pass@IP:554/video1` |
| Axis | `rtsp://user:pass@IP:554/axis-media/media.amp` |
| Vivotek | `rtsp://user:pass@IP:554/live.sdp` |
| Generic | `rtsp://user:pass@IP:554/stream` |

## Troubleshooting

### Worker not connecting to cameras

**Symptoms:**
- Logs show: "Failed to open RTSP stream"
- No detections in database

**Solutions:**

1. **Test RTSP locally**:
   ```bash
   ffplay rtsp://username:password@PUBLIC_IP:554/stream
   ```

2. **Check IP is public**:
   - Go to https://whatismyipaddress.com
   - Compare with your camera IP
   - Private IPs (192.168.x.x, 10.x.x.x) won't work

3. **Check firewall**:
   - Port 554 must be open on camera
   - Check camera's web interface → Network → Port

4. **Verify credentials**:
   - Test with camera vendor software (Hik-Connect, etc.)
   - Same credentials should work

### Dashboard not updating

**Symptoms:**
- Detections not showing
- Old data displayed

**Solutions:**

1. **Check Supabase connection**:
   - Verify `SUPABASE_URL` and `SUPABASE_KEY` in Streamlit secrets
   - Check browser console for errors

2. **Check worker is running**:
   - Go to Render dashboard
   - Worker status should be "active"
   - CPU/Memory usage should be non-zero

3. **Enable auto-refresh**:
   - Check "🔄 Auto-refresh (5s)" in sidebar

### Worker crashes (OOM)

**Symptoms:**
- Render shows "Crashed"
- Logs show "Out of memory"

**Solutions:**

1. **Reduce frame rate**:
   ```
   FRAME_RATE=2  # Default is 5
   ```

2. **Reduce batch size**:
   ```
   FRAMES_PER_BATCH=5  # Default is 10
   ```

3. **Use multiple workers**:
   - Create a 2nd worker on Render
   - Set different camera ranges:
     - Worker 1: `CAMERA_RANGE_START=0`, `CAMERA_RANGE_END=49`
     - Worker 2: `CAMERA_RANGE_START=50`, `CAMERA_RANGE_END=99`

### Camera authentication fails

**Symptoms:**
- Logs show authentication error
- Vendor software works but worker doesn't

**Solutions:**

1. **URL encode credentials**:
   - If password has special chars, the auto-encoding should handle it
   - Check the generated RTSP URL in logs

2. **Try different stream**:
   - Change from main to sub stream in camera settings
   - Or use different channel (101 → 102)

## Scaling

### 1-10 Cameras
- 1 Worker (Render Free)
- Cost: $0/month

### 11-30 Cameras
- 2 Workers (Render + Railway Free)
- Cost: $0/month

### 31-50 Cameras
- 3 Workers (Render + Railway + Fly.io)
- Cost: $0/month

### 50+ Cameras
- 4+ Workers or upgrade to paid tier
- Cost: $0-7/month

## Security Best Practices

1. **Never commit secrets** to git
2. **Use strong passwords** for cameras
3. **Enable Row Level Security** in Supabase (already in schema)
4. **Use VPN** if cameras don't have public IP
5. **Monitor worker logs** for suspicious activity
6. **Rotate credentials** periodically

## Cost Summary

| Service | Tier | Cost |
|---------|------|------|
| Streamlit Cloud | Free | $0 |
| Render | Free | $0 |
| Supabase | Free | $0 |
| **Total** | | **$0/month** |

## Next Steps

1. ✅ Deploy to production
2. ✅ Add your cameras
3. ✅ Monitor for 24 hours
4. ✅ Adjust settings based on performance
5. ✅ Set up alerts (email/Slack)
6. ✅ Configure data retention policy

## Support

- **Streamlit Docs**: https://docs.streamlit.io
- **Render Docs**: https://render.com/docs
- **Supabase Docs**: https://supabase.com/docs
- **GitHub Issues**: Report bugs in this repo

---

**Generated by EPI Recognition System v1.0.0**
