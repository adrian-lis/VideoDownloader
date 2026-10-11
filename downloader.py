#!/usr/bin/env python3
"""
Video Downloader

Requirements:
    Python 3.10+
    yt-dlp

Optional dependency:
    FFmpeg

Windows:
    Uses ./ffmpeg/ffmpeg.exe when available.

Linux:
    Uses FFmpeg installed in PATH.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp is not installed.")
    print()
    print("Install it with:")
    print("    python -m pip install -U yt-dlp")
    input("\nPress Enter to exit...")
    raise SystemExit(1)


# --------------------------------------------------
# Paths and defaults
# --------------------------------------------------

APP_DIR = Path.home() / ".video_downloader"
HISTORY_FILE = APP_DIR / "history.json"
CONFIG_FILE = APP_DIR / "config.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"

DEFAULT_SETTINGS: dict[str, Any] = {
    "download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "format": "mp4",
    "retries": 10,
    "fragment_retries": 10,
    "socket_timeout": 30,
    "overwrite": False,
    "show_progress": True,
}

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


# --------------------------------------------------
# Terminal and banner
# --------------------------------------------------

def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def terminal_width() -> int:
    try:
        return max(60, shutil.get_terminal_size((100, 24)).columns)
    except OSError:
        return 100


def print_banner() -> None:
    width = terminal_width()

    banner = [
        r" _    ___     __              ____                      __                __         ",
        r"| |  / (_)___/ /__  ____     / __ \____ _      ______  / /___  ____ _____/ /__  _____",
        r"| | / / / __  / _ \/ __ \   / / / / __ \ | /| / / __ \/ / __ \/ __ `/ __  / _ \/ ___/",
        r"| |/ / / /_/ /  __/ /_/ /  / /_/ / /_/ / |/ |/ / / / / / /_/ / /_/ / /_/ /  __/ /    ",
        r"|___/_/\__,_/\___/\____/  /_____/\____/|__/|__/_/ /_/_/\____/\__,_/\__,_/\___/_/     ",
        r"",
    ]

    print("=" * width)
    for line in banner:
        print(line.center(width))

    print("=" * width)


def print_header(title: str = "MENU") -> None:
    print_banner()
    print()
    print(title.center(terminal_width()))
    print("-" * terminal_width())


def pause(message: str = "Press Enter to continue...") -> None:
    input(f"\n  {message}")


def show_message(
    title: str,
    message: str,
    *,
    wait: bool = True,
) -> None:
    clear_screen()
    print_header(title)
    print()
    print(f"  {message}")
    print()

    if wait:
        pause()


# --------------------------------------------------
# Configuration
# --------------------------------------------------

def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    ensure_app_dir()
    settings = DEFAULT_SETTINGS.copy()

    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

            if isinstance(saved, dict):
                for key in DEFAULT_SETTINGS:
                    if key in saved:
                        settings[key] = saved[key]

        except (OSError, json.JSONDecodeError):
            pass

    if settings.get("format") not in {"mp4", "best"}:
        settings["format"] = "mp4"

    for key, default in (
        ("retries", 10),
        ("fragment_retries", 10),
        ("socket_timeout", 30),
    ):
        try:
            settings[key] = max(1, min(100, int(settings[key])))
        except (TypeError, ValueError):
            settings[key] = default

    for key in ("overwrite", "show_progress"):
        settings[key] = bool(settings[key])

    try:
        download_dir = Path(str(settings["download_dir"])).expanduser()
        settings["download_dir"] = str(download_dir)
    except (TypeError, ValueError):
        settings["download_dir"] = str(DEFAULT_DOWNLOAD_DIR)

    return settings


def save_settings(settings: dict[str, Any]) -> None:
    ensure_app_dir()

    try:
        CONFIG_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"\n  Could not save settings: {exc}")


def reset_settings() -> dict[str, Any]:
    settings = DEFAULT_SETTINGS.copy()
    save_settings(settings)
    return settings


# --------------------------------------------------
# Download history
# --------------------------------------------------

def load_history() -> list[dict[str, Any]]:
    ensure_app_dir()

    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_history(history: list[dict[str, Any]]) -> None:
    ensure_app_dir()

    try:
        HISTORY_FILE.write_text(
            json.dumps(history[-500:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def add_history(
    history: list[dict[str, Any]],
    *,
    url: str,
    title: str,
    output: str,
    status: str,
) -> None:
    history.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
        "title": title,
        "output": output,
        "status": status,
    })
    save_history(history)


def clear_history(history: list[dict[str, Any]]) -> None:
    clear_screen()
    print_header("CLEAR DOWNLOAD HISTORY")
    print()

    if not history:
        print("  The download history is already empty.")
        pause()
        return

    print(f"  Entries to delete: {len(history)}")
    print()
    print("  This only deletes the history file contents.")
    print("  Downloaded videos will not be deleted.")
    print()

    choice = input("  Clear all history? (y/N): ").strip().lower()

    if choice not in {"y", "yes"}:
        print("\n  Operation cancelled.")
        pause()
        return

    history.clear()
    save_history(history)

    clear_screen()
    print_header("HISTORY CLEARED")
    print()
    print("  Download history has been cleared.")
    pause()


def show_history(history: list[dict[str, Any]]) -> None:
    while True:
        clear_screen()
        print_header("DOWNLOAD HISTORY")
        print()

        if not history:
            print("  No downloads yet.")
        else:
            print(f"  Total entries: {len(history)}")
            print()

            for item in reversed(history[-50:]):
                status = item.get("status", "UNKNOWN")
                date = item.get("date", "")
                title = item.get("title", "Unknown")
                output = item.get("output", "")

                print(f"  [{status}] {date}")
                print(f"  {title}")

                if output:
                    print(f"  {output}")

                print()

        print("  1. Clear history")
        print("  0. Back")
        print()

        choice = input("  Select: ").strip()

        if choice == "1":
            clear_history(history)
        elif choice == "0":
            return


# --------------------------------------------------
# Formatting
# --------------------------------------------------

def sanitize_filename(name: str) -> str:
    name = INVALID_FILENAME_CHARS.sub("_", name)
    name = re.sub(r"\s+", " ", name)
    name = name.strip(" .")

    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    if name.upper() in reserved_names:
        name = f"_{name}"

    if not name:
        name = "video"

    return name[:180].rstrip(" .") or "video"


def format_bytes(value: float | int | None) -> str:
    if value is None:
        return "Unknown"

    value = float(value)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            if unit == "B":
                return f"{value:.0f} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024

    return "Unknown"


def format_seconds(seconds: float | int | None) -> str:
    if seconds is None:
        return "--:--"

    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def progress_bar(percent: float, width: int = 44) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = int(width * percent / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def clean_error(exc: Exception) -> str:
    message = ANSI_ESCAPE.sub("", str(exc)).strip()

    if not message:
        return exc.__class__.__name__

    if "ffmpeg" in message.lower():
        return (
            "FFmpeg is required for this download. "
            "Install FFmpeg or provide ffmpeg/ffmpeg.exe on Windows."
        )

    return message


# --------------------------------------------------
# FFmpeg
# --------------------------------------------------

def get_ffmpeg_path() -> str | None:
    if os.name == "nt":
        local_ffmpeg = (
            Path(__file__).resolve().parent
            / "ffmpeg"
            / "ffmpeg.exe"
        )

        if local_ffmpeg.is_file():
            return str(local_ffmpeg)

    return shutil.which("ffmpeg")


def check_ffmpeg() -> bool:
    return get_ffmpeg_path() is not None


# --------------------------------------------------
# Logging
# --------------------------------------------------

class SilentLogger:
    """Prevent yt-dlp from printing its own terminal output."""

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


# --------------------------------------------------
# Progress display
# --------------------------------------------------

class TerminalProgress:
    SPINNER = "|/-\\"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.started = time.monotonic()
        self.last_draw = 0.0
        self.current_url = ""
        self.title = ""
        self.percent = 0.0
        self.downloaded = 0
        self.total = 0
        self.speed = 0
        self.eta = None
        self.status = "Starting..."
        self.spinner_index = 0

    def set_url(self, url: str) -> None:
        self.current_url = url

    def set_title(self, title: str) -> None:
        self.title = title

    def update(
        self,
        data: dict[str, Any],
        force: bool = False,
    ) -> None:
        if not self.enabled:
            return

        now = time.monotonic()

        if not force and now - self.last_draw < 0.1:
            return

        self.last_draw = now
        self.spinner_index = (
            self.spinner_index + 1
        ) % len(self.SPINNER)

        status = data.get("status")

        if status == "downloading":
            self.downloaded = data.get("downloaded_bytes") or 0
            self.total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
                or 0
            )
            self.speed = data.get("speed") or 0
            self.eta = data.get("eta")

            if self.total:
                self.percent = self.downloaded / self.total * 100
            else:
                raw_percent = str(
                    data.get("_percent_str", "0%")
                ).strip("% ")

                try:
                    self.percent = float(raw_percent)
                except ValueError:
                    self.percent = 0.0

            self.status = "Downloading"

        elif status == "finished":
            self.percent = 100
            self.status = "Finalizing"

        elif status == "error":
            self.status = "Error"

        self.draw()

    def draw(self) -> None:
        if not self.enabled:
            return

        width = terminal_width()
        bar_width = min(52, max(24, width - 42))
        elapsed = time.monotonic() - self.started
        spinner = self.SPINNER[self.spinner_index]

        lines = [
            f"  {spinner}  {self.title or 'Video'}",
            f"  URL: {self.current_url}",
            "",
            (
                f"  {progress_bar(self.percent, bar_width)}"
                f"  {self.percent:6.1f}%"
            ),
            (
                f"  {format_bytes(self.downloaded)} / "
                f"{format_bytes(self.total) if self.total else 'Unknown'}"
                f"   {format_bytes(self.speed)}/s"
                f"   ETA {format_seconds(self.eta)}"
                f"   Elapsed {format_seconds(elapsed)}"
            ),
            f"  Status: {self.status}",
        ]

        clear_screen()
        print_header()
        print()
        print("\n".join(line[:width] for line in lines))
        print()

    def finish(
        self,
        title: str,
        output: str | None,
        success: bool,
    ) -> None:
        self.title = title
        self.percent = 100 if success else self.percent
        self.status = "Completed" if success else "Failed"

        if self.enabled:
            self.draw()
        else:
            print(f"\n  {title}: {self.status}")

        if output:
            print(f"  Output: {output}")

        print()


# --------------------------------------------------
# Output file detection
# --------------------------------------------------

def find_final_output(
    directory: Path,
    safe_title: str,
    playlist_index: int | None = None,
) -> Path | None:
    prefix = f"{playlist_index}-" if playlist_index is not None else ""

    candidates = sorted(
        directory.glob(f"{prefix}{safe_title}.*"),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
    )

    candidates = [
        path
        for path in candidates
        if not path.name.endswith((".part", ".ytdl", ".temp"))
    ]

    return candidates[-1] if candidates else None


# --------------------------------------------------
# Downloader
# --------------------------------------------------

class Downloader:
    def __init__(
        self,
        settings: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> None:
        self.settings = settings
        self.history = history
        self.download_dir = Path(
            str(settings["download_dir"])
        ).expanduser()
        self.progress = TerminalProgress(
            enabled=settings["show_progress"]
        )

    def base_options(self) -> dict[str, Any]:
        if self.settings["format"] == "mp4":
            format_selector = (
                "bv*[ext=mp4]+ba[ext=m4a]/"
                "b[ext=mp4]/"
                "bv*+ba/"
                "b"
            )
        else:
            format_selector = "bv*+ba/b"

        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "ignoreerrors": False,
            "continuedl": True,
            "overwrites": self.settings["overwrite"],
            "retries": self.settings["retries"],
            "fragment_retries": self.settings["fragment_retries"],
            "socket_timeout": self.settings["socket_timeout"],
            "file_access_retries": self.settings["retries"],
            "extractor_retries": self.settings["retries"],
            "concurrent_fragment_downloads": 1,
            "progress_hooks": [self.progress_hook],
            "postprocessor_hooks": [self.postprocessor_hook],
            "logger": SilentLogger(),
            "format": format_selector,
            "merge_output_format": "mp4",
        }

        ffmpeg_path = get_ffmpeg_path()

        if ffmpeg_path:
            options["ffmpeg_location"] = ffmpeg_path

        return options

    def progress_hook(self, data: dict[str, Any]) -> None:
        self.progress.update(data)

    def postprocessor_hook(self, data: dict[str, Any]) -> None:
        if data.get("status") == "started":
            self.progress.status = "Processing"
            self.progress.draw()
        elif data.get("status") == "finished":
            self.progress.status = "Finalizing"
            self.progress.draw()

    def download_single(
        self,
        url: str,
        *,
        output_dir: Path | None = None,
        playlist_index: int | None = None,
    ) -> bool:
        output_dir = output_dir or self.download_dir

        self.progress = TerminalProgress(
            enabled=self.settings["show_progress"]
        )
        self.progress.set_url(url)

        info_options = self.base_options()
        info_options.update({
            "skip_download": True,
            "extract_flat": True,
        })

        try:
            with yt_dlp.YoutubeDL(info_options) as ydl:
                info = ydl.extract_info(url, download=False)

        except KeyboardInterrupt:
            raise

        except Exception as exc:
            show_message(
                "DOWNLOAD ERROR",
                f"Could not read URL:\n\n  {url}\n\n"
                f"  Error: {clean_error(exc)}",
                wait=False,
            )

            add_history(
                self.history,
                url=url,
                title=url,
                output="",
                status="ERROR",
            )
            return False

        if not info:
            print("  No downloadable media was found.")
            add_history(
                self.history,
                url=url,
                title=url,
                output="",
                status="ERROR",
            )
            return False

        if info.get("_type") == "playlist":
            return self.download_playlist(url, info)

        title = str(info.get("title") or "video")
        safe_title = sanitize_filename(title)
        self.progress.set_title(title)

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            if playlist_index is not None:
                filename = f"{playlist_index}-{safe_title}.%(ext)s"
            else:
                filename = f"{safe_title}.%(ext)s"

            options = self.base_options()
            options.update({
                "outtmpl": str(output_dir / filename),
                "noplaylist": True,
            })

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            output_path = find_final_output(
                output_dir,
                safe_title,
                playlist_index,
            )

            output_string = (
                str(output_path)
                if output_path
                else str(output_dir)
            )

            self.progress.finish(title, output_string, True)

            add_history(
                self.history,
                url=url,
                title=title,
                output=output_string,
                status="OK",
            )
            return True

        except KeyboardInterrupt:
            self.progress.status = "Cancelled"
            self.progress.draw()
            print("  Download cancelled.")

            add_history(
                self.history,
                url=url,
                title=title,
                output=str(output_dir),
                status="CANCELLED",
            )
            return False

        except Exception as exc:
            self.progress.finish(title, None, False)
            print(f"  Error: {clean_error(exc)}")

            add_history(
                self.history,
                url=url,
                title=title,
                output=str(output_dir),
                status="ERROR",
            )
            return False

    def download_playlist(
        self,
        url: str,
        info: dict[str, Any] | None = None,
    ) -> bool:
        if info is None:
            options = self.base_options()
            options.update({
                "skip_download": True,
                "extract_flat": True,
            })

            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=False)

            except KeyboardInterrupt:
                raise

            except Exception as exc:
                show_message(
                    "PLAYLIST ERROR",
                    f"Could not read playlist:\n\n  {url}\n\n"
                    f"  Error: {clean_error(exc)}",
                    wait=False,
                )
                return False

        if not info:
            return False

        playlist_title = str(info.get("title") or "Playlist")
        folder_name = sanitize_filename(playlist_title)
        playlist_dir = self.download_dir / folder_name

        try:
            playlist_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            show_message(
                "PLAYLIST ERROR",
                f"Could not create directory:\n\n  {playlist_dir}\n\n"
                f"  Error: {exc}",
            )
            return False

        entries = [
            entry
            for entry in (info.get("entries") or [])
            if entry
        ]

        if not entries:
            show_message(
                "PLAYLIST",
                "The playlist contains no downloadable videos.",
            )
            return False

        clear_screen()
        print_header("PLAYLIST DOWNLOAD")
        print()
        print(f"  Playlist: {playlist_title}")
        print(f"  Videos:   {len(entries)}")
        print(f"  Folder:   {playlist_dir}")
        print()

        success_count = 0

        for number, entry in enumerate(entries, start=1):
            entry_url = entry.get("webpage_url") or entry.get("url")

            if not entry_url:
                continue

            if not str(entry_url).startswith(("http://", "https://")):
                extractor = (
                    entry.get("ie_key")
                    or entry.get("extractor_key")
                    or ""
                )

                if "youtube" in str(extractor).lower():
                    entry_url = (
                        "https://www.youtube.com/watch?v="
                        f"{entry_url}"
                    )
                else:
                    continue

            if self.download_single(
                str(entry_url),
                output_dir=playlist_dir,
                playlist_index=number,
            ):
                success_count += 1

        clear_screen()
        print_header("PLAYLIST COMPLETED")
        print()
        print(f"  Playlist:  {playlist_title}")
        print(f"  Completed: {success_count}/{len(entries)}")
        print(f"  Folder:    {playlist_dir}")
        print()

        add_history(
            self.history,
            url=url,
            title=playlist_title,
            output=str(playlist_dir),
            status=(
                "OK"
                if success_count == len(entries)
                else "PARTIAL"
            ),
        )

        return success_count == len(entries)


# --------------------------------------------------
# Download input
# --------------------------------------------------

def collect_urls() -> list[str]:
    clear_screen()
    print_header("NEW DOWNLOAD")
    print()
    print("  Enter one or more video or playlist URLs.")
    print("  Separate multiple URLs with spaces.")
    print("  Press Enter on an empty line to cancel.")
    print()

    raw = input("  URLs: ").strip()

    if not raw:
        return []

    return [
        item.strip().strip("<>\"'")
        for item in raw.split()
        if item.strip()
    ]


def start_download(
    settings: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    urls = collect_urls()

    if not urls:
        return

    downloader = Downloader(settings, history)

    for url in urls:
        if not re.match(r"^https?://", url, re.IGNORECASE):
            show_message(
                "INVALID URL",
                f"Invalid URL:\n\n  {url}",
            )
            continue

        try:
            options = downloader.base_options()
            options.update({
                "skip_download": True,
                "extract_flat": True,
            })

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                show_message(
                    "DOWNLOAD ERROR",
                    f"No downloadable media was found:\n\n  {url}",
                )
                continue

            if info.get("_type") == "playlist":
                downloader.download_playlist(url, info)
            else:
                downloader.download_single(
                    url,
                    output_dir=downloader.download_dir,
                )

        except KeyboardInterrupt:
            clear_screen()
            print_header()
            print()
            print("  Operation cancelled.")
            break

        except Exception as exc:
            show_message(
                "DOWNLOAD ERROR",
                f"Error:\n\n  {clean_error(exc)}",
            )

    print("  All requested URLs have been processed.")


# --------------------------------------------------
# Settings menu
# --------------------------------------------------

def choose_download_directory(
    settings: dict[str, Any],
) -> None:
    current = Path(str(settings["download_dir"])).expanduser()

    clear_screen()
    print_header("DOWNLOAD DIRECTORY")
    print()
    print(f"  Current directory: {current}")
    print()
    print("  Enter a new directory, or press Enter to keep the current one.")
    print()

    value = input("  Directory: ").strip().strip('"')

    if not value:
        return

    path = Path(value).expanduser()

    try:
        path.mkdir(parents=True, exist_ok=True)
        settings["download_dir"] = str(path.resolve())
        save_settings(settings)

        print("\n  Download directory updated.")

    except OSError as exc:
        print(f"\n  Could not use directory: {exc}")

    pause()


def edit_number_setting(
    settings: dict[str, Any],
    key: str,
    title: str,
    minimum: int,
    maximum: int,
) -> None:
    current = settings[key]

    clear_screen()
    print_header(title)
    print()
    print(f"  Current value: {current}")
    print(f"  Allowed range: {minimum}-{maximum}")
    print()

    value = input("  New value (Enter to cancel): ").strip()

    if not value:
        return

    try:
        number = int(value)

        if not minimum <= number <= maximum:
            raise ValueError

        settings[key] = number
        save_settings(settings)
        print("\n  Setting updated.")

    except ValueError:
        print("\n  Invalid value. No changes were made.")

    pause()


def show_settings(settings: dict[str, Any]) -> None:
    while True:
        clear_screen()
        print_header("SETTINGS")
        print()
        print(f"  1. Download directory")
        print(f"     {settings['download_dir']}")
        print()
        print(
            f"  2. Format preference: "
            f"{'MP4 preferred' if settings['format'] == 'mp4' else 'Best available'}"
        )
        print(
            f"  3. Download retries: {settings['retries']}"
        )
        print(
            f"  4. Fragment retries: {settings['fragment_retries']}"
        )
        print(
            f"  5. Socket timeout: {settings['socket_timeout']} seconds"
        )
        print(
            f"  6. Overwrite existing files: "
            f"{'Yes' if settings['overwrite'] else 'No'}"
        )
        print(
            f"  7. Progress display: "
            f"{'Enabled' if settings['show_progress'] else 'Disabled'}"
        )
        print()
        print("  8. Reset settings to defaults")
        print("  0. Back")
        print()

        choice = input("  Select: ").strip()

        if choice == "1":
            choose_download_directory(settings)

        elif choice == "2":
            settings["format"] = (
                "best" if settings["format"] == "mp4" else "mp4"
            )
            save_settings(settings)

        elif choice == "3":
            edit_number_setting(
                settings,
                "retries",
                "DOWNLOAD RETRIES",
                1,
                100,
            )

        elif choice == "4":
            edit_number_setting(
                settings,
                "fragment_retries",
                "FRAGMENT RETRIES",
                1,
                100,
            )

        elif choice == "5":
            edit_number_setting(
                settings,
                "socket_timeout",
                "SOCKET TIMEOUT",
                5,
                300,
            )

        elif choice == "6":
            settings["overwrite"] = not settings["overwrite"]
            save_settings(settings)

        elif choice == "7":
            settings["show_progress"] = not settings["show_progress"]
            save_settings(settings)

        elif choice == "8":
            clear_screen()
            print_header("RESET SETTINGS")
            print()
            print("  Restore all settings to their default values?")
            print()
            choice = input("  Confirm (y/N): ").strip().lower()

            if choice in {"y", "yes"}:
                settings.clear()
                settings.update(reset_settings())
                print("\n  Settings restored.")

            pause()

        elif choice == "0":
            return


# --------------------------------------------------
# Main menu
# --------------------------------------------------

def main() -> None:
    ensure_app_dir()

    settings = load_settings()
    history = load_history()

    download_dir = Path(
        str(settings["download_dir"])
    ).expanduser()

    try:
        download_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        settings["download_dir"] = str(DEFAULT_DOWNLOAD_DIR)
        download_dir = DEFAULT_DOWNLOAD_DIR
        download_dir.mkdir(parents=True, exist_ok=True)
        save_settings(settings)

    while True:
        clear_screen()
        print_header()
        print()
        print(f"  Download directory: {settings['download_dir']}")
        print(f"  FFmpeg: {'available' if check_ffmpeg() else 'not found'}")
        print(f"  History entries: {len(history)}")
        print()
        print("  1. New download")
        print("  2. History")
        print("  3. Settings")
        print("  4. Clear history")
        print("  0. Exit")
        print()

        choice = input("  Select: ").strip()

        if choice == "1":
            start_download(settings, history)
            pause()

        elif choice == "2":
            show_history(history)

        elif choice == "3":
            show_settings(settings)

        elif choice == "4":
            clear_history(history)

        elif choice == "0":
            clear_screen()
            print("Goodbye.")
            return


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        clear_screen()
        print("Operation cancelled.")

    except Exception as exc:
        clear_screen()
        print_header("FATAL ERROR")
        print()
        print(f"  {clean_error(exc)}")
        print()
        print("  The application stopped unexpectedly.")
        print()
        input("  Press Enter to exit...")
