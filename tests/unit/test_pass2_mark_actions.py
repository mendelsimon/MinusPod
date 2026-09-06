"""Pass-2 must honour the 'mark' action instead of cutting.

Regression: _stamp_pass2_cut_actions only allowed remove/beep, so a pass-2
finding whose category resolved to 'mark' was rewritten to
DEFAULT_SEGMENT_ACTION and re-cut out of the pass-1 output. With every
category on 'mark' that silently removed show content -- observed on two
episodes, where the show's own theme song was cut by the second pass after
pass 1 had correctly left it in place.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from main_app.processing import _stamp_pass2_cut_actions
from main_app.verification_reconciliation import _drop_uncovered_pass2_ads

ALL_MARK = {c: 'mark' for c in
            ('sponsor', 'cross_promo', 'self_promo', 'interaction',
             'intro', 'outro', 'recap')}


def _ad(start, end, category=None):
    ad = {'start': start, 'end': end}
    if category is not None:
        ad['category'] = category
    return ad


class TestStampHonoursMark:
    def test_mark_category_is_not_rewritten_to_remove(self):
        proc, orig = [_ad(1.2, 63.7, 'intro')], [_ad(1.2, 63.7, 'intro')]
        _stamp_pass2_cut_actions(proc, orig, ALL_MARK)
        assert proc[0]['action_applied'] == 'mark'
        assert orig[0]['action_applied'] == 'mark'

    def test_mark_is_stamped_not_cut(self):
        proc, orig = [_ad(1.2, 63.7, 'intro')], [_ad(1.2, 63.7, 'intro')]
        _stamp_pass2_cut_actions(proc, orig, ALL_MARK)
        assert proc[0]['was_cut'] is False
        assert orig[0]['was_cut'] is False

    def test_uncategorised_pass2_ad_follows_the_sponsor_action(self):
        # Verification findings that arrive without a category normalize to
        # 'sponsor'; with sponsor on mark they must not cut either.
        proc, orig = [_ad(2194.2, 2225.4)], [_ad(2194.2, 2225.4)]
        _stamp_pass2_cut_actions(proc, orig, ALL_MARK)
        assert proc[0]['action_applied'] == 'mark'

    def test_remove_still_cuts_when_the_category_says_so(self):
        actions = dict(ALL_MARK, sponsor='remove')
        proc, orig = [_ad(100.0, 160.0, 'sponsor')], [_ad(100.0, 160.0, 'sponsor')]
        _stamp_pass2_cut_actions(proc, orig, actions)
        assert proc[0]['action_applied'] == 'remove'
        assert 'was_cut' not in proc[0]

    def test_beep_is_untouched(self):
        actions = dict(ALL_MARK, sponsor='beep')
        proc, orig = [_ad(100.0, 160.0, 'sponsor')], [_ad(100.0, 160.0, 'sponsor')]
        _stamp_pass2_cut_actions(proc, orig, actions)
        assert proc[0]['action_applied'] == 'beep'

    def test_an_unknown_action_still_falls_back_to_the_default(self):
        proc, orig = [_ad(100.0, 160.0, 'sponsor')], [_ad(100.0, 160.0, 'sponsor')]
        _stamp_pass2_cut_actions(proc, orig, {'sponsor': 'explode'})
        assert proc[0]['action_applied'] == 'remove'


class TestMarksSurviveTheCoverageDrop:
    def test_a_mark_is_kept_though_the_recut_never_touched_it(self):
        proc = [_ad(1.2, 63.7, 'intro')]
        ui = [_ad(1.2, 63.7, 'intro')]
        _stamp_pass2_cut_actions(proc, ui, ALL_MARK)
        # remove_ads drops marks, so an all-mark recut applies nothing.
        _drop_uncovered_pass2_ads('slug', 'ep', proc, ui, [], list(proc), list(ui))
        assert len(proc) == 1
        assert len(ui) == 1

    def test_an_uncut_remove_is_still_dropped(self):
        proc = [_ad(100.0, 160.0, 'sponsor')]
        ui = [_ad(100.0, 160.0, 'sponsor')]
        _stamp_pass2_cut_actions(proc, ui, dict(ALL_MARK, sponsor='remove'))
        _drop_uncovered_pass2_ads('slug', 'ep', proc, ui, [], list(proc), list(ui))
        assert proc == []
        assert ui == []

    def test_a_mark_beside_an_uncut_remove_survives_alone(self):
        proc = [_ad(1.2, 63.7, 'intro'), _ad(100.0, 160.0, 'sponsor')]
        ui = [_ad(1.2, 63.7, 'intro'), _ad(100.0, 160.0, 'sponsor')]
        _stamp_pass2_cut_actions(proc, ui, dict(ALL_MARK, sponsor='remove'))
        _drop_uncovered_pass2_ads('slug', 'ep', proc, ui, [], list(proc), list(ui))
        assert [a['start'] for a in proc] == [1.2]
        assert [a['start'] for a in ui] == [1.2]
