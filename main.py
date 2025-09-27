from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
import yt_dlp
import os
import uuid
import logging

# TikTokApi import
from TikTokApi import TikTokApi

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
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
    video_id = str(uuid.uuid4())
    output_template = f"{video_id}.%(ext)s"

    ydl_opts = {
        "format": "best[height<=720]/bestvideo[height<=720]+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
        "ignoreerrors": False,
        # 'cookies_from_browser': ('chrome',),  # optional
    }

    try:
        # ---- Try yt-dlp first ----
        logger.info(f"Trying yt-dlp for {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                raise Exception("yt-dlp could not extract info")

            ext = info.get("ext", "mp4")
            downloaded_file = f"{video_id}.{ext}"

            if not os.path.exists(downloaded_file):
                possible_files = [f for f in os.listdir(".") if f.startswith(video_id)]
                if possible_files:
                    downloaded_file = possible_files[0]
                else:
                    raise Exception("Download completed but file not found")

        video_title = info.get("title", "video")
        safe_filename = "".join(c for c in video_title if c.isalnum() or c in (" ", "-", "_")).rstrip()
        safe_filename = f"{safe_filename[:50]}.mp4"

        return FileResponse(
            path=downloaded_file,
            media_type="video/mp4",
            filename=safe_filename,
            background=BackgroundTask(
                lambda: os.remove(downloaded_file) if os.path.exists(downloaded_file) else None
            ),
        )

    except Exception as e:
        logger.warning(f"yt-dlp failed, fallback to TikTokApi. Error: {str(e)}")

        # ---- Fallback: TikTokApi ----
        try:
            if "tiktok.com" not in url:
                raise HTTPException(status_code=400, detail="Unsupported platform for fallback")

            with TikTokApi() as api:
                vid = url.split("/")[-1].split("?")[0]
                video = api.video(id=vid)
                info = video.info()
                play_url = info["video"]["playAddr"]

                # instead of downloading on server, redirect to TikTok CDN link
                return RedirectResponse(url=play_url)

        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Both yt-dlp and TikTokApi failed: {str(e2)}"
            )
