from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PARENTS = Path(__file__).resolve().parents
ROOT = PARENTS[3] if len(PARENTS) > 3 else Path.cwd()
SCRIPT = Path(os.environ.get('TECHFLOW_XSLT_VERIFY_SCRIPT', str(ROOT / 'deploy/flarum/extensions/ablecloud-community-theme/tools/verify-xslt-assets.php')))
PHP = shutil.which('php')


class XsltDeploymentContractTests(unittest.TestCase):
    def test_theme_publishes_before_verification(self):
        deploy = (ROOT / 'deploy/flarum/apply-community-theme-update.sh').read_text(encoding='utf-8')
        self.assertLess(deploy.index('cache:clear'), deploy.index('assets:publish'))
        self.assertLess(deploy.index('assets:publish'), deploy.index('verify-xslt-assets.php'))

    def test_rehearsals_cover_compatibility_assets(self):
        theme = (ROOT / 'deploy/flarum/rehearse-community-theme.sh').read_text(encoding='utf-8')
        core = (ROOT / 'deploy/flarum/rehearse-1.8.18.sh').read_text(encoding='utf-8')
        self.assertIn('assets:publish', theme)
        self.assertIn('verify-xslt-assets.php', theme)
        self.assertIn('assets:publish', core)
        self.assertIn('xslt-polyfill.min.js', core)
        self.assertIn('dist/xslt-wasm.js', core)


@unittest.skipUnless(PHP, 'PHP CLI is required for native verifier tests')
class XsltVerifierRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='community-xslt-unit-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        marker = self.root / 'vendor/flarum/core/src/Formatter/XsltPolyfill.php'
        marker.parent.mkdir(parents=True)
        marker.write_text('<?php // fixture only')
        self.source = self.root / 'vendor/flarum/core/js/dist/xslt-polyfill'
        self.public = self.root / 'public/assets/xslt-polyfill'
        for relative in ('xslt-polyfill.min.js', 'dist/xslt-wasm.js'):
            for base in (self.source, self.public):
                p = base / relative
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('/* synthetic ' + relative + ' */')

    def run_verifier(self, target=None):
        env = {**os.environ, 'TECHFLOW_ALLOWED_FLARUM_ROOT': str(self.root)}
        return subprocess.run([PHP, str(SCRIPT), str(target or self.root)], env=env,
                              capture_output=True, text=True, check=False)

    def test_matching_files_pass_without_modifying_them(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.run_verifier()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(json.loads(result.stdout)['verified']))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_older_core_does_not_require_an_unused_polyfill(self):
        (self.root / 'vendor/flarum/core/src/Formatter/XsltPolyfill.php').unlink()
        result = self.run_verifier()
        self.assertEqual(0, result.returncode)
        self.assertFalse(json.loads(result.stdout)['required'])

    def test_missing_main_fails(self):
        (self.public / 'xslt-polyfill.min.js').unlink()
        self.assertEqual(1, self.run_verifier().returncode)

    def test_missing_wasm_bundle_fails(self):
        (self.public / 'dist/xslt-wasm.js').unlink()
        self.assertEqual(1, self.run_verifier().returncode)

    def test_missing_vendor_bundle_fails(self):
        (self.source / 'dist/xslt-wasm.js').unlink()
        self.assertEqual(1, self.run_verifier().returncode)

    def test_empty_file_fails(self):
        (self.public / 'xslt-polyfill.min.js').write_text('')
        self.assertEqual(1, self.run_verifier().returncode)

    def test_mismatched_file_fails(self):
        (self.public / 'dist/xslt-wasm.js').write_text('different fixture')
        self.assertEqual(1, self.run_verifier().returncode)

    def test_wrong_root_is_rejected(self):
        other = self.root / 'other'
        other.mkdir()
        self.assertEqual(2, self.run_verifier(other).returncode)


if __name__ == '__main__':
    unittest.main()
