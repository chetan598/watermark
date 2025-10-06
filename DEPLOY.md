# 🚀 Deployment Guide for Render

## Quick Deploy to Render

### Option 1: Using render.yaml (Recommended)

1. **Push to GitHub** (already done! ✅)
   ```bash
   git push origin main
   ```

2. **Create New Web Service on Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `chetan598/watermark`
   - Render will auto-detect `render.yaml`

3. **Deploy!**
   - Click "Apply" and Render will deploy automatically

### Option 2: Manual Configuration

If you prefer manual setup:

**Build Command:**
```bash
apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libxrender-dev libgomp1 && pip install --upgrade pip && pip install -r requirements.txt
```

**Start Command:**
```bash
python main.py
```

**Environment Variables:**
- `PYTHON_VERSION`: `3.11.5`

**Health Check Path:**
- `/health`

---

## Render Configuration Details

### System Dependencies Required:

- **ffmpeg** - For audio/video processing
- **libsm6, libxext6, libxrender-dev** - For OpenCV
- **libgomp1** - For multi-threading support

### Python Version:

- **Recommended**: Python 3.11.x
- **Avoid**: Python 3.13 (numpy/opencv compatibility issues)

### Disk Storage:

- **10GB disk** for temporary video storage
- Mounted at `/opt/render/project/src/outputs`

---

## Alternative Build Commands

### Minimal (Faster build):
```bash
apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
```

### With system libraries (Recommended):
```bash
apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libxrender-dev libgomp1 && pip install --upgrade pip && pip install -r requirements.txt
```

### Full (includes debugging tools):
```bash
apt-get update && apt-get install -y ffmpeg libsm6 libxext6 libxrender-dev libgomp1 libgl1 && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt
```

---

## Environment Variables (Optional)

Add these in Render Dashboard → Environment:

```bash
# Python settings
PYTHON_VERSION=3.11.5

# API settings (optional)
PORT=8000
HOST=0.0.0.0

# Performance (optional)
WORKERS=1
```

---

## Post-Deployment

### Test Your API:

```bash
# Replace with your Render URL
RENDER_URL="https://your-app.onrender.com"

# Health check
curl $RENDER_URL/health

# Upload video
curl -X POST "$RENDER_URL/upload" \
  -F "file=@test_video.mp4" \
  -F "webhook_url=https://webhook.site/your-id"
```

### API Documentation:

- Swagger UI: `https://your-app.onrender.com/docs`
- ReDoc: `https://your-app.onrender.com/redoc`

---

## Troubleshooting

### Build Fails with numpy error:

**Solution**: Use Python 3.11, not 3.13
- Add `runtime.txt` with `python-3.11.9`
- Or set `PYTHON_VERSION=3.11.5` in environment

### ffmpeg not found:

**Solution**: Add ffmpeg to build command
```bash
apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt
```

### OpenCV import error:

**Solution**: Install system libraries
```bash
apt-get install -y libsm6 libxext6 libxrender-dev libgomp1
```

### Out of memory:

**Solution**: Reduce batch size in `main.py`:
```python
# Line 160
batch_size = 15  # Reduce from 30 to 15
max_workers = 2  # Reduce from 4 to 2
```

### Slow cold starts:

**Solution**: 
- Upgrade to paid plan (keeps instance running)
- Or use Render Cron to ping every 10 minutes

---

## Free Tier Limitations

Render Free Tier includes:
- ✅ 750 hours/month
- ✅ Auto-sleep after 15 min inactivity
- ✅ Shared CPU/RAM
- ⚠️ Cold starts (10-30 seconds)
- ⚠️ No persistent disk on free tier

**For Production**: Upgrade to Starter ($7/month) for:
- Always-on instances
- Persistent disk
- Better performance

---

## Deployment Checklist

- [x] Push code to GitHub
- [ ] Create Render account
- [ ] Connect GitHub repository
- [ ] Configure build command
- [ ] Set Python version to 3.11
- [ ] Add health check path
- [ ] Deploy!
- [ ] Test endpoints
- [ ] Monitor logs

---

## Monitoring

View logs in Render Dashboard:
- Build logs - Check for dependency issues
- Deploy logs - Watch startup
- Runtime logs - Monitor requests

---

## Cost Estimate

### Free Tier:
- API hosting: **$0/month**
- 750 hours free
- Auto-sleeps when idle

### Starter Plan ($7/month):
- Always-on
- 512MB RAM
- 0.5 CPU
- Better for production

### Pro Plan ($25/month):
- 2GB RAM
- 1 CPU
- Faster processing

---

## Next Steps

1. **Deploy**: Follow Option 1 or 2 above
2. **Test**: Use curl or Postman
3. **Monitor**: Check Render dashboard
4. **Scale**: Upgrade if needed

Need help? Check: https://render.com/docs

