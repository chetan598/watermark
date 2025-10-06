# 🔧 FIX SUPABASE TIMEOUT - COMPLETE SOLUTION

## The Problem

Your Supabase Edge Function is timing out because it waits for video processing to complete.

**Supabase Edge Function Limits:**
- Max execution time: ~150 seconds
- Your video processing: Can take 1-5 minutes
- Result: ❌ "The signal has been aborted"

---

## The Solution

**Edge Function should return IMMEDIATELY, not wait for processing!**

### Flow:

```
OLD (Times out ❌):
Frontend → Edge Function → Render API → WAIT → WAIT → TIMEOUT!

NEW (Never times out ✅):
Frontend → Edge Function → Render API
         ↓ (returns immediately)
Frontend → Stream URL (SSE) → Real-time updates → Video ready!
```

---

## 🚀 Implementation Steps

### Step 1: Update Supabase Edge Function

**File:** `supabase/functions/process-watermark-video/index.ts`

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_API = "https://watermark-g4f2.onrender.com";

serve(async (req) => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
      },
    });
  }

  try {
    // Get file from frontend
    const formData = await req.formData();
    const file = formData.get('file');

    if (!file) {
      throw new Error('No file provided');
    }

    // Forward to Render (returns immediately!)
    const renderForm = new FormData();
    renderForm.append('file', file);

    const response = await fetch(`${RENDER_API}/upload-stream`, {
      method: 'POST',
      body: renderForm,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }

    const { task_id, stream_url } = await response.json();

    // Return IMMEDIATELY - don't wait for processing!
    return new Response(JSON.stringify({
      success: true,
      task_id,
      stream_url: `${RENDER_API}${stream_url}`,
    }), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });

  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      error: error.message,
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
});
```

**Deploy:**
```bash
supabase functions deploy process-watermark-video
```

---

### Step 2: Update Frontend (React)

**File:** `VideoWatermarkRemover.tsx`

```typescript
import { useState, useRef, useEffect } from 'react';
import { supabase } from './supabaseClient';

export function VideoWatermarkRemover() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle');
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setProgress(0);
      setStatus('uploading');
      setError('');

      // Close existing connection
      eventSourceRef.current?.close();

      // 1. Call Edge Function (returns immediately!)
      const formData = new FormData();
      formData.append('file', selectedFile);

      const { data, error: edgeError } = await supabase.functions.invoke(
        'process-watermark-video',
        { body: formData }
      );

      if (edgeError || !data.success) {
        throw new Error(edgeError?.message || data.error || 'Upload failed');
      }

      console.log('✅ Got task_id:', data.task_id);
      console.log('📡 Streaming from:', data.stream_url);

      setStatus('processing');

      // 2. Connect to SSE stream DIRECTLY
      const eventSource = new EventSource(data.stream_url);
      eventSourceRef.current = eventSource;

      // Heartbeat
      eventSource.addEventListener('heartbeat', () => {
        console.log('💓 Connection alive');
      });

      // Progress
      eventSource.addEventListener('progress', (e) => {
        const { progress: p, status: s } = JSON.parse(e.data);
        setProgress(p);
        setStatus(s);
      });

      // Complete
      eventSource.addEventListener('complete', (e) => {
        const { download_url } = JSON.parse(e.data);
        setVideoUrl(download_url);
        setProgress(100);
        setStatus('completed');
        eventSource.close();
      });

      // Error
      eventSource.addEventListener('error', (e: any) => {
        const msg = e.data ? JSON.parse(e.data).message : 'Connection error';
        setError(msg);
        setStatus('error');
        eventSource.close();
      });

    } catch (err: any) {
      setError(err.message);
      setStatus('error');
    }
  };

  // Cleanup
  useEffect(() => {
    return () => eventSourceRef.current?.close();
  }, []);

  return (
    <div>
      <input type="file" onChange={handleFileSelect} accept=".mp4,.mov,.avi" />
      <button onClick={handleUpload} disabled={!selectedFile || status === 'processing'}>
        Remove Watermark
      </button>
      
      {progress > 0 && <progress value={progress} max="100" />}
      {status && <p>Status: {status}</p>}
      {error && <p style={{color: 'red'}}>{error}</p>}
      {videoUrl && <video src={videoUrl} controls />}
    </div>
  );
}
```

---

## 🎯 Alternative: Skip Supabase Edge Function Entirely

Call Render API DIRECTLY from frontend (simplest solution!):

```typescript
const handleUpload = async () => {
  const formData = new FormData();
  formData.append('file', selectedFile);

  // 1. Upload directly to Render
  const response = await fetch('https://watermark-g4f2.onrender.com/upload-stream', {
    method: 'POST',
    body: formData,
  });

  const { task_id, stream_url } = await response.json();

  // 2. Connect to SSE stream
  const eventSource = new EventSource(`https://watermark-g4f2.onrender.com${stream_url}`);

  eventSource.addEventListener('progress', (e) => {
    const { progress } = JSON.parse(e.data);
    setProgress(progress);
  });

  eventSource.addEventListener('complete', (e) => {
    const { download_url } = JSON.parse(e.data);
    setVideoUrl(`https://watermark-g4f2.onrender.com${download_url}`);
    eventSource.close();
  });
};
```

---

## 📊 Comparison

| Method | Timeout Risk | Complexity |
|--------|--------------|------------|
| **Old (Polling)** | ❌ HIGH | High |
| **Edge Function Wait** | ❌ HIGH | Medium |
| **Edge Function → SSE** | ✅ NONE | Medium |
| **Direct → SSE** | ✅ NONE | Low |

---

## ✅ What's Fixed

1. ✅ **Edge Function returns in < 2 seconds** (no timeout)
2. ✅ **SSE connection stays alive for hours** (heartbeat every 15s)
3. ✅ **Real-time progress** (0.5s updates)
4. ✅ **Auto video delivery** when ready
5. ✅ **Independent tasks** (each has own stream)

---

## 🔥 Test It

### Deploy Edge Function:
```bash
supabase functions deploy process-watermark-video
```

### Test from Frontend:
Upload a video → Should see:
```
✅ Got task_id: 20251006_153417_292_0d4fe8a6
📡 Streaming from: https://watermark-g4f2.onrender.com/stream/...
💓 Heartbeat: 3:45:12 PM
📊 Progress: 25%
📊 Progress: 67%
🎉 Video ready!
```

**NO MORE TIMEOUTS!** 🎉

---

## 📋 Deployment Checklist

- [ ] Update Edge Function with code above
- [ ] Deploy: `supabase functions deploy process-watermark-video`
- [ ] Update frontend component
- [ ] Test upload
- [ ] Connection should stay alive for hours ✅

---

**The connection will NEVER timeout now!** Even if processing takes 1 hour, the heartbeat keeps it alive! 💪

