from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import cv2
import numpy as np
import os
import subprocess
from pathlib import Path
from typing import Optional
import asyncio
import requests
import time
from datetime import datetime
import secrets
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Initialize FastAPI app
app = FastAPI(
    title="Watermark Remover API - Storage Based",
    description="Professional watermark removal with Supabase Storage integration",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Create temp directory for processing
TEMP_DIR = Path("temp_processing")
TEMP_DIR.mkdir(exist_ok=True)

# Watermark masks configuration
WATERMARK_MASKS = [
    {'id': 1, 'x': 330, 'y': 404, 'w': 150, 'h': 62, 'start': 0.0, 'end': 1.0},
    {'id': 2, 'x': 5,   'y': 670, 'w': 130, 'h': 75, 'start': 0.5, 'end': 4.0},
    {'id': 3, 'x': 10,  'y': 37,  'w': 120, 'h': 72, 'start': 3.2, 'end': 6.2},
    {'id': 4, 'x': 334, 'y': 398, 'w': 138, 'h': 67, 'start': 6.0, 'end': 9.0},
    {'id': 5, 'x': 0,   'y': 670, 'w': 130, 'h': 75, 'start': 7, 'end': 9.8}
]

# Processing status storage
processing_status = {}
used_task_ids = set()

# Request model
class ProcessVideoRequest(BaseModel):
    task_id: str
    video_url: str  # Supabase Storage URL
    supabase_url: str
    supabase_key: str

def generate_unique_task_id() -> str:
    """Generate unique task ID"""
    while True:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        microseconds = f"{datetime.now().microsecond:06d}"[:3]
        random_part = secrets.token_hex(4)
        task_id = f"{timestamp}_{microseconds}_{random_part}"
        if task_id not in used_task_ids:
            used_task_ids.add(task_id)
            return task_id

def process_frame_with_watermark(frame, mask, current_time):
    """ULTRA-FAST watermark removal using TELEA algorithm"""
    is_watermark_present = False
    for wm in WATERMARK_MASKS:
        if wm['start'] <= current_time < wm['end']:
            x, y, w, h = wm['x'], wm['y'], wm['w'], wm['h']
            cv2.rectangle(mask, (x, y), (x + w, y + h), (255), -1)
            is_watermark_present = True
    
    if not is_watermark_present:
        return frame
    
    # Fast inpainting
    reconstructed = cv2.inpaint(frame, mask, 10, cv2.INPAINT_TELEA)
    reconstructed = cv2.GaussianBlur(reconstructed, (5, 5), 0)
    
    # Feathered masking
    mask_float = mask.astype(float) / 255.0
    mask_soft = cv2.GaussianBlur(mask_float, (21, 21), 0)
    mask_soft = np.stack([mask_soft] * 3, axis=-1)
    
    # Blend
    final_frame = (mask_soft * reconstructed + (1 - mask_soft) * frame).astype(np.uint8)
    return final_frame

def download_video_from_url(url: str, output_path: str) -> bool:
    """Download video from Supabase Storage URL"""
    try:
        print(f"Downloading video from: {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"Downloaded successfully: {output_path}")
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False

def send_video_to_callback(video_path: str, task_id: str, callback_url: str) -> bool:
    """Send processed video back to the callback URL that made the request"""
    try:
        print(f"📤 Sending processed video back to callback URL: {callback_url}")
        
        # Read video file
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        # Create form data for multipart upload
        files = {
            'video': (f'processed_{task_id}.mp4', video_data, 'video/mp4')
        }
        
        data = {
            'task_id': task_id,
            'status': 'completed',
            'message': 'Video processing completed successfully'
        }
        
        # Send to callback URL
        response = requests.post(
            callback_url,
            files=files,
            data=data,
            timeout=300  # 5 minutes timeout for large files
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Video sent to callback URL successfully")
            return True
        else:
            print(f"❌ Failed to send to callback URL: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending to callback URL: {e}")
        return False

def process_video_with_inpainting(input_video_path: str, output_video_path: str, task_id: str) -> bool:
    """Process video with watermark removal"""
    try:
        processing_status[task_id] = {"status": "processing", "progress": 0}
        
        cap = cv2.VideoCapture(input_video_path)
        if not cap.isOpened():
            processing_status[task_id] = {"status": "error", "message": "Could not open video"}
            return False

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        # Process in parallel batches
        batch_size = 50
        max_workers = min(8, multiprocessing.cpu_count())
        
        current_frame_num = 0
        frame_batch = []
        time_batch = []
    
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = current_frame_num / fps
            frame_batch.append(frame.copy())
            time_batch.append(current_time)
            
            if len(frame_batch) >= batch_size or current_frame_num == frame_count - 1:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    masks = [np.zeros(frame.shape[:2], dtype=np.uint8) for frame in frame_batch]
                    processed_frames = list(executor.map(
                        process_frame_with_watermark,
                        frame_batch,
                        masks,
                        time_batch
                    ))
                
                for processed_frame in processed_frames:
                    out.write(processed_frame)
                
                frame_batch = []
                time_batch = []
                
                progress = (current_frame_num + 1) / frame_count
                processing_status[task_id]["progress"] = int(progress * 100)
        
            current_frame_num += 1

        cap.release()
        out.release()
        cv2.destroyAllWindows()
    
        # Add audio
        processing_status[task_id]["status"] = "adding_audio"
        
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except:
            ffmpeg_path = 'ffmpeg'
        
        output_with_audio = output_video_path.replace('.mp4', '_audio.mp4')
        
        cmd = [
            ffmpeg_path, '-y',
            '-i', output_video_path,
            '-i', input_video_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-c:a', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0?',
            '-shortest',
            output_with_audio
        ]
        
        subprocess.run(cmd, capture_output=True, text=True)
        
        if os.path.exists(output_with_audio) and os.path.getsize(output_with_audio) > 0:
            os.remove(output_video_path)
            os.rename(output_with_audio, output_video_path)
            
        processing_status[task_id]["status"] = "completed"
        processing_status[task_id]["progress"] = 100
        return True
            
    except Exception as e:
        processing_status[task_id] = {"status": "error", "message": str(e)}
        return False

async def process_video_task(request: ProcessVideoRequest):
    """Background task to process video from URL"""
    task_id = request.task_id
    
    try:
        processing_status[task_id] = {"status": "downloading", "progress": 0}
        
        # Download video
        input_path = TEMP_DIR / f"{task_id}_input.mp4"
        if not download_video_from_url(request.video_url, str(input_path)):
            processing_status[task_id] = {"status": "error", "message": "Download failed"}
            return
        
        # Process video
        output_path = TEMP_DIR / f"{task_id}_output.mp4"
        if not process_video_with_inpainting(str(input_path), str(output_path), task_id):
            return
        
        # Send processed video back to callback URL
        if request.callback_url:
            processing_status[task_id]["status"] = "uploading"
            print(f"🎬 Video processing complete, sending back to callback URL...")
            
            success = send_video_to_callback(
                str(output_path),
                task_id,
                request.callback_url
            )
            
            if success:
                processing_status[task_id] = {
                    "status": "completed",
                    "progress": 100,
                    "message": "Video sent to callback URL successfully"
                }
                print(f"🎉 Task {task_id} completed successfully! Video sent to callback URL.")
            else:
                processing_status[task_id] = {
                    "status": "error",
                    "message": "Failed to send video to callback URL"
                }
                print(f"❌ Task {task_id} failed: Failed to send video to callback URL")
        else:
            # No callback URL provided, just mark as completed
            processing_status[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Video processing completed (no callback URL provided)"
            }
            print(f"🎉 Task {task_id} completed successfully! (No callback URL provided)")
        
        # Cleanup temp files
        if input_path.exists():
            os.remove(input_path)
        if output_path.exists():
            os.remove(output_path)
            
    except Exception as e:
        processing_status[task_id] = {"status": "error", "message": str(e)}

# --- API Routes ---

@app.get("/")
async def root():
    return {
        "message": "Watermark Remover API - Direct Response",
        "version": "2.0.0",
        "endpoints": {
            "POST /process": "Process video and return processed video directly",
            "GET /status/{task_id}": "Check processing status",
            "GET /stream/{task_id}": "SSE stream for progress",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "watermark-remover-storage"}

@app.post("/process")
async def process_video(request: ProcessVideoRequest):
    """
    Process video from Supabase Storage URL and return processed video directly
    
    Args:
        task_id: Unique task identifier
        video_url: Supabase Storage URL of the video
        supabase_url: Supabase project URL
        supabase_key: Supabase service key
    
    Returns:
        Processed video file directly in the response
    """
    print(f"Received process request for task: {request.task_id}")
    
    try:
        # Set initial status
        processing_status[request.task_id] = {"status": "downloading", "progress": 0}
        
        # Download video
        input_path = TEMP_DIR / f"{request.task_id}_input.mp4"
        if not download_video_from_url(request.video_url, str(input_path)):
            processing_status[request.task_id] = {"status": "error", "message": "Download failed"}
            raise HTTPException(status_code=400, detail="Download failed")
        
        # Process video
        output_path = TEMP_DIR / f"{request.task_id}_output.mp4"
        if not process_video_with_inpainting(str(input_path), str(output_path), request.task_id):
            processing_status[request.task_id] = {"status": "error", "message": "Processing failed"}
            raise HTTPException(status_code=500, detail="Video processing failed")
        
        # Mark as completed
        processing_status[request.task_id] = {
            "status": "completed",
            "progress": 100,
            "message": "Video processing completed successfully"
        }
        
        # Return the processed video file directly
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(output_path),
            filename=f"processed_{request.task_id}.mp4",
            media_type="video/mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        processing_status[request.task_id] = {"status": "error", "message": str(e)}
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        # Cleanup temp files
        try:
            input_path = locals().get('input_path')
            output_path = locals().get('output_path')
            if input_path and input_path.exists():
                os.remove(input_path)
            # Do not remove output_path here as it's being sent back
            # It should be cleaned up later if needed, or by a separate process
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Get processing status"""
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return processing_status[task_id]

@app.get("/stream/{task_id}")
async def stream_progress(task_id: str):
    """Server-Sent Events for real-time progress"""
    async def event_generator():
        try:
            last_progress = -1
            heartbeat_counter = 0
            
            while True:
                heartbeat_counter += 1
                if heartbeat_counter % 4 == 0:
                    yield {
                        "event": "heartbeat",
                        "data": f'{{"alive": true, "timestamp": {int(time.time())}}}'
                    }
                
                if task_id not in processing_status:
                    yield {
                        "event": "waiting",
                        "data": '{"message": "Waiting for processing to start..."}'
                    }
                    await asyncio.sleep(0.5)
                    continue
                
                status_data = processing_status[task_id]
                current_progress = status_data.get("progress", 0)
                current_status = status_data.get("status", "processing")
                
                if current_progress != last_progress or heartbeat_counter % 10 == 0:
                    yield {
                        "event": "progress",
                        "data": f'{{"progress": {current_progress}, "status": "{current_status}"}}'
                    }
                    last_progress = current_progress
                
                if current_status == "completed":
                    processed_url = status_data.get("processed_video_url", "")
                    yield {
                        "event": "complete",
                        "data": f'{{"status": "completed", "processed_video_url": "{processed_url}", "task_id": "{task_id}"}}'
                    }
                    break
                
                if current_status == "error":
                    error_msg = status_data.get("message", "Unknown error").replace('"', '\\"')
                    yield {
                        "event": "error",
                        "data": f'{{"message": "{error_msg}"}}'
                    }
                    break
                
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            yield {
                "event": "error",
                "data": f'{{"message": "Stream error: {str(e)}"}}'
            }
    
    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
        ping=15
    )

@app.delete("/cleanup/{task_id}")
async def cleanup_task(task_id: str):
    """Clean up task data"""
    if task_id in processing_status:
        del processing_status[task_id]
    
    # Clean up any remaining temp files
    for file in TEMP_DIR.glob(f"{task_id}*"):
        try:
            os.remove(file)
        except:
            pass
    
    return {"message": "Task cleaned up successfully"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        timeout_keep_alive=3600,
        timeout_graceful_shutdown=30,
        access_log=True
    )
