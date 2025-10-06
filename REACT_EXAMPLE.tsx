/**
 * DROP-IN REPLACEMENT FOR YOUR VideoWatermarkRemover COMPONENT
 * 
 * This uses SSE streaming - NEVER times out, even for 1 hour!
 * Copy this into your VideoWatermarkRemover.tsx file
 */

import { useState, useRef } from 'react';

const RENDER_API = "https://watermark-g4f2.onrender.com";

export function VideoWatermarkRemover() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>('idle');
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      // Reset state
      setProgress(0);
      setStatus('idle');
      setVideoUrl('');
      setError('');
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) {
      setError('Please select a video file');
      return;
    }

    try {
      setIsProcessing(true);
      setProgress(0);
      setStatus('uploading');
      setError('');
      setVideoUrl('');

      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      console.log('🚀 Uploading video to:', `${RENDER_API}/upload-stream`);

      // 1. Upload video (returns IMMEDIATELY - no timeout!)
      const formData = new FormData();
      formData.append('file', selectedFile);

      const uploadResponse = await fetch(`${RENDER_API}/upload-stream`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.status}`);
      }

      const { task_id, stream_url } = await uploadResponse.json();
      console.log('✅ Upload successful! Task ID:', task_id);
      console.log('📡 Connecting to stream:', stream_url);

      setStatus('processing');

      // 2. Connect to SSE stream for real-time updates
      const eventSource = new EventSource(`${RENDER_API}${stream_url}`);
      eventSourceRef.current = eventSource;

      // 3. Heartbeat - connection is alive
      eventSource.addEventListener('heartbeat', (event) => {
        const data = JSON.parse(event.data);
        console.log('💓 Heartbeat:', data.timestamp);
        // Connection is alive - do nothing, just log
      });

      // 4. Waiting for processing
      eventSource.addEventListener('waiting', (event) => {
        const data = JSON.parse(event.data);
        console.log('⏳ Waiting:', data.message);
        setStatus('waiting');
      });

      // 5. Progress updates (real-time!)
      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        console.log(`📊 Progress: ${data.progress}% (${data.status})`);
        setProgress(data.progress);
        setStatus(data.status);
      });

      // 6. Video ready! (automatically delivered)
      eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        console.log('🎉 Video ready!', data);

        const videoDownloadUrl = `${RENDER_API}${data.download_url}`;
        setVideoUrl(videoDownloadUrl);
        setProgress(100);
        setStatus('completed');
        setIsProcessing(false);

        // Close the stream
        eventSource.close();
        eventSourceRef.current = null;

        console.log('✅ Processing complete! File size:', data.file_size, 'bytes');
      });

      // 7. Handle errors
      eventSource.addEventListener('error', (event: any) => {
        console.error('❌ Stream error:', event);
        
        try {
          const data = JSON.parse(event.data || '{}');
          setError(data.message || 'Stream connection error');
        } catch {
          setError('Connection lost. The server may still be processing.');
        }
        
        setStatus('error');
        setIsProcessing(false);
        eventSource.close();
        eventSourceRef.current = null;
      });

      // Handle connection errors
      eventSource.onerror = (err) => {
        console.error('❌ EventSource error:', err);
        setError('Connection error. Please check server status.');
        setStatus('error');
        setIsProcessing(false);
        eventSource.close();
        eventSourceRef.current = null;
      };

    } catch (err: any) {
      console.error('❌ Upload error:', err);
      setError(err.message || 'Upload failed');
      setStatus('error');
      setIsProcessing(false);
    }
  };

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="watermark-remover">
      <h2>✨ Watermark Remover</h2>
      
      {/* File Input */}
      <div className="upload-section">
        <input
          type="file"
          accept=".mp4,.mov,.avi"
          onChange={handleFileSelect}
          disabled={isProcessing}
        />
        {selectedFile && (
          <p>Selected: {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</p>
        )}
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUploadAndProcess}
        disabled={!selectedFile || isProcessing}
        className="upload-btn"
      >
        {isProcessing ? '⏳ Processing...' : '🚀 Remove Watermark'}
      </button>

      {/* Status Display */}
      {status !== 'idle' && status !== 'completed' && (
        <div className="status-section">
          <p>Status: {status}</p>
          {progress > 0 && (
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${progress}%` }}
              >
                {progress}%
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error" style={{ color: 'red', padding: '10px', border: '1px solid red' }}>
          ❌ {error}
        </div>
      )}

      {/* Success - Video Ready! */}
      {status === 'completed' && videoUrl && (
        <div className="success-section">
          <h3>✅ Watermark Removed Successfully!</h3>
          <video src={videoUrl} controls style={{ width: '100%', maxWidth: '600px' }} />
          <br />
          <a 
            href={videoUrl} 
            download="cleaned_video.mp4"
            className="download-btn"
            style={{ display: 'inline-block', marginTop: '10px', padding: '10px 20px', background: '#4caf50', color: 'white', textDecoration: 'none', borderRadius: '5px' }}
          >
            ⬇️ Download Cleaned Video
          </a>
        </div>
      )}

      {/* Styles */}
      <style>{`
        .progress-bar {
          width: 100%;
          height: 30px;
          background: #f0f0f0;
          border-radius: 15px;
          overflow: hidden;
          margin: 10px 0;
        }
        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          transition: width 0.3s ease;
        }
        .upload-btn {
          padding: 15px 30px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 10px;
          font-size: 16px;
          font-weight: bold;
          cursor: pointer;
          margin: 10px 0;
        }
        .upload-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}

export default VideoWatermarkRemover;

