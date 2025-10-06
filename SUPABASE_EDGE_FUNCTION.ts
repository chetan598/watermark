/**
 * SUPABASE EDGE FUNCTION - INSTANT RETURN (No Timeout!)
 * 
 * File: supabase/functions/process-watermark-video/index.ts
 * 
 * This function:
 * 1. Receives video from frontend
 * 2. Forwards to Render API
 * 3. Returns task_id + stream_url IMMEDIATELY (< 2 seconds)
 * 4. Frontend connects to stream for updates
 * 
 * NO MORE TIMEOUTS! Edge Function exits immediately.
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_API_URL = "https://watermark-g4f2.onrender.com";

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, apikey, x-client-info',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  try {
    console.log('[UPLOAD] Starting video upload...');

    // Get form data from request
    const formData = await req.formData();
    const file = formData.get('file');

    if (!file) {
      throw new Error('No file provided');
    }

    console.log('[UPLOAD] File received:', file.name || 'unnamed', file.size, 'bytes');

    // Forward to Render API
    const renderFormData = new FormData();
    renderFormData.append('file', file);

    console.log('[UPLOAD] Forwarding to Render API...');

    const uploadResponse = await fetch(`${RENDER_API_URL}/upload-stream`, {
      method: 'POST',
      body: renderFormData,
    });

    if (!uploadResponse.ok) {
      const errorText = await uploadResponse.text();
      console.error('[ERROR] Render API failed:', uploadResponse.status, errorText);
      throw new Error(`Render API error: ${uploadResponse.status}`);
    }

    const result = await uploadResponse.json();
    console.log('[SUCCESS] Got task_id:', result.task_id);

    // Return IMMEDIATELY with task_id and stream_url
    // Frontend will connect to stream directly
    return new Response(JSON.stringify({
      success: true,
      task_id: result.task_id,
      stream_url: `${RENDER_API_URL}${result.stream_url}`,
      message: 'Video uploaded! Connect to stream_url for real-time updates.',
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });

  } catch (error) {
    console.error('[ERROR] Edge Function error:', error.message);
    
    return new Response(JSON.stringify({
      success: false,
      error: error.message,
      details: 'Failed to upload video to processing API',
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }
});

/**
 * DEPLOYMENT:
 * 
 * 1. Save this as: supabase/functions/process-watermark-video/index.ts
 * 
 * 2. Deploy:
 *    supabase functions deploy process-watermark-video
 * 
 * 3. Done! Edge Function returns in < 2 seconds, no timeout!
 */

