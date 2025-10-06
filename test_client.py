"""
Simple test client for the Watermark Remover API
Usage: python test_client.py <video_file_path>
"""

import requests
import time
import sys
import os

API_BASE_URL = "http://localhost:8000"


def upload_video(video_path):
    """Upload video to the API"""
    if not os.path.exists(video_path):
        print(f"Error: File '{video_path}' not found")
        return None
    
    print(f"Uploading {video_path}...")
    
    with open(video_path, "rb") as f:
        files = {"file": f}
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Upload successful! Task ID: {data['task_id']}")
        return data
    else:
        print(f"✗ Upload failed: {response.text}")
        return None


def check_status(task_id):
    """Check processing status"""
    response = requests.get(f"{API_BASE_URL}/status/{task_id}")
    if response.status_code == 200:
        return response.json()
    return None


def download_video(filename, output_path):
    """Download processed video"""
    print(f"Downloading to {output_path}...")
    response = requests.get(f"{API_BASE_URL}/download/{filename}")
    
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"✓ Downloaded successfully to {output_path}")
        return True
    else:
        print(f"✗ Download failed: {response.text}")
        return False


def cleanup(task_id):
    """Cleanup files on server"""
    response = requests.delete(f"{API_BASE_URL}/cleanup/{task_id}")
    if response.status_code == 200:
        print("✓ Server files cleaned up")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <video_file_path>")
        print("Example: python test_client.py my_video.mp4")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print("Error: API is not responding. Make sure the server is running.")
            print("Run: python main.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API. Make sure the server is running.")
        print("Run: python main.py")
        sys.exit(1)
    
    print("=" * 60)
    print("Watermark Remover API Test Client")
    print("=" * 60)
    
    # Upload video
    upload_data = upload_video(video_path)
    if not upload_data:
        sys.exit(1)
    
    task_id = upload_data["task_id"]
    filename = upload_data["download_url"].split("/")[-1]
    
    # Poll status
    print("\nProcessing video...")
    last_progress = -1
    
    while True:
        status_data = check_status(task_id)
        
        if not status_data:
            print("✗ Failed to get status")
            break
        
        status = status_data.get("status")
        progress = status_data.get("progress", 0)
        
        # Only print if progress changed
        if progress != last_progress:
            if status == "processing":
                print(f"Progress: {progress}%", end="\r")
            elif status == "adding_audio":
                print("\nAdding audio track...")
            last_progress = progress
        
        if status == "completed":
            print("\n✓ Processing completed!")
            break
        elif status == "error":
            print(f"\n✗ Processing error: {status_data.get('message', 'Unknown error')}")
            sys.exit(1)
        
        time.sleep(1)
    
    # Download video
    output_filename = f"cleaned_{os.path.basename(video_path)}"
    if download_video(filename, output_filename):
        file_size = os.path.getsize(output_filename) / (1024 * 1024)  # MB
        print(f"File size: {file_size:.2f} MB")
    
    # Cleanup
    print("\nCleaning up server files...")
    cleanup(task_id)
    
    print("\n" + "=" * 60)
    print("Done! ✨")
    print("=" * 60)


if __name__ == "__main__":
    main()

