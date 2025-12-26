from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional


ProgressCallback = Callable[["ProgressEvent"], None]
LogCallback = Callable[["LogEvent"], None]


@dataclass
class DownloadConfig:
    """Configuration for a single yt-dlp download task."""

    url: str
    output_dir: str = "downloads"
    filename_template: str = "%(title)s.%(ext)s"
    format: str = "best"
    audio_only: bool = False
    playlist_items: Optional[str] = None
    timeout: Optional[int] = None
    retries: int = 3
    proxy: Optional[str] = None
    extra_yt_dlp_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressEvent:
    """Event object passed to progress callbacks."""

    status: Literal["downloading", "finished", "error"]
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[int] = None
    filename: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEvent:
    """Structured log event for higher level consumers."""

    level: Literal["debug", "info", "warning", "error"]
    message: str
    context: Optional[Dict[str, Any]] = None


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    filepaths: List[str]
    info: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


__all__ = [
    "DownloadConfig",
    "ProgressEvent",
    "LogEvent",
    "DownloadResult",
    "ProgressCallback",
    "LogCallback",
]


