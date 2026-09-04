"""The 'mark' segment action.

'keep' is pulled from the cut list before the validator, the reviewer, the
hold rules and the min-cut-confidence gate ever run, on the reasoning that a
segment left in the audio can do no harm. That stops being true once a player
auto-skips the chapter published for it. 'mark' rides the full cut path so it
inherits every one of those guards, and diverges only at the audio edit.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from config import SEGMENT_ACTIONS, count_not_cut


class TestMarkIsARecognisedAction:
    def test_mark_is_accepted_by_the_settings_allowlist(self):
        # api/settings.py and api/feeds.py both gate on this tuple.
        assert 'mark' in SEGMENT_ACTIONS

    def test_existing_actions_are_unchanged(self):
        assert SEGMENT_ACTIONS == ('remove', 'beep', 'keep', 'mark')


class TestMarkIsNotAMiss:
    """A deliberately-marked segment must not inflate the 'not cut' count
    the notifications surface, exactly as a kept one does not."""

    def test_marked_marker_is_excluded(self):
        markers = [{'was_cut': False, 'action_applied': 'mark'}]
        assert count_not_cut(markers) == 0

    def test_kept_marker_is_still_excluded(self):
        markers = [{'was_cut': False, 'action_applied': 'keep'}]
        assert count_not_cut(markers) == 0

    def test_a_genuine_miss_still_counts(self):
        markers = [{'was_cut': False, 'action_applied': 'remove'}]
        assert count_not_cut(markers) == 1


class TestMarkDivergesOnlyAtTheAudioEdit:
    """AudioProcessor.remove_ads is the single seam where 'mark' stops
    behaving like 'remove'."""

    def _processor(self):
        # __new__ skips __init__; only the attributes the cutting path
        # touches after the mark filter are needed here.
        from audio_processor import AudioProcessor
        proc = AudioProcessor.__new__(AudioProcessor)
        proc.replace_audio_path = '/nonexistent/replace.mp3'
        return proc

    def test_marked_segments_are_dropped_before_cutting(self, tmp_path, monkeypatch):
        src = tmp_path / "in.mp3"
        src.write_bytes(b"audio")
        out = tmp_path / "out.mp3"
        segments = [{'start': 10.0, 'end': 20.0, 'action_applied': 'mark'}]
        applied = self._processor().remove_ads(str(src), segments, str(out))
        # Nothing to cut: the file is copied and no cut is reported, so
        # downstream timestamp mapping never shifts.
        assert applied == []
        assert out.read_bytes() == b"audio"

    def test_a_marked_span_does_not_suppress_a_real_cut(self, tmp_path):
        # Only-mark takes the "nothing to cut" early return. Adding a
        # removable segment must not: it proceeds into the cutting path,
        # which then fails on this stub audio. The difference in return
        # value is the proof the filter dropped only the mark.
        src = tmp_path / "in.mp3"
        src.write_bytes(b"audio")
        mark_only = [{'start': 10.0, 'end': 20.0, 'action_applied': 'mark'}]
        mixed = mark_only + [{'start': 30.0, 'end': 40.0,
                              'action_applied': 'remove'}]

        assert self._processor().remove_ads(
            str(src), mark_only, str(tmp_path / "a.mp3")) == []
        assert self._processor().remove_ads(
            str(src), mixed, str(tmp_path / "b.mp3")) is None


class TestMarkStaysOnTheCutPath:
    """The guards 'keep' bypasses are all reached via the cut list, so the
    partition step must leave a mark in it."""

    def test_partition_keep_ads_does_not_pull_a_mark(self):
        from main_app.processing import _partition_keep_ads
        ads = [{'start': 1.0, 'end': 2.0, 'category': 'sponsor'}]
        keep, remove = _partition_keep_ads(ads, {'sponsor': 'mark'})
        assert keep == []
        assert remove == ads

    def test_partition_cut_actions_stamps_mark_and_clears_was_cut(self):
        from main_app.processing import _partition_cut_actions
        ads = [{'start': 1.0, 'end': 2.0, 'category': 'sponsor',
                'was_cut': True}]
        _partition_cut_actions(ads, {'sponsor': 'mark'})
        assert ads[0]['action_applied'] == 'mark'
        assert ads[0]['was_cut'] is False

    def test_remove_action_still_reports_was_cut(self):
        from main_app.processing import _partition_cut_actions
        ads = [{'start': 1.0, 'end': 2.0, 'category': 'sponsor',
                'was_cut': True}]
        _partition_cut_actions(ads, {'sponsor': 'remove'})
        assert ads[0]['action_applied'] == 'remove'
        assert ads[0]['was_cut'] is True


class TestMarkIsChapterWorthy:
    def test_merge_ad_chapters_marks_a_mark(self):
        from chapters_generator import merge_ad_chapters
        markers = [{'start': 900.0, 'end': 960.0, 'action_applied': 'mark',
                    'category': 'sponsor', 'confidence': 0.99}]
        result = merge_ad_chapters([{'startTime': 1, 'title': 'Intro'}],
                                   markers, [], 3600.0)
        assert {'startTime': 900, 'title': '[mp:sponsor]'} in result

    def test_build_segment_hints_treats_a_mark_as_a_range(self):
        from chapters_generator import build_segment_hints
        markers = [{'start': 100.0, 'end': 130.0, 'action_applied': 'mark',
                    'category': 'sponsor'}]
        hints = build_segment_hints(markers, [])
        assert hints[0]['type'] == 'range'
