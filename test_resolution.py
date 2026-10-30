"""Resolution polling regressions, without starting a GUI or playing media."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import vlc


source = Path(__file__).with_name("minivid.py").read_text(encoding="utf-8")
compile(source, "minivid.py", "exec")
window = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "MiniVidWindow")
method = next(n for n in window.body if isinstance(n, ast.FunctionDef) and n.name == "update_video_resolution")
namespace = {"vlc": vlc}
exec(compile(ast.Module(body=[method], type_ignores=[]), "minivid.py", "exec"), namespace)
update = namespace["update_video_resolution"]


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.subject = SimpleNamespace(
            player=Mock(), resolution_timer=Mock(),
            video_resolution=None,
        )
        self.subject.player.get_state.return_value = vlc.State.Playing
        self.subject.player.has_vout.return_value = 1
        self.subject.player.video_get_marquee_int.return_value = 1

    def test_delayed_size_and_changed_resolution(self):
        self.subject.player.video_get_size.side_effect = [None, (0, 0), (1920, 1080), (1280, 720)]
        for _ in range(4):
            update(self.subject)
        self.assertEqual(self.subject.video_resolution, (1280, 720))
        self.assertEqual(self.subject.player.video_set_marquee_string.call_count, 2)
        self.subject.resolution_timer.stop.assert_not_called()
        self.subject.player.video_set_marquee_int.assert_any_call(vlc.VideoMarqueeOption.Position, 5)
        self.subject.player.video_set_marquee_int.assert_any_call(vlc.VideoMarqueeOption.Timeout, 0)

    def test_terminal_states_stop_polling(self):
        for state in (vlc.State.Ended, vlc.State.Error):
            self.subject.player.get_state.return_value = state
            update(self.subject)
        self.assertEqual(self.subject.resolution_timer.stop.call_count, 2)
        self.subject.player.video_get_size.assert_not_called()

    def test_waits_for_output_and_survives_transient_stopped(self):
        self.subject.player.get_state.return_value = vlc.State.Stopped
        update(self.subject)
        self.subject.player.get_state.return_value = vlc.State.Playing
        self.subject.player.has_vout.return_value = 0
        update(self.subject)
        self.subject.player.video_set_marquee_int.assert_not_called()
        self.subject.resolution_timer.stop.assert_not_called()
        self.subject.player.has_vout.return_value = 1
        self.subject.player.video_get_size.return_value = (1920, 1080)
        update(self.subject)
        self.assertEqual(self.subject.video_resolution, (1920, 1080))

    def test_stable_overlay_is_not_reconfigured_but_missing_one_recovers(self):
        self.subject.player.video_get_size.return_value = (1920, 1080)
        update(self.subject)
        self.subject.player.reset_mock()
        update(self.subject)
        self.subject.player.video_set_marquee_int.assert_not_called()
        self.subject.player.video_set_marquee_string.assert_not_called()
        self.subject.player.video_get_marquee_int.return_value = 0
        update(self.subject)
        calls = self.subject.player.video_set_marquee_int.call_args_list
        self.assertEqual(calls[0].args, (vlc.VideoMarqueeOption.Enable, 0))
        self.assertEqual(calls[-1].args, (vlc.VideoMarqueeOption.Enable, 1))

    def test_real_vlc_accepts_integer_position(self):
        instance = vlc.Instance()
        player = instance.media_player_new()
        try:
            player.video_set_marquee_int(vlc.VideoMarqueeOption.Position, vlc.Position.top_right.value)
        finally:
            player.release()
            instance.release()


if __name__ == "__main__":
    unittest.main()
