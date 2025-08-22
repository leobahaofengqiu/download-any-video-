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
def download_video(url: str, format: str = "video"):
    try:
        video_id = str(uuid.uuid4())  # unique ID for file naming

        # Configure yt_dlp options based on format
        if format.lower() not in ["video", "audio"]:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'video' or 'audio'.")

        ydl_opts = {
            "outtmpl": f"{video_id}.%(ext)s",
            "noplaylist": True,  # avoid downloading playlists
            "quiet": True,
        }

        if format.lower() == "video":
            ydl_opts.update({
                "format": "bestvideo+bestaudio/best",  # best quality video
                "merge_output_format": "mp4",         # force MP4
            })
        else:  # audio
            ydl_opts.update({
                "format": "bestaudio",                # best audio quality
                "extractaudio": True,                 # extract audio
                "audioformat": "mp3",                 # convert to MP3
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",      # use ffmpeg to extract audio
                    "preferredcodec": "mp3",
                    "preferredquality": "192",        # set audio quality (192 kbps)
                }],
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

            # For audio, yt_dlp may change the extension after postprocessing
            if format.lower() == "audio":
                downloaded_file = downloaded_file.replace(".webm", ".mp3").replace(".m4a", ".mp3")

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Download failed: file not found.")

        # Metadata for response
        metadata = {
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "webpage_url": info.get("webpage_url"),
            "ext": "mp3" if format.lower() == "audio" else "mp4",
        }

        # Determine media type and filename
        media_type = "audio/mpeg" if format.lower() == "audio" else "video/mp4"
        file_extension = "mp3" if format.lower() == "audio" else "mp4"
        filename = f"{info.get('title', 'media')}.{file_extension}"

        # Return file response with cleanup
        return FileResponse(
            path=downloaded_file,
            media_type=media_type,
            filename=filename,
            background=BackgroundTask(lambda: os.remove(downloaded_file) if os.path.exists(downloaded_file) else None),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
