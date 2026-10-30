"""Playback shortcut regressions, without starting a GUI or playing media."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call

import vlc


source = Path(__file__).with_name("minivid.py").read_text(encoding="utf-8")
compile(source, "minivid.py", "exec")
window = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "MiniVidWindow")
method = next(n for n in window.body if isinstance(n, ast.FunctionDef) and n.name == "toggle_pause")
namespace = {"vlc": vlc}
exec(compile(ast.Module(body=[method], type_ignores=[]), "minivid.py", "exec"), namespace)
toggle_pause = namespace["toggle_pause"]


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.subject = SimpleNamespace(
            folder=SimpleNamespace(current=Path("video.mp4")),
            player=Mock(),
            resolution_timer=Mock(),
        )

    def test_playing_video_pauses(self):
        self.subject.player.get_state.return_value = vlc.State.Playing
        toggle_pause(self.subject)
        self.subject.player.set_pause.assert_called_once_with(1)
        self.subject.player.play.assert_not_called()

    def test_paused_video_resumes(self):
        self.subject.player.get_state.return_value = vlc.State.Paused
        toggle_pause(self.subject)
        self.subject.player.set_pause.assert_called_once_with(0)
        self.subject.player.play.assert_not_called()

    def test_ended_video_replays_and_restarts_resolution_polling(self):
        self.subject.player.get_state.return_value = vlc.State.Ended
        toggle_pause(self.subject)
        self.assertEqual(
            self.subject.player.method_calls,
            [call.get_state(), call.set_time(0), call.play()],
        )
        self.subject.resolution_timer.start.assert_called_once_with()

    def test_no_current_video_does_nothing(self):
        self.subject.folder.current = None
        toggle_pause(self.subject)
        self.subject.player.get_state.assert_not_called()
        self.subject.resolution_timer.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
