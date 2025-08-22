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


# --- Helper function to normalize Shorts links ---
def normalize_url(url: str) -> str:
    if "youtube.com/shorts/" in url:
        video_id = url.split("/")[-1].split("?")[0]
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


@app.get("/formats/")
async def get_formats(url: str):
    try:
        url = normalize_url(url)

        ydl_opts = {
            "noplaylist": True,
            "quiet": True,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                )
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

            video_formats = []
            audio_formats = []
            for f in formats:
                if f.get("vcodec") != "none" and f.get("acodec") != "none":
                    video_formats.append({
                        "format_id": f.get("format_id"),
                        "resolution": f.get("resolution", "Unknown"),
                        "ext": f.get("ext", "mp4"),
                        "format_note": f.get("format_note", "Unknown"),
                        "filesize": f.get("filesize", None),
                    })
                elif f.get("acodec") != "none" and f.get("vcodec") == "none":
                    audio_formats.append({
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext", "m4a"),
                        "format_note": f.get("format_note", "Unknown"),
                        "filesize": f.get("filesize", None),
                    })

            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
                "video_formats": video_formats,
                "audio_formats": audio_formats,
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching formats: {str(e)}")


@app.get("/download/")
def download_video(url: str, format: str = "video", format_id: str = None):
    try:
        url = normalize_url(url)
        video_id = str(uuid.uuid4())

        if format.lower() not in ["video", "audio"]:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'video' or 'audio'.")

        ydl_opts = {
            "outtmpl": f"{video_id}.%(ext)s",
            "noplaylist": True,
            "quiet": True,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/115.0.0.0 Safari/537.36"
                )
            },
        }

        if format.lower() == "video":
            if format_id:
                ydl_opts.update({
                    "format": format_id,
                    "merge_output_format": "mp4",
                })
            else:
                ydl_opts.update({
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                })
        else:  # audio
            if format_id:
                ydl_opts.update({
                    "format": format_id,
                    "extractaudio": True,
                    "audioformat": "mp3",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "bestaudio",
                    "extractaudio": True,
                    "audioformat": "mp3",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

            if format.lower() == "audio":
                downloaded_file = downloaded_file.replace(".webm", ".mp3").replace(".m4a", ".mp3")

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Download failed: file not found.")

        media_type = "audio/mpeg" if format.lower() == "audio" else "video/mp4"
        file_extension = "mp3" if format.lower() == "audio" else "mp4"
        filename = f"{info.get('title', 'media')}.{file_extension}"

        return FileResponse(
            path=downloaded_file,
            media_type=media_type,
            filename=filename,
            background=BackgroundTask(lambda: os.remove(downloaded_file) if os.path.exists(downloaded_file) else None),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
