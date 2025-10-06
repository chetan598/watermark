# 🔴 Real-Time Streaming API Guide

## NEW: Live Progress Updates + Auto Video Delivery

No more timeouts! The API now supports **Server-Sent Events (SSE)** for real-time progress updates and automatic video delivery.

---

## 🚀 How It Works

### Traditional (Old Way - Can Timeout ❌):
```
1. Upload video → wait... wait... wait... → timeout (504)
2. Poll /status every second
3. Download video when ready
```

### Streaming (New Way - Never Timeouts ✅):
```
1. Upload video → get task_id immediately
2. Connect to SSE stream → receive live updates
3. Get video automatically when ready
```

---

## 📡 API Endpoints

### 1. Upload with Streaming (NEW)
```
POST /upload-stream
```

**Returns immediately** with `task_id` and `stream_url`

### 2. Connect to Stream
```
GET /stream/{task_id}
```

**Keeps connection alive** and sends:
- Real-time progress updates (every 0.5s)
- Status changes
- Final video URL when complete

### 3. Traditional Upload (Still Available)
```
POST /upload
```

Works as before - returns task_id, poll manually

---

## 🎯 Frontend Implementation (React)

### Example: Using EventSource (Native SSE)

```typescript
// 1. Upload video
const formData = new FormData();
formData.append('file', videoFile);

const uploadResponse = await fetch('https://watermark-g4f2.onrender.com/upload-stream', {
  method: 'POST',
  body: formData,
});

const { task_id, stream_url } = await uploadResponse.json();

// 2. Connect to SSE stream
const eventSource = new EventSource(`https://watermark-g4f2.onrender.com${stream_url}`);

// 3. Listen for progress updates
eventSource.addEventListener('progress', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
  setProgress(data.progress); // Update UI
});

// 4. Listen for completion
eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('Video ready!', data.download_url);
  
  // Download or display video
  const videoUrl = `https://watermark-g4f2.onrender.com${data.download_url}`;
  setVideoUrl(videoUrl);
  
  eventSource.close(); // Close connection
});

// 5. Handle errors
eventSource.addEventListener('error', (event) => {
  const data = JSON.parse(event.data);
  console.error('Error:', data.message);
  eventSource.close();
});
```

---

## 🔥 Complete React Component Example

```typescript
import { useState } from 'react';

export function VideoWatermarkRemover() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');

  const handleUpload = async (file: File) => {
    try {
      // Reset state
      setProgress(0);
      setStatus('uploading');
      setError('');
      setVideoUrl('');

      // 1. Upload video
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await fetch(
        'https://watermark-g4f2.onrender.com/upload-stream',
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!uploadResponse.ok) {
        throw new Error('Upload failed');
      }

      const { task_id, stream_url } = await uploadResponse.json();
      setStatus('processing');

      // 2. Connect to SSE stream
      const eventSource = new EventSource(
        `https://watermark-g4f2.onrender.com${stream_url}`
      );

      // 3. Progress updates
      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        setProgress(data.progress);
        setStatus(data.status);
      });

      // 4. Completion
      eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        const videoUrl = `https://watermark-g4f2.onrender.com${data.download_url}`;
        
        setVideoUrl(videoUrl);
        setStatus('completed');
        setProgress(100);
        
        eventSource.close();
      });

      // 5. Errors
      eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data || '{}');
        setError(data.message || 'Stream connection error');
        setStatus('error');
        eventSource.close();
      });

      // Cleanup on unmount
      return () => eventSource.close();

    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  return (
    <div>
      <input type="file" onChange={(e) => handleUpload(e.target.files[0])} />
      
      {status === 'processing' && (
        <div>
          <progress value={progress} max="100" />
          <p>{progress}% complete</p>
        </div>
      )}
      
      {status === 'completed' && videoUrl && (
        <div>
          <video src={videoUrl} controls />
          <a href={videoUrl} download>Download</a>
        </div>
      )}
      
      {error && <p style={{color: 'red'}}>{error}</p>}
    </div>
  );
}
```

---

## 📊 SSE Event Types

### Event: `progress`
```json
{
  "progress": 45,
  "status": "processing"
}
```

### Event: `complete`
```json
{
  "status": "completed",
  "download_url": "/download/20251006_153417_292_0d4fe8a6_output.mp4",
  "file_size": 15728640
}
```

### Event: `error`
```json
{
  "message": "Video processing failed"
}
```

---

## 🎯 Supabase Edge Function Update

```typescript
// Update your Supabase Edge Function to use streaming

export async function processVideoWithStreaming(videoFile: File) {
  const formData = new FormData();
  formData.append('file', videoFile);

  // Upload to get task_id
  const uploadResponse = await fetch(
    'https://watermark-g4f2.onrender.com/upload-stream',
    {
      method: 'POST',
      body: formData,
    }
  );

  const { task_id, stream_url } = await uploadResponse.json();

  // Return task_id and stream_url to frontend
  return {
    task_id,
    stream_url: `https://watermark-g4f2.onrender.com${stream_url}`,
  };
}
```

Then in your React app, connect to the `stream_url` with EventSource.

---

## ⚡ Benefits

| Feature | Old (Polling) | New (SSE Streaming) |
|---------|--------------|---------------------|
| Timeout | ❌ 504 after 60s | ✅ Never times out |
| Updates | Poll every 1s | Real-time (0.5s) |
| Bandwidth | High (constant polling) | Low (push only) |
| Complexity | Multiple requests | Single connection |
| Video Delivery | Manual download | Auto-delivered |

---

## 🔧 Testing SSE Locally

```bash
# 1. Upload video
curl -X POST "http://localhost:8000/upload-stream" \
  -F "file=@test.mp4"

# Response:
{
  "task_id": "20251006_153417_292_0d4fe8a6",
  "stream_url": "/stream/20251006_153417_292_0d4fe8a6",
  "message": "Video uploaded. Connect to stream_url for real-time updates."
}

# 2. Connect to stream (in browser or with curl)
curl -N https://watermark-g4f2.onrender.com/stream/20251006_153417_292_0d4fe8a6

# You'll see:
event: progress
data: {"progress": 10, "status": "processing"}

event: progress
data: {"progress": 45, "status": "processing"}

event: complete
data: {"status": "completed", "download_url": "/download/...", "file_size": 12345}
```

---

## 🌐 CORS is Fixed

SSE works across origins - no CORS issues! ✅

---

## 💡 Why This Solves Your Problem

1. ✅ **No 504 timeout** - connection stays alive
2. ✅ **Real-time updates** - see progress instantly
3. ✅ **Auto video delivery** - get URL when ready
4. ✅ **Independent requests** - each upload tracked separately
5. ✅ **Live connection** - maintained throughout processing

---

## 📋 Migration Guide

### In Your Supabase Edge Function:

**Change this:**
```typescript
// OLD
const response = await fetch(RENDER_URL + '/upload', ...);
// Waits for completion → times out
```

**To this:**
```typescript
// NEW
const response = await fetch(RENDER_URL + '/upload-stream', ...);
const { task_id, stream_url } = await response.json();

// Return to frontend immediately
return { task_id, stream_url };
```

### In Your React Component:

Connect to `stream_url` with `EventSource` (example above).

---

## 🚀 Deploy Commands

```bash
# Already committed and pushing...
git push origin main
```

**Render will deploy in ~5 minutes with SSE support!**

---

**No more timeouts! Each request is independent and streams results in real-time!** 🎉

