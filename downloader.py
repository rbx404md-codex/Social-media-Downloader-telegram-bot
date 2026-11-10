import os
import uuid
import asyncio
import yt_dlp
from config import DOWNLOAD_DIR

# Simple in-memory cache: result_id -> extracted info dict
# In production, swap this for Redis so it survives restarts / scales across workers.
LINK_CACHE: dict[str, dict] = {}


def detect_platform(url: str) -> str:
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    if "instagram.com" in url:
        return "Instagram"
    if "tiktok.com" in url:
        return "TikTok"
    if "twitter.com" in url or "x.com" in url:
        return "Twitter/X"
    if "facebook.com" in url or "fb.watch" in url:
        return "Facebook"
    if "pinterest.com" in url:
        return "Pinterest"
    return "Unknown"


async def extract_info(url: str) -> dict:
    """Run yt-dlp extract_info in a thread (it's blocking)."""
    loop = asyncio.get_event_loop()

    def _extract():
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await loop.run_in_executor(None, _extract)

    result_id = str(uuid.uuid4())[:8]
    LINK_CACHE[result_id] = {"url": url, "info": info}
    return {"result_id": result_id, "info": info}


def build_quality_options(info: dict) -> list:
    """Turn yt-dlp formats into simplified label/format_id pairs."""
    seen_heights = set()
    options = []
    formats = info.get("formats", [])
    for f in formats:
        height = f.get("height")
        if height and height not in seen_heights and f.get("vcodec") != "none":
            seen_heights.add(height)
            options.append({"label": f"{height}p", "format_id": str(height)})
    options.sort(key=lambda x: int(x["label"].replace("p", "")), reverse=True)
    return options[:5] if options else [{"label": "Best Available", "format_id": "best"}]


async def download_media(result_id: str, format_choice: str, progress_hook=None) -> str:
    """Download the chosen format/quality; returns local file path."""
    cached = LINK_CACHE.get(result_id)
    if not cached:
        raise ValueError("Link expired, please resend it.")

    url = cached["url"]
    loop = asyncio.get_event_loop()
    output_template = os.path.join(DOWNLOAD_DIR, f"{result_id}_%(title).50s.%(ext)s")

    def _download():
        if format_choice == "audio":
            fmt = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            fmt = (
                f"bestvideo[height<={format_choice}]+bestaudio/best"
                if format_choice != "best"
                else "best"
            )
            postprocessors = []

        ydl_opts = {
            "format": fmt,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "postprocessors": postprocessors,
        }
        if progress_hook:
            ydl_opts["progress_hooks"] = [progress_hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)
            if format_choice == "audio":
                filepath = os.path.splitext(filepath)[0] + ".mp3"
            return filepath

    filepath = await loop.run_in_executor(None, _download)
    return filepath


def cleanup_file(filepath: str):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass
