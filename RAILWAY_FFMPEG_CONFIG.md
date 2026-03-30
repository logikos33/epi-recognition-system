# Railway FFmpeg Configuration Guide

## Overview

The EPI Recognition System uses FFmpeg for RTSP to HLS transcoding. This guide covers the complete configuration for Railway deployment.

## Environment Variables

Add these environment variables in your Railway project:

### FFmpeg Configuration
```bash
# FFmpeg Log Level (optional, default: warning)
FFMPEG_LOG_LEVEL=warning

# FFmpeg Preset for transcoding (optional, default: ultrafast)
FFMPEG_PRESET=ultrafast

# FFmpeg Video Bitrate (optional, default: 512k)
FFMPEG_VIDEO_BITRATE=512k

# FFmpeg Output Resolution (optional, default: 640x360)
FFMPEG_RESOLUTION=640x360

# HLS Segment Duration (optional, default: 1 second)
HLS_SEGMENT_DURATION=1

# HLS Playlist Size (optional, default: 3 segments)
HLS_PLAYLIST_SIZE=3
```

### Stream Health Monitoring
```bash
# Health Check Interval (optional, default: 30 seconds)
STREAM_HEALTH_CHECK_INTERVAL=30

# Max Stream Restart Attempts (optional, default: 3)
MAX_STREAM_RESTARTS=3
```

### Current Configuration (nixpacks.toml)

The `nixpacks.toml` file already includes FFmpeg:

```toml
[phases.setup]
nixPkgs = ["postgresql", "libpq", "ffmpeg"]

[phases.install]
nixPkgs = ["opencv", "python311", "ffmpeg"]
```

## Performance Tuning

### Low Latency (Current - Recommended)
- Preset: `ultrafast`
- Bitrate: `512k`
- Resolution: `640x360`
- Segment duration: `1s`
- Playlist size: `3`
- **Latency**: ~2-3 seconds
- **CPU Usage**: Low
- **Quality**: Medium

### Balanced Quality
- Preset: `fast`
- Bitrate: `1024k`
- Resolution: `1280x720`
- Segment duration: `2s`
- Playlist size: `5`
- **Latency**: ~4-6 seconds
- **CPU Usage**: Medium
- **Quality**: High

### High Quality
- Preset: `medium`
- Bitrate: `2048k`
- Resolution: `1920x1080`
- Segment duration: `3s`
- Playlist size: `5`
- **Latency**: ~8-10 seconds
- **CPU Usage**: High
- **Quality**: Very High

## Monitoring

### Health Check Endpoint

The system provides a health check endpoint at `/streams/health` that returns:

```json
{
  "total_streams": 5,
  "streams": [
    {
      "camera_id": 1,
      "is_healthy": true,
      "pid": 12345,
      "uptime_seconds": 3600,
      "restart_count": 0
    }
  ],
  "timestamp": "2026-03-29T23:45:00"
}
```

### Logs

FFmpeg logs are captured by Railway's log aggregation. View logs in Railway dashboard:

```bash
# View real-time logs
railway logs --service <service-name>

# View last 100 lines
railway logs --service <service-name> -n 100
```

## Troubleshooting

### Issue: High CPU Usage

**Solution**: Reduce quality settings
```bash
FFMPEG_PRESET=ultrafast
FFMPEG_VIDEO_BITRATE=512k
FFMPEG_RESOLUTION=640x360
```

### Issue: High Latency

**Solution**: Reduce buffer sizes
```bash
HLS_SEGMENT_DURATION=1
HLS_PLAYLIST_SIZE=3
```

### Issue: FFmpeg Crashes

**Solution**: Check logs and increase memory
```bash
# Check if FFmpeg is installed
railway logs | grep "ffmpeg"

# View FFmpeg specific errors
railway logs | grep "FFmpeg failed"
```

### Issue: Streams Not Starting

**Solution**: Check RTSP connectivity
```bash
# Test RTSP connection from API
POST /api/cameras/test
{
  "manufacturer": "intelbras",
  "ip": "192.168.1.100",
  "port": 554,
  "username": "admin",
  "password": "password"
}
```

## Deployment

### Automatic Deployment

1. Push to `main` branch
2. Railway auto-deploys using `nixpacks.toml`
3. FFmpeg is installed automatically
4. Build time: ~2-3 minutes

### Manual Deployment

```bash
# Connect to Railway project
./connect-railway-project.sh

# Deploy
railway up

# View logs
railway logs --service api
```

## Verification

After deployment, verify FFmpeg is working:

```bash
# 1. Check health endpoint
curl https://your-app.railway.app/health

# 2. Check if FFmpeg is available (should return version info)
curl https://your-app.railway.app/api/ffmpeg-version

# 3. Start a test stream
POST https://your-app.railway.app/api/cameras/{camera_id}/stream/start
```

## Security Notes

- FFmpeg processes run in isolated Railway containers
- No external FFmpeg connections (only inbound RTSP)
- HLS files are served over HTTPS automatically
- All endpoints require JWT authentication
- RTSP URLs are never exposed to frontend

## Maintenance

### Regular Tasks

1. **Monitor health reports** - Check `/streams/health` daily
2. **Review logs** - Look for FFmpeg errors weekly
3. **Update FFmpeg** - Railway updates nixpkgs automatically
4. **Clean up streams** - Old HLS segments auto-delete

### Alerts

Set up Railway alerts for:
- CPU usage > 80%
- Memory usage > 1GB
- Restart count > 3
- Failed health checks
