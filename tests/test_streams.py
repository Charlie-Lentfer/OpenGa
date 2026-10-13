import copy
import dataclasses
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openga_v1.config import ModelInputs, ModelConfig
from openga_v1.engine import run
from openga_v1 import validation
from openga_v1.streams import build_streams, balance_rows, stream_issues, INPUT_IDS, OUTPUT_IDS
from openga_flowsheet.flowsheet import INPUTS, OUTPUTS, overview_rows, render_svg


class LiveStreamTests(unittest.TestCase):
    def test_baseline_preserves_v1_results(self):
        groups = validation.run_all(ModelInputs())
        self.assertEqual(len(groups['internal']), 14)
        self.assertEqual(len(groups['regression']), 10)
        self.assertTrue(all(c.verdict == 'PASS' for g in ('internal', 'regression') for c in groups[g]))

    def test_balances_and_nonnegative_values_across_scenarios(self):
        scenarios = [({}, 1), ({'GaFeed': 48}, 1), ({'GaFeed': 185}, 1),
                     ({'WashRec': 90}, 1), ({'PrecRec': 85}, 1),
                     ({'NaOH_UP9': 30}, 1), ({'CapProd': 200000}, 1),
                     ({}, 2), ({}, 3), ({'IXRec': 60, 'CoAdsAl': 2}, 4)]
        for params, resin in scenarios:
            with self.subTest(params=params, resin=resin):
                r = run(ModelInputs(cfg=ModelConfig(resin_preset=resin)).with_overrides(params))
                self.assertEqual(len(r.streams), 37)
                checks = balance_rows(r.streams)
                self.assertEqual(len(checks), 52)
                self.assertTrue(all(row['Status'] == 'PASS' for row in checks))
                self.assertFalse(stream_issues(r.streams))

    def test_streams_agree_with_existing_meb(self):
        r = run(ModelInputs().with_overrides({'WashRec': 95, 'PrecRec': 85}))
        s, m = r.streams, r.meb
        for stream, value in [('S1', m.feed_ga_kg), ('S3', m.ga_out['UP1']),
                              ('S5', m.ga_out['UP2']), ('S8', m.ga_out['UP3']),
                              ('S14', m.ga_out['UP5']), ('S23', m.ga_cake),
                              ('S28', m.ga_elyte), ('S31', m.ga_crude), ('S34', 1)]:
            self.assertAlmostEqual(s[stream]['Ga'], value)
        self.assertAlmostEqual(s['S1']['total_kg_per_kg_Ga'], m.liquor_kg_per_kg)
        self.assertAlmostEqual(s['S10']['total_kg_per_kg_Ga'], m.w_raw_kg)
        self.assertAlmostEqual(s['S20']['components']['NaOH'] + s['S24']['components']['NaOH'], m.naoh_total)

    def test_wash_and_precipitation_losses_are_retained(self):
        r = run(ModelInputs().with_overrides({'WashRec': 90, 'PrecRec': 80}))
        s, m = r.streams, r.meb
        self.assertAlmostEqual(s['S7']['Ga'], m.ga_out['UP2'] - m.ga_out['UP3'])
        self.assertAlmostEqual(s['S22']['Ga'], m.ga_out['UP5'] - m.ga_out['UP8'])
        self.assertGreater(s['S21']['components']['Ga'], 0)

    def test_no_boundary_double_counting(self):
        ids = [sid for g in INPUTS + OUTPUTS for sid in g.ids]
        self.assertEqual(set(ids), set(INPUT_IDS + OUTPUT_IDS))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn('S30', ids)
        self.assertNotIn('S30R', ids)
        r = run(ModelInputs())
        self.assertEqual(r.streams['S30R']['total_kg_per_kg_Ga'], 0)
        self.assertEqual(r.streams['S30']['components'], r.streams['S30P']['components'])

    def test_rendered_values_follow_changed_feed(self):
        a = run(ModelInputs())
        b = run(ModelInputs().with_overrides({'GaFeed': 140}))
        self.assertAlmostEqual(b.streams['S1']['total_kg_per_kg_Ga'], a.streams['S1']['total_kg_per_kg_Ga'] / 2)
        self.assertNotEqual(overview_rows(a.streams), overview_rows(b.streams))
        self.assertIn('71,943 kg', render_svg(a.streams))
        self.assertIn('35,972 kg', render_svg(b.streams))

    def test_all_display_variants_parse(self):
        s = run(ModelInputs()).streams
        for component in ('total', 'Ga', 'Al', 'V'):
            for theme in ('light', 'dark'):
                for interactive in (True, False):
                    svg = render_svg(s, component=component, theme=theme, interactive=interactive)
                    ET.fromstring(svg)
                    self.assertEqual('Hover cards' in svg, interactive)

    def test_reporting_does_not_mutate_model(self):
        r = run(ModelInputs())
        before = (copy.deepcopy(r.params), dataclasses.asdict(r.meb))
        build_streams(r.params, r.meb)
        self.assertEqual(before, (r.params, dataclasses.asdict(r.meb)))

    def test_invalid_stream_is_flagged_even_when_a_total_can_close(self):
        s = run(ModelInputs()).streams
        s['S30']['components']['Water'] = -1
        self.assertTrue(stream_issues(s))

    def test_v1_does_not_silently_accept_unmodelled_recycle(self):
        r = run(ModelInputs())
        with self.assertRaisesRegex(ValueError, 'recycle'):
            build_streams({**r.params, 'EWRecycle': 50}, r.meb)

    def test_scenario_is_not_compared_to_unchanged_workbook_baseline(self):
        for mi in [ModelInputs().with_overrides({'GaFeed': 100}),
                   ModelInputs(cfg=ModelConfig(policy_package=2))]:
            checks = validation.regression(mi)
            self.assertTrue(all(c.kind == 'info' for c in checks))


if __name__ == '__main__':
    unittest.main()
