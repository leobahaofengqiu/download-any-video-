from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
import yt_dlp
import os
import uuid
import logging
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Universal Video Downloader API 🚀")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Universal Video Downloader API is running 🚀"}

@app.get("/download/")
def download_video(url: str):
    try:
        logger.info(f"Download request for URL: {url}")
        
        video_id = str(uuid.uuid4())
        output_template = f"{video_id}.%(ext)s"
        
        ydl_opts = {
            "format": "best[height<=720]/bestvideo[height<=720]+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
            "extractaudio": False,
            "audioformat": "mp3",
            "ignoreerrors": False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Extracting video info...")
            info = ydl.extract_info(url, download=True)
            
            if not info:
                raise HTTPException(status_code=400, detail="Could not extract video information")
            
            video_title = info.get("title", "video")
            ext = info.get("ext", "mp4")
            downloaded_file = f"{video_id}.{ext}"
            
            if not os.path.exists(downloaded_file):
                possible_files = [f for f in os.listdir(".") if f.startswith(video_id)]
                if possible_files:
                    downloaded_file = possible_files[0]
                else:
                    raise HTTPException(status_code=500, detail="Download completed but file not found")
        
        logger.info(f"Download successful: {downloaded_file}")
        
        safe_filename = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_filename = f"{safe_filename[:50]}.mp4"
        
        return FileResponse(
            path=downloaded_file,
            media_type="video/mp4",
            filename=safe_filename,
            background=BackgroundTask(
                lambda: os.remove(downloaded_file) if os.path.exists(downloaded_file) else None
            ),
        )
        
    except yt_dlp.DownloadError as e:
        logger.error(f"yt-dlp download error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# 🚀 Railway fix: run with assigned PORT
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
