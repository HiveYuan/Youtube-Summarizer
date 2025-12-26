from __future__ import annotations

import logging
from typing import Any

from youtube_downloader import (
    DownloadConfig,
    LogEvent,
    ProgressEvent,
    YouTubeDownloadService,
)


def print_progress(event: ProgressEvent) -> None:
    """Simple progress callback for demonstration."""
    if event.status == "downloading":
        pct: float | None = None
        if event.total_bytes and event.downloaded_bytes:
            pct = event.downloaded_bytes / event.total_bytes * 100
        msg_parts: list[str] = ["Downloading"]
        if event.filename:
            msg_parts.append(f"{event.filename}")
        if pct is not None:
            msg_parts.append(f"{pct:.1f}%")
        print(" - ".join(msg_parts))
    elif event.status == "finished":
        print(f"Finished: {event.filename or ''}")
    else:
        print(f"Status: {event.status}")


def print_log(event: LogEvent) -> None:
    """Simple log callback for demonstration."""
    print(f"[{event.level.upper()}] {event.message}")


def main() -> None:
    """Example entry point to demonstrate service usage."""
    logging.basicConfig(level=logging.INFO)

    service = YouTubeDownloadService(default_output_dir="downloads")

    # Example URL placeholder, replace with a real YouTube URL when using.
    url = "https://www.youtube.com/watch?v=svnWHr7539g"

    # Basic video download using convenience method.
    result_video = service.download_video(url, on_progress=print_progress, on_log=print_log)  # type: ignore[arg-type]
    print("Video download success:", result_video.success)
    print("Files:", result_video.filepaths)

    # Audio-only download using explicit config.
    config = DownloadConfig(url=url, output_dir="downloads", audio_only=True)
    result_audio = service.download(config, on_progress=print_progress, on_log=print_log)
    print("Audio download success:", result_audio.success)
    print("Files:", result_audio.filepaths)


if __name__ == "__main__":
    main()


