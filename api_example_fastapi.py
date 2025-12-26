from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from pydantic import BaseModel

from youtube_downloader import DownloadConfig, YouTubeDownloadService


app = FastAPI()
service = YouTubeDownloadService(default_output_dir="downloads")


class DownloadRequest(BaseModel):
    """Request body for download endpoints."""

    url: str
    audio_only: bool = False
    playlist_items: str | None = None
    format: str | None = None


@app.get("/info")
def get_info(url: str) -> Dict[str, Any]:
    """Return metadata for a YouTube URL."""
    return service.get_info(url)


@app.post("/download")
def download(req: DownloadRequest) -> Dict[str, Any]:
    """Download a video or audio, returning basic result info."""
    config = DownloadConfig(
        url=req.url,
        audio_only=req.audio_only,
        playlist_items=req.playlist_items,
        format=req.format or "best",
    )
    result = service.download(config)
    return {
        "success": result.success,
        "files": result.filepaths,
        "errors": result.errors,
    }


