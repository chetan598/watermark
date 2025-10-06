"""
Example Webhook Receiver
This demonstrates how to receive the processed video from the API

Run this on a different port (e.g., 5000) and use http://localhost:5000/webhook as your webhook URL
"""

from fastapi import FastAPI, File, UploadFile, Form
import uvicorn
import os
from datetime import datetime

app = FastAPI(title="Webhook Receiver Example")

# Directory to save received videos
RECEIVED_DIR = "received_videos"
os.makedirs(RECEIVED_DIR, exist_ok=True)


@app.post("/webhook")
async def receive_webhook(
    video: UploadFile = File(...),
    task_id: str = Form(...),
    status: str = Form(...),
    file_size_mb: float = Form(...)
):
    """
    Receive the processed video from the watermark remover API
    """
    print("=" * 60)
    print(f"📨 WEBHOOK RECEIVED at {datetime.now()}")
    print(f"Task ID: {task_id}")
    print(f"Status: {status}")
    print(f"File Size: {file_size_mb} MB")
    print("=" * 60)
    
    # Save the video
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{timestamp}_{task_id[:8]}_processed.mp4"
    output_path = os.path.join(RECEIVED_DIR, output_filename)
    
    # Write video to disk
    with open(output_path, "wb") as f:
        content = await video.read()
        f.write(content)
    
    print(f"✅ Video saved to: {output_path}")
    print(f"📊 Actual file size: {len(content) / (1024*1024):.2f} MB")
    print("=" * 60)
    
    # Your custom logic here
    # - Send to S3/cloud storage
    # - Send notification
    # - Trigger another process
    # - etc.
    
    return {
        "received": True,
        "task_id": task_id,
        "saved_to": output_path,
        "timestamp": timestamp
    }


@app.get("/")
def root():
    return {
        "message": "Webhook Receiver Running",
        "endpoint": "/webhook",
        "received_videos": len(os.listdir(RECEIVED_DIR))
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎣 Webhook Receiver Started")
    print("=" * 60)
    print("Listening for webhooks at: http://localhost:5000/webhook")
    print("Videos will be saved to:", os.path.abspath(RECEIVED_DIR))
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=5000)

