from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import yt_dlp
import os
import uuid

app = FastAPI(title="Universal Video Downloader API 🚀")


@app.get("/")
def root():
    return {"message": "Universal Video Downloader API is running 🚀"}


@app.get("/download/")
def download_video(url: str):
    try:
        video_id = str(uuid.uuid4())  # unique ID for file naming

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",  # best quality
            "merge_output_format": "mp4",          # force mp4
            "outtmpl": f"{video_id}.%(ext)s",
            "noplaylist": True,                    # avoid whole playlists
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Download failed: file not found.")

        # Metadata for response (can be returned if you want JSON instead of direct file)
        metadata = {
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "webpage_url": info.get("webpage_url"),
            "ext": info.get("ext"),
        }

        # Return video file as response, auto-deleting after serving
        return FileResponse(
            path=downloaded_file,
            media_type="video/mp4",
            filename=f"{info.get('title','video')}.mp4",
            background=BackgroundTask(lambda: os.remove(downloaded_file) if os.path.exists(downloaded_file) else None),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
