from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REQUIRED_PACKAGES = {
    "vlc": "python-vlc>=3.0",
    "PySide6": "PySide6>=6.7",
    "send2trash": "Send2Trash>=1.8",
}


def ensure_required_packages() -> None:
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)

    if not missing:
        return

    print("Installing missing Python packages:")
    for package_name in missing:
        print(f"  - {package_name}")

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    except subprocess.CalledProcessError as exc:
        print()
        print("Could not install required packages automatically.")
        print("Try running this from the minivid folder:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")
        raise SystemExit(exc.returncode) from exc


ensure_required_packages()

import vlc  # noqa: E402
from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtGui import QKeySequence, QShortcut  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget  # noqa: E402
from send2trash import send2trash  # noqa: E402


VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".flv",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.name.casefold())
    return [int(part) if part.isdigit() else part for part in parts]


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.casefold() in VIDEO_EXTENSIONS


class VideoFolder:
    def __init__(self) -> None:
        self.files: list[Path] = []
        self.index = 0

    @property
    def current(self) -> Path | None:
        if not self.files:
            return None
        return self.files[self.index]

    def load(self, video_path: Path) -> None:
        video_path = video_path.resolve()
        if not is_video(video_path):
            raise ValueError(f"Not a supported video file: {video_path}")

        self.files = sorted(
            (path for path in video_path.parent.iterdir() if is_video(path)),
            key=natural_key,
        )
        self.index = self.files.index(video_path)

    def move(self, offset: int) -> Path | None:
        if not self.files:
            return None
        self.index = (self.index + offset) % len(self.files)
        return self.current

    def remove_current(self) -> Path | None:
        if not self.files:
            return None

        deleted_index = self.index
        deleted_path = self.files.pop(deleted_index)
        if self.files:
            self.index = min(deleted_index, len(self.files) - 1)
        else:
            self.index = 0
        return deleted_path


class MiniVidWindow(QMainWindow):
    def __init__(self, initial_video: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("minivid")
        self.setAcceptDrops(True)
        self.resize(960, 540)

        self.folder = VideoFolder()
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.video_resolution: tuple[int, int] | None = None

        self.video_frame = QWidget(self)
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.video_frame.setStyleSheet("background: black;")

        self.setCentralWidget(self.video_frame)

        self.resolution_timer = QTimer(self)
        self.resolution_timer.setInterval(250)
        self.resolution_timer.timeout.connect(self.update_video_resolution)

        self.install_shortcuts()

        if initial_video is not None:
            self.open_video(initial_video)

    def install_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Tab), self, activated=self.next_video)
        QShortcut(QKeySequence(Qt.Key.Key_Backtab), self, activated=self.previous_video)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, activated=self.delete_current)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, activated=self.delete_current)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.toggle_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.close)

    def open_video(self, path: Path) -> None:
        try:
            self.folder.load(path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return

        self.play_current()

    def play_current(self) -> None:
        self.resolution_timer.stop()
        self.video_resolution = None
        self.player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 0)
        current = self.folder.current
        if current is None:
            self.player.stop()
            self.setWindowTitle("minivid")
            return

        media = self.vlc_instance.media_new(str(current))
        self.player.set_media(media)
        self.attach_player_to_window()

        self.player.play()

        self.setWindowTitle(f"minivid - {current.name}")

        self.resolution_timer.start()

    def attach_player_to_window(self) -> None:
        handle = int(self.video_frame.winId())
        if sys.platform.startswith("win"):
            self.player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self.player.set_nsobject(handle)
        else:
            self.player.set_xwindow(handle)

    def next_video(self) -> None:
        if self.folder.move(1):
            self.play_current()

    def previous_video(self) -> None:
        if self.folder.move(-1):
            self.play_current()

    def delete_current(self) -> None:
        current = self.folder.current
        if current is None:
            return

        self.player.stop()
        deleted_path = self.folder.remove_current()
        if deleted_path is not None:
            send2trash(str(deleted_path))
        self.play_current()

    def toggle_pause(self) -> None:
        if self.folder.current is not None:
            self.player.pause()

    def update_video_resolution(self) -> None:
        state = self.player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error):
            self.resolution_timer.stop()
            return
        # Metadata can be ready before the output that will draw the marquee.
        # Stopped can also be transient while switching media; keep polling.
        if state not in (vlc.State.Playing, vlc.State.Paused) or not self.player.has_vout():
            return
        size = self.player.video_get_size(0)
        if not size:
            return
        width, height = size

        if width > 0 and height > 0:
            changed = self.video_resolution != (width, height)
            self.video_resolution = (width, height)

            if not changed and self.player.video_get_marquee_int(vlc.VideoMarqueeOption.Enable):
                return

            # Configure before enabling. Rewriting settings on every tick
            # triggers VLC's sub-source callbacks and can rebuild the filter.
            self.player.video_set_marquee_int(
                vlc.VideoMarqueeOption.Enable, 0
            )
            self.player.video_set_marquee_string(
                vlc.VideoMarqueeOption.Text,
                f"{width} x {height}"
            )
            self.player.video_set_marquee_int(
                vlc.VideoMarqueeOption.Position,
                vlc.Position.top_right.value
            )
            self.player.video_set_marquee_int(
                vlc.VideoMarqueeOption.Size, 18
            )
            self.player.video_set_marquee_int(
                vlc.VideoMarqueeOption.Timeout, 0
            )
            self.player.video_set_marquee_int(
                vlc.VideoMarqueeOption.Enable, 1
            )

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and is_video(Path(url.toLocalFile())):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if is_video(path):
                    self.open_video(path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.resolution_timer.stop()
        self.player.stop()
        super().closeEvent(event)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quickly review and delete videos in a folder.")
    parser.add_argument("video", nargs="?", type=Path, help="Video file to open.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    app = QApplication(sys.argv)
    window = MiniVidWindow(args.video)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
