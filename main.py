from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import yt_dlp
import cv2
import subprocess
import os
import uuid

app = FastAPI(title="Universal Video Downloader API 🚀")


@app.get("/")
def root():
    return {"message": "Universal Video Downloader API is running 🚀"}


@app.get("/download/")
def download_video(url: str):
    try:
        # Unique ID for filenames
        video_id = str(uuid.uuid4())
        input_file = f"{video_id}.%(ext)s"

        # yt-dlp options
        ydl_opts = {
            "format": "mp4/best",
            "outtmpl": input_file,
        }

        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Download failed: file not found.")

        # OpenCV: take first frame to detect watermark
        cap = cv2.VideoCapture(downloaded_file)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise HTTPException(status_code=500, detail="Could not read video for watermark detection.")

        # Convert frame to grayscale and threshold
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY)

        # Find contours (possible watermark/logos)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Default watermark area = None
        x, y, w, h = 0, 0, 0, 0
        if contours:
            # Pick largest bright region (likely watermark)
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)

        # Output file
        output_file = f"{video_id}_clean.mp4"

        if w > 0 and h > 0:
            # Run ffmpeg with delogo filter
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", downloaded_file,
                "-vf", f"delogo=x={x}:y={y}:w={w}:h={h}:show=0",
                "-c:a", "copy",
                "-y",  # overwrite if exists
                output_file
            ]
        else:
            # If no watermark detected, just copy original
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", downloaded_file,
                "-c", "copy",
                "-y",
                output_file
            ]

        subprocess.run(ffmpeg_cmd, check=True)

        # Remove original file
        os.remove(downloaded_file)

        # Return clean file
        return FileResponse(
            path=output_file,
            media_type="video/mp4",
            filename=f"{info.get('title','video')}_clean.mp4",
            background=BackgroundTask(lambda: os.remove(output_file))
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
