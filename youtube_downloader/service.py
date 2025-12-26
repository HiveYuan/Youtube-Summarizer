from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Dict, List, Literal, Optional

import yt_dlp

from .models import (
    DownloadConfig,
    DownloadResult,
    LogCallback,
    LogEvent,
    ProgressCallback,
    ProgressEvent,
)


class _YtDlpLogger:
    """Adapter to route yt-dlp logs into Python logging and optional callbacks."""

    def __init__(self, logger: logging.Logger, on_log: Optional[LogCallback]) -> None:
        self._logger = logger
        self._on_log = on_log

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)
        self._emit("debug", msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)
        self._emit("info", msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)
        self._emit("warning", msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)
        self._emit("error", msg)

    def _emit(self, level: Literal["debug", "info", "warning", "error"], msg: str) -> None:
        if self._on_log is not None:
            event = LogEvent(level=level, message=msg, context=None)
            self._on_log(event)


class YouTubeDownloadService:
    """High-level service wrapper around yt-dlp."""

    def __init__(
        self,
        default_output_dir: str = "downloads",
        default_proxy: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize the service with default options."""
        self._default_output_dir = default_output_dir
        self._default_proxy = default_proxy

        if logger is None:
            logger = logging.getLogger("youtube_downloader")
            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        self._logger = logger

        # Ensure default output directory exists
        os.makedirs(self._default_output_dir, exist_ok=True)

    # ---------------------- Public synchronous API ---------------------- #

    def get_info(self, url: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """Fetch video information without downloading."""
        ydl_opts: Dict[str, Any] = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
        }

        effective_proxy = proxy or self._default_proxy
        if effective_proxy:
            ydl_opts["proxy"] = effective_proxy

        self._logger.debug("Fetching info for URL %s", url)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info

    def download(
        self,
        config: DownloadConfig,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
    ) -> DownloadResult:
        """Download content according to the provided configuration."""
        self._logger.info("Starting download for URL %s", config.url)

        # Ensure output directory exists
        output_dir = config.output_dir or self._default_output_dir
        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = self._build_yt_dlp_options(config, output_dir, on_progress, on_log)

        filepaths: List[str] = []
        info: Dict[str, Any] = {}
        errors: List[str] = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(config.url, download=True)
                # yt-dlp returns either dict or list; we try to infer file path(s) from info
                if "_filename" in info:
                    filepaths.append(info["_filename"])
                elif "requested_downloads" in info:
                    for item in info.get("requested_downloads", []):
                        path = item.get("_filename")
                        if path:
                            filepaths.append(path)

            self._logger.info("Download succeeded for URL %s", config.url)
            return DownloadResult(success=True, filepaths=filepaths, info=info, errors=[])
        except Exception as exc:  # noqa: BLE001
            msg = f"Download failed for URL {config.url}: {exc}"
            self._logger.error(msg)
            errors.append(str(exc))
            if on_log is not None:
                on_log(LogEvent(level="error", message=msg, context=None))
            return DownloadResult(success=False, filepaths=filepaths, info=info, errors=errors)

    # ---------------------- Convenience methods ---------------------- #

    def download_video(
        self,
        url: str,
        *,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
        **config_kwargs: Any,
    ) -> DownloadResult:
        """Download video with default configuration.

        Callbacks are separated from DownloadConfig to keep the config model clean.
        """
        config = DownloadConfig(
            url=url,
            output_dir=self._default_output_dir,
            **config_kwargs,
        )
        return self.download(config, on_progress=on_progress, on_log=on_log)

    def download_audio(
        self,
        url: str,
        *,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
        **config_kwargs: Any,
    ) -> DownloadResult:
        """Download audio only using yt-dlp audio extraction."""
        config_kwargs.setdefault("format", "bestaudio/best")
        config = DownloadConfig(
            url=url,
            output_dir=self._default_output_dir,
            audio_only=True,
            **config_kwargs,
        )
        return self.download(config, on_progress=on_progress, on_log=on_log)

    def download_playlist(
        self,
        url: str,
        playlist_items: Optional[str] = None,
        *,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
        **config_kwargs: Any,
    ) -> DownloadResult:
        """Download a playlist or selected items from a playlist."""
        config = DownloadConfig(
            url=url,
            output_dir=self._default_output_dir,
            playlist_items=playlist_items,
            **config_kwargs,
        )
        return self.download(config, on_progress=on_progress, on_log=on_log)

    # ---------------------- Async wrappers (future ready) ---------------------- #

    async def get_info_async(self, url: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """Async wrapper for get_info using a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_info, url, proxy)

    async def download_async(
        self,
        config: DownloadConfig,
        on_progress: Optional[ProgressCallback] = None,
        on_log: Optional[LogCallback] = None,
    ) -> DownloadResult:
        """Async wrapper for download using a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.download, config, on_progress, on_log)

    # ---------------------- Internal helpers ---------------------- #

    def _build_yt_dlp_options(
        self,
        config: DownloadConfig,
        output_dir: str,
        on_progress: Optional[ProgressCallback],
        on_log: Optional[LogCallback],
    ) -> Dict[str, Any]:
        """Map DownloadConfig and callbacks to yt-dlp options."""
        ydl_opts: Dict[str, Any] = {
            "outtmpl": os.path.join(output_dir, config.filename_template),
            "format": config.format,
            "noplaylist": config.playlist_items is None,
            "logger": _YtDlpLogger(self._logger, on_log),
            "progress_hooks": [self._make_progress_hook(on_progress)] if on_progress else [],
            "retries": config.retries,
        }

        # Apply proxy
        effective_proxy = config.proxy or self._default_proxy
        if effective_proxy:
            ydl_opts["proxy"] = effective_proxy

        # Timeout
        if config.timeout is not None:
            ydl_opts["socket_timeout"] = config.timeout

        # Playlist selection
        if config.playlist_items is not None:
            ydl_opts["playlist_items"] = config.playlist_items

        # Audio only mode via postprocessors
        if config.audio_only:
            # Extract best available audio and convert to mp3 by default
            ydl_opts.setdefault("format", "bestaudio/best")
            ydl_opts.setdefault("postprocessors", []).append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            )

        # Merge extra user-defined options last
        ydl_opts.update(config.extra_yt_dlp_options)

        return ydl_opts

    def _make_progress_hook(self, on_progress: Optional[ProgressCallback]) -> Callable[[Dict[str, Any]], None]:
        """Create a yt-dlp progress hook that forwards events to ProgressCallback."""

        def _hook(status: Dict[str, Any]) -> None:
            if on_progress is None:
                return

            event_status: Literal["downloading", "finished", "error"]
            raw_status = status.get("status")
            if raw_status == "downloading":
                event_status = "downloading"
            elif raw_status == "finished":
                event_status = "finished"
            else:
                # yt-dlp may not have explicit error in progress hooks; we reserve this
                event_status = "error"

            event = ProgressEvent(
                status=event_status,
                downloaded_bytes=status.get("downloaded_bytes"),
                total_bytes=status.get("total_bytes") or status.get("total_bytes_estimate"),
                speed=status.get("speed"),
                eta=status.get("eta"),
                filename=status.get("filename") or status.get("info_dict", {}).get("filename"),
                raw=status,
            )
            on_progress(event)

        return _hook


