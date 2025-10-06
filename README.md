# Watermark Remover API

Professional pixel-perfect watermark removal API built with FastAPI. This API processes videos to remove watermarks using advanced inpainting techniques.

## Features

- 🎯 **Pixel-Perfect Removal**: Advanced dual-algorithm inpainting removes every trace
- 🎥 **Enhanced Quality**: Output video equals or exceeds original quality (CRF 18 encoding)
- 🔊 **Audio Preserved**: Original audio/voice track remains 100% intact (320k bitrate)
- ✨ **Texture Matching**: Intelligent sampling from surrounding areas for natural look
- 🎨 **Smart Sharpening**: Restores detail lost during processing - no softness
- 🚀 **Async Processing**: Background task processing with status tracking

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure ffmpeg is installed on your system:
- **Windows**: Download from https://ffmpeg.org/download.html
- **Linux**: `sudo apt-get install ffmpeg`
- **Mac**: `brew install ffmpeg`

## Running the Server

Start the FastAPI server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Web Interface

For a user-friendly web interface, simply open `index.html` in your browser after starting the server. This provides:
- Drag & drop file upload
- Real-time progress tracking
- Video preview
- One-click download

Alternatively, use the command-line test client:

```bash
python test_client.py your_video.mp4
```

## API Documentation

Once the server is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## API Endpoints

### 1. Health Check
```bash
GET /health
```

### 2. Upload Video for Processing
```bash
POST /upload
```

**Request**: Multipart form-data with video file and optional webhook URL

**Parameters:**
- `file` (required): Video file to process
- `webhook_url` (optional): URL to receive the processed video when ready

**Example using curl (without webhook):**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your_video.mp4"
```

**Example using curl (with webhook):**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@your_video.mp4" \
  -F "webhook_url=http://localhost:5000/webhook"
```

**Example using Python requests:**
```python
import requests

url = "http://localhost:8000/upload"
files = {"file": open("your_video.mp4", "rb")}
data = {"webhook_url": "http://localhost:5000/webhook"}  # Optional
response = requests.post(url, files=files, data=data)
print(response.json())
```

**Response (without webhook):**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Video uploaded successfully. Processing started.",
  "status_url": "/status/123e4567-e89b-12d3-a456-426614174000",
  "download_url": "/download/123e4567-e89b-12d3-a456-426614174000_output.mp4"
}
```

**Response (with webhook):**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Video uploaded successfully. Processing started. Video will be sent to webhook when ready.",
  "status_url": "/status/123e4567-e89b-12d3-a456-426614174000",
  "download_url": "/download/123e4567-e89b-12d3-a456-426614174000_output.mp4",
  "webhook_url": "http://localhost:5000/webhook"
}
```

### 3. Check Processing Status
```bash
GET /status/{task_id}
```

**Example:**
```bash
curl "http://localhost:8000/status/123e4567-e89b-12d3-a456-426614174000"
```

**Response (Processing):**
```json
{
  "status": "processing",
  "progress": 45
}
```

**Response (Completed):**
```json
{
  "status": "completed",
  "progress": 100
}
```

### 4. Download Processed Video
```bash
GET /download/{filename}
```

**Example:**
```bash
curl -O "http://localhost:8000/download/123e4567-e89b-12d3-a456-426614174000_output.mp4"
```

### 5. Cleanup Files
```bash
DELETE /cleanup/{task_id}
```

Removes processed files and clears status tracking.

## Complete Workflow Examples

### Method 1: Traditional (Poll for Status)

```python
import requests
import time

# 1. Upload video
upload_url = "http://localhost:8000/upload"
files = {"file": open("video_with_watermark.mp4", "rb")}
response = requests.post(upload_url, files=files)
data = response.json()

task_id = data["task_id"]
print(f"Task ID: {task_id}")

# 2. Poll status until complete
status_url = f"http://localhost:8000/status/{task_id}"
while True:
    status_response = requests.get(status_url)
    status_data = status_response.json()
    
    print(f"Status: {status_data['status']} - Progress: {status_data.get('progress', 0)}%")
    
    if status_data["status"] == "completed":
        break
    elif status_data["status"] == "error":
        print(f"Error: {status_data.get('message', 'Unknown error')}")
        break
    
    time.sleep(2)

# 3. Download processed video
download_url = f"http://localhost:8000{data['download_url']}"
video_response = requests.get(download_url)

with open("cleaned_video.mp4", "wb") as f:
    f.write(video_response.content)

print("Video downloaded successfully!")

# 4. Optional: Cleanup
cleanup_url = f"http://localhost:8000/cleanup/{task_id}"
requests.delete(cleanup_url)
```

### Method 2: Webhook (Recommended - No Polling!)

```python
import requests

# Upload video with webhook URL
upload_url = "http://localhost:8000/upload"
files = {"file": open("video_with_watermark.mp4", "rb")}
data = {"webhook_url": "https://your-domain.com/webhook"}

response = requests.post(upload_url, files=files, data=data)
print(response.json())

# That's it! The processed video will be automatically sent to your webhook
# Your webhook will receive:
# - video file (multipart)
# - task_id
# - status
# - file_size_mb
```

**Set up a webhook receiver:**
```bash
# Run the example webhook receiver
python webhook_receiver_example.py
```

Then use `http://localhost:5000/webhook` as your webhook URL for testing.

## Directory Structure

```
.
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── uploads/            # Temporary upload directory (auto-created)
└── outputs/            # Processed video directory (auto-created)
```

## Technical Details

The watermark removal uses:
- **Navier-Stokes Inpainting**: Smooth, fluid-like reconstruction
- **Median & Gaussian Filtering**: Removes artifacts and smooths surfaces
- **Color Tone Preservation**: Samples dominant colors from surrounding areas
- **Feathered Masking**: Ultra-smooth blending for invisible seams
- **H.264 Encoding**: High-quality output (CRF 18, slow preset)
- **Audio Preservation**: Original audio track at 320k bitrate

## Notes

- Videos are processed in the background, allowing the API to handle multiple requests
- Processing time depends on video length and resolution
- Temporary files are stored in `uploads/` and `outputs/` directories
- Use the cleanup endpoint to remove files after download
- The API supports `.mp4`, `.mov`, and `.avi` formats

## Troubleshooting

**Error: "Could not open video file"**
- Ensure the video format is supported
- Check that the file is not corrupted

**Error: ffmpeg not found**
- Install ffmpeg on your system
- The API will attempt to use imageio-ffmpeg as a fallback

**Slow processing**
- Video processing is CPU-intensive
- Consider using a machine with better CPU or GPU acceleration
- Processing time scales with video length and resolution

## License

This project is provided as-is for educational and commercial use.

