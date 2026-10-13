"""Exercise the multipage UI: run gating, stale results, inputs, methods and the flowsheet."""
import base64
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'app'))

PAGES = ['views/overview.py', 'views/feed.py', 'views/process.py', 'views/cost.py',
         'views/carbon.py', 'views/policy.py', 'views/results.py', 'views/uncertainty.py',
         'views/methods.py']


def _app():
    from streamlit.testing.v1 import AppTest
    return AppTest.from_file(str(ROOT / 'app' / 'streamlit_app.py'), default_timeout=90).run()


def _number(app, suffix):
    return next(n for n in app.number_input if (n.key or '').endswith(suffix))


def _image_svg(app):
    url = app.get('image')[0].proto.imgs[0].url
    assert url.startswith('data:image/svg+xml;base64,')
    return base64.b64decode(url.split(',', 1)[1]).decode()


@unittest.skipUnless(importlib.util.find_spec('streamlit'), 'Install requirements.txt for UI tests')
class AppTests(unittest.TestCase):
    def test_every_page_renders_before_and_after_run(self):
        app = _app()
        self.assertFalse(app.exception)
        for page in PAGES:
            app.switch_page(page).run()
            self.assertFalse(app.exception, page)
            self.assertFalse(app.metric, f'{page} shows results before Run')
        app.button(key='run_sidebar').click().run()
        self.assertIsNotNone(app.session_state['run'])
        for page in PAGES:
            app.switch_page(page).run()
            self.assertFalse(app.exception, page)

    def test_run_snapshot_and_stale_banner(self):
        app = _app()
        app.switch_page('views/feed.py').run()
        app.button(key='run_feed').click().run()
        self.assertEqual(app.metric[0].value, '692')
        _number(app, '_GaFeed').set_value(100.0).run()
        self.assertEqual(app.session_state['overrides']['GaFeed'], 100)
        # Results stay on the previous run until Run is pressed again.
        self.assertTrue(any('changed since the last run' in w.value for w in app.warning))
        self.assertEqual(app.metric[0].value, '692')
        app.button(key='run_feed').click().run()
        self.assertFalse(app.warning)
        self.assertEqual(app.metric[0].value, '484')
        # Edits survive a page change and come back seeded from session state.
        app.switch_page('views/results.py').run()
        app.switch_page('views/feed.py').run()
        self.assertEqual(_number(app, '_GaFeed').value, 100)
        app.button(key='reset_all').click().run()
        self.assertEqual(app.session_state['overrides'], {})
        self.assertEqual(_number(app, '_GaFeed').value, 70)
        self.assertTrue(any('changed since the last run' in w.value for w in app.warning))

    def test_resin_preset_locks_and_syncs_ix_inputs(self):
        app = _app()
        app.switch_page('views/process.py').run()
        ix = [n for n in app.number_input if (n.key or '').endswith('_IXRec')]
        self.assertEqual(len(ix), 2)
        self.assertTrue(all(n.disabled for n in ix))
        app.selectbox(key='cfg_resin_preset').select(4).run()
        self.assertFalse(app.exception)
        ix = [n for n in app.number_input if (n.key or '').endswith('_IXRec')]
        self.assertFalse(any(n.disabled for n in ix))
        ix[0].set_value(50.0).run()
        self.assertFalse(app.exception)
        self.assertTrue(all(n.value == 50 for n in app.number_input
                            if (n.key or '').endswith('_IXRec')))

    def test_method_choices(self):
        app = _app()
        app.switch_page('views/cost.py').run()
        app.selectbox(key='cfg_capex_mode').select('per_stage').run()
        self.assertEqual(len([n for n in app.number_input if (n.key or '').startswith('stage_')]), 11)
        app.selectbox(key='cfg_capex_mode').select('user_total').run()
        app.number_input(key='cx_fci').set_value(300e6).run()
        app.button(key='run_cost').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['cfg'].capex_user.fci_aud, 300e6)
        app.switch_page('views/policy.py').run()
        app.selectbox(key='cfg_policy_model').select('legacy').run()
        app.button(key='run_policy').click().run()
        self.assertFalse(app.exception)
        app.switch_page('views/results.py').run()
        self.assertFalse(app.exception)

    def test_flow_diagram_follows_the_run(self):
        def diagram(app):
            return next(m.value for m in app.markdown if "<svg" in m.value)

        app = _app()
        app.switch_page('views/process.py').run()
        app.button(key='run_process').click().run()
        svg = diagram(app)
        self.assertIn('Stream 1 · Bayer liquor slipstream', svg)
        self.assertIn('Total 71,943 kg per kg Ga', svg)
        self.assertEqual(svg.count('class="ga-stream"'), 34)
        app.switch_page('views/feed.py').run()
        _number(app, '_GaFeed').set_value(100.0).run()
        app.button(key='run_feed').click().run()
        app.switch_page('views/process.py').run()
        self.assertIn('Total 50,360 kg per kg Ga', diagram(app))
        self.assertFalse(app.exception)

    def test_cost_bridge_shows_every_package(self):
        import charts
        app = _app()
        app.switch_page('views/cost.py').run()
        app.button(key='run_cost').click().run()
        self.assertFalse(app.exception)
        spec = app.get('vega_lite_chart')[0].proto.spec
        for name in ('No policy support', 'Medium support', 'Bullish support'):
            self.assertIn(name, spec)
        self.assertNotIn('"Custom"', spec)
        self.assertTrue(hasattr(charts, 'bridge_compare'))

    def test_uncertainty_after_run(self):
        app = _app()
        app.switch_page('views/uncertainty.py').run()
        self.assertNotIn('mc_go', [b.key for b in app.button])
        app.button(key='run_unc_empty').click().run()
        app.select_slider(key='mc_trials').set_value(200).run()
        app.button(key='mc_go').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['mc']['trials'], 200)
        # Histogram bars span bin edges and carry no corner radius (which Vega-Lite 6
        # drops for x/x2 range bars, leaving an empty chart).
        spec = app.get('vega_lite_chart')[-1].proto.spec
        self.assertIn('"field": "from"', spec.replace('":"', '": "'))
        self.assertNotIn('cornerRadiusTopLeft', spec)
        app.radio(key='unc_target').set_value('carbon').run()
        self.assertFalse(app.exception)


if __name__ == '__main__':
    unittest.main()
