import json
from prepare_sync import git
from refresh_upstream import refresh
from test_prepare_sync import SyncFixture
import test_prepare_sync


class RefreshTests(SyncFixture):
    def image_history(self):
        git(self.root, 'checkout', '--detach', self.upstream)
        workflows = self.root / '.github/workflows'
        workflows.mkdir(parents=True)
        for name, called in [('call-build.yml', 'build-on-call.yml'),
                             ('call-update.yml', 'update-on-call.yml')]:
            (workflows / name).write_text(
                f'name: call\njobs:\n  call:\n    uses: hotio/base/.github/workflows/{called}@workflows\n')
        (workflows / 'build-on-call.yml').write_text(
            'name: build\njobs:\n  build:\n    steps: []\n'
            '  tags:\n    url: https://hotio.dev/containers/base\n  notify:\n    steps: []\n')
        (workflows / 'update-on-call.yml').write_text('name: update\njobs:\n  update:\n    steps: []\n')
        (workflows / 'maintenance.yml').write_text('account-wide mutation\n')
        (self.root / 'renovate.json').write_text('{}\n')
        upstream = self.commit('upstream workflows')
        git(self.root, 'checkout', '--detach', self.base)
        (self.root / 'README.md').write_text('edbfi documentation\n')
        self.base = self.commit('destination documentation')
        return upstream

    def test_full_refresh_restores_workflows_without_replacing_history(self):
        upstream = self.image_history()
        result = refresh(self.root, 'base-image', 'workflows', upstream, None)
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), self.base)
        self.assertEqual(result['base'], self.base)
        self.assertFalse((self.root / 'custom.txt').exists())
        self.assertEqual((self.root / 'README.md').read_text(), 'edbfi documentation\n')
        workflows = self.root / '.github/workflows'
        self.assertIn('edbfi/base-image/', (workflows / 'call-build.yml').read_text())
        self.assertIn('https://web.edb.fi/containers/', (workflows / 'build-on-call.yml').read_text())
        self.assertNotIn('notify:', (workflows / 'build-on-call.yml').read_text())
        self.assertFalse((workflows / 'maintenance.yml').exists())
        self.assertFalse((self.root / 'renovate.json').exists())
        self.assertEqual(json.loads((self.root / '.upstream.json').read_text())['revision'], upstream)
        self.commit('apply refresh')
        refresh(self.root, 'base-image', 'workflows', upstream, None)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_dirty_destination_rejected_before_replacing_files(self):
        upstream = self.image_history()
        (self.root / 'custom.txt').write_text('uncommitted\n')
        with self.assertRaisesRegex(ValueError, 'clean'):
            refresh(self.root, 'base-image', 'workflows', upstream, None)
        self.assertEqual((self.root / 'custom.txt').read_text(), 'uncommitted\n')

    def test_wrong_target_branch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'provenance'):
            refresh(self.root, 'base-image', 'alpinevpn', self.upstream, None)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')


class WebsiteRefreshTests(SyncFixture):
    site_history = test_prepare_sync.WebsiteSyncTests.site_history

    def test_refresh_preserves_destination_tags_and_overlay(self):
        source, base, upstream = self.site_history()
        git(self.root, 'checkout', '--detach', upstream)
        workflow = self.root / '.github/workflows/deploy-pages.yml'
        workflow.parent.mkdir(parents=True)
        workflow.write_text('run: pip install zensical\n')
        upstream = self.commit('upstream Pages')
        git(self.root, 'checkout', '--detach', base)
        (self.root / 'docs/containers/caddy-tags.json').write_text('{"edbfi":"published"}\n')
        git(self.root, 'rm', 'docs/containers/sabnzbd-tags.json')
        (self.root / 'requirements.txt').write_text('zensical==0.0.65\n')
        base = self.commit('destination publication')
        refresh(self.root, 'website', 'master', upstream, source)
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), base)
        self.assertEqual(json.loads((self.root / 'docs/containers/caddy-tags.json').read_text()),
                         {'edbfi': 'published'})
        self.assertEqual(json.loads((self.root / 'docs/containers/sabnzbd-tags.json').read_text()), {})
        self.assertEqual((self.root / 'docs/CNAME').read_text().strip(), 'web.edb.fi')
        self.assertFalse((self.root / 'docs/containers/jackett.md').exists())
        self.assertIn('pip install -r requirements.txt', workflow.read_text())
        self.commit('apply refresh')
        refresh(self.root, 'website', 'master', upstream, source)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
