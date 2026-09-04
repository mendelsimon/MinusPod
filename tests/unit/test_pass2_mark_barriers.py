"""Pass-2 reconciliation against marked spans.

With every category on 'mark' nothing is cut, so the audio pass 2 reads still
contains every ad pass 1 found. It will therefore re-detect them all. A kept
span treats that as a disagreement worth reviewing; a marked span must not,
because the marker it would conflict with is the one pass 1 already published.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from main_app.verification_reconciliation import (
    _exclude_kept_spans_from_verification,
)


def _finding(start, end):
    return {'start': start, 'end': end}


def _barrier(start, end, action):
    return {'start': start, 'end': end, 'action_applied': action}


class TestMarkedSpansDropDuplicates:
    def test_finding_inside_a_marked_span_is_dropped(self):
        proc = [_finding(100.0, 130.0)]
        orig = [_finding(100.0, 130.0)]
        surviving_p, surviving_o, conflicts = _exclude_kept_spans_from_verification(
            proc, orig, [_barrier(95.0, 140.0, 'mark')], [], [])
        assert surviving_p == []
        # Dropped, not held: nothing for a human to adjudicate.
        assert conflicts == []

    def test_finding_inside_a_kept_span_is_still_held(self):
        proc = [_finding(100.0, 130.0)]
        orig = [_finding(100.0, 130.0)]
        surviving_p, surviving_o, conflicts = _exclude_kept_spans_from_verification(
            proc, orig, [_barrier(95.0, 140.0, 'keep')], [], [])
        assert surviving_p == []
        assert len(conflicts) == 1
        assert conflicts[0]['held_for_review'] is True

    def test_a_genuine_miss_outside_every_barrier_survives(self):
        # The whole point of keeping pass 2 on: ads pass 1 never found.
        proc = [_finding(500.0, 530.0)]
        orig = [_finding(500.0, 530.0)]
        surviving_p, _, conflicts = _exclude_kept_spans_from_verification(
            proc, orig, [_barrier(95.0, 140.0, 'mark')], [], [])
        assert surviving_p == proc
        assert conflicts == []

    def test_mixed_barriers_route_each_finding_correctly(self):
        proc = [_finding(100.0, 130.0), _finding(300.0, 330.0),
                _finding(700.0, 730.0)]
        orig = [dict(a) for a in proc]
        barriers = [_barrier(95.0, 140.0, 'mark'),
                    _barrier(295.0, 340.0, 'keep')]
        surviving_p, _, conflicts = _exclude_kept_spans_from_verification(
            proc, orig, barriers, [], [])
        assert [a['start'] for a in surviving_p] == [700.0]
        assert [c['start'] for c in conflicts] == [300.0]

    def test_no_barriers_is_a_passthrough(self):
        proc = [_finding(100.0, 130.0)]
        orig = [_finding(100.0, 130.0)]
        surviving_p, surviving_o, conflicts = _exclude_kept_spans_from_verification(
            proc, orig, [], [], [])
        assert surviving_p == proc
        assert conflicts == []
