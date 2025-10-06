/**
 * FRONTEND INTEGRATION - COMPLETE WORKING EXAMPLE
 * 
 * This shows how to call Supabase Edge Function → Get Stream URL → Connect to SSE
 * 
 * NO TIMEOUTS! Connection stays alive for hours.
 */

import { useState, useRef, useEffect } from 'react';
import { supabase } from './supabaseClient'; // Your Supabase client

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

      // Close any existing SSE connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      console.log('📤 Uploading video via Supabase Edge Function...');

      // Call Supabase Edge Function
      const formData = new FormData();
      formData.append('file', selectedFile);

      const { data, error: functionError } = await supabase.functions.invoke(
        'process-watermark-video',
        {
          body: formData,
        }
      );

      if (functionError) {
        throw new Error(functionError.message);
      }

      if (!data.success) {
        throw new Error(data.error || 'Upload failed');
      }

      console.log('✅ Edge Function returned:', data);
      console.log('📡 Connecting to SSE stream:', data.stream_url);

      const { task_id, stream_url } = data;
      setStatus('processing');

      // Connect DIRECTLY to Render API's SSE stream
      const eventSource = new EventSource(stream_url);
      eventSourceRef.current = eventSource;

      // Heartbeat - keeps connection alive
      eventSource.addEventListener('heartbeat', (event) => {
        const heartbeatData = JSON.parse(event.data);
        console.log('💓 Heartbeat:', new Date(heartbeatData.timestamp * 1000).toLocaleTimeString());
      });

      // Waiting status
      eventSource.addEventListener('waiting', (event) => {
        console.log('⏳ Waiting for processing...');
        setStatus('waiting');
      });

      // Real-time progress updates
      eventSource.addEventListener('progress', (event) => {
        const progressData = JSON.parse(event.data);
        console.log(`📊 Progress: ${progressData.progress}%`);
        setProgress(progressData.progress);
        setStatus(progressData.status);
      });

      // Video processing complete!
      eventSource.addEventListener('complete', (event) => {
        const completeData = JSON.parse(event.data);
        console.log('🎉 Video ready!', completeData);

        // Set video URL for download/display
        setVideoUrl(completeData.download_url);
        setProgress(100);
        setStatus('completed');
        setIsProcessing(false);

        // Close stream
        eventSource.close();
        eventSourceRef.current = null;

        console.log('✅ Complete! File size:', (completeData.file_size / (1024 * 1024)).toFixed(2), 'MB');
      });

      // Handle errors from stream
      eventSource.addEventListener('error', (event: MessageEvent) => {
        console.error('❌ Stream error:', event);
        
        try {
          if (event.data) {
            const errorData = JSON.parse(event.data);
            setError(errorData.message || 'Processing error');
          } else {
            setError('Stream connection lost');
          }
        } catch {
          setError('Connection error');
        }
        
        setStatus('error');
        setIsProcessing(false);
        eventSource.close();
        eventSourceRef.current = null;
      });

      // Handle EventSource connection errors
      eventSource.onerror = (err) => {
        console.error('❌ EventSource error:', err);
        // Don't set error here - SSE reconnects automatically
        // Only set error if we get an actual error event
      };

    } catch (err: any) {
      console.error('❌ Upload failed:', err);
      setError(err.message || 'Upload failed');
      setStatus('error');
      setIsProcessing(false);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        console.log('🔌 Closing SSE connection on unmount');
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-3xl font-bold mb-6">✨ Watermark Remover</h2>
      
      {/* File Input */}
      <div className="mb-4">
        <label className="block mb-2 font-semibold">Select Video:</label>
        <input
          type="file"
          accept=".mp4,.mov,.avi"
          onChange={handleFileSelect}
          disabled={isProcessing}
          className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 p-2"
        />
        {selectedFile && (
          <p className="mt-2 text-sm text-gray-600">
            📹 {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
          </p>
        )}
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUploadAndProcess}
        disabled={!selectedFile || isProcessing}
        className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold py-3 px-6 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:from-purple-700 hover:to-indigo-700 transition"
      >
        {isProcessing ? '⏳ Processing...' : '🪄 Remove Watermark'}
      </button>

      {/* Status & Progress */}
      {status !== 'idle' && status !== 'completed' && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm font-semibold text-blue-800 mb-2">
            Status: {status === 'uploading' && '📤 Uploading...'}
            {status === 'waiting' && '⏳ Starting processing...'}
            {status === 'processing' && '⚙️ Removing watermark...'}
            {status === 'adding_audio' && '🔊 Adding audio...'}
          </p>
          {progress > 0 && (
            <div className="w-full bg-gray-200 rounded-full h-6 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-purple-600 to-indigo-600 h-6 flex items-center justify-center text-white text-sm font-bold transition-all duration-300"
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
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">❌ {error}</p>
        </div>
      )}

      {/* Success - Video Ready */}
      {status === 'completed' && videoUrl && (
        <div className="mt-6 p-6 bg-green-50 border border-green-200 rounded-lg">
          <h3 className="text-xl font-bold text-green-800 mb-4">
            ✅ Watermark Removed Successfully!
          </h3>
          <video 
            src={videoUrl} 
            controls 
            className="w-full rounded-lg mb-4"
          />
          <a
            href={videoUrl}
            download="cleaned_video.mp4"
            className="inline-block bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition"
          >
            ⬇️ Download Cleaned Video
          </a>
        </div>
      )}
    </div>
  );
}

