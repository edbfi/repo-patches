import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from prepare_sync import prepare, git


class SyncFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.out = Path(self.temp.name) / 'evidence'
        git(self.root, 'init', '-b', 'main')
        # Finish Git housekeeping before TemporaryDirectory removes the fixture.
        git(self.root, 'config', 'maintenance.autoDetach', 'false')
        git(self.root, 'config', 'gc.autoDetach', 'false')
        git(self.root, 'config', 'user.name', 'Test')
        git(self.root, 'config', 'user.email', 'test@example.com')
        (self.root / 'shared.txt').write_text('original\n')
        self.upstream = self.commit('upstream')
        self.record(self.upstream)
        (self.root / 'custom.txt').write_text('maintained\n')
        self.base = self.commit('customization')

    def commit(self, message):
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', message)
        return git(self.root, 'rev-parse', 'HEAD')

    def record(self, revision):
        (self.root / '.upstream.json').write_text(json.dumps({
            'repository': 'hotio/base', 'branch': 'workflows', 'revision': revision}, indent=2) + '\n')

    def advance(self):
        git(self.root, 'checkout', '--detach', self.upstream)
        (self.root / 'shared.txt').write_text('new upstream\n')
        result = self.commit('upstream update')
        git(self.root, 'checkout', '--detach', self.base)
        return result


class SyncTests(SyncFixture):
    def test_update_preserves_customization_and_recoverable_bundle(self):
        upstream = self.advance()
        result = prepare(self.root, upstream, 'base-image', 'workflows', self.out)
        self.assertEqual(result['status'], 'prepared')
        self.assertEqual((self.root / 'custom.txt').read_text(), 'maintained\n')
        self.assertEqual((self.root / 'shared.txt').read_text(), 'new upstream\n')
        recovered = Path(self.temp.name) / 'recovered'
        subprocess.run(['git', 'clone', str(self.out / 'candidate.bundle'), str(recovered)], check=True, capture_output=True)
        self.assertEqual(git(recovered, 'rev-parse', 'HEAD'), result['candidate'])
        git(recovered, 'fsck', '--full')
        git(self.root, 'checkout', '--detach', self.base)
        git(self.root, 'apply', '--check', str(self.out / 'candidate.patch'))

    def test_conflict_leaves_original_head_and_worktree(self):
        upstream = self.advance()
        (self.root / 'shared.txt').write_text('maintained alternative\n')
        before = self.commit('local edit')
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            prepare(self.root, upstream, 'base-image', 'workflows', self.out)
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), before)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        self.assertEqual((self.root / 'shared.txt').read_text(), 'maintained alternative\n')
        self.assertFalse(self.out.exists())

    def test_unchanged_has_no_patch_or_commit(self):
        result = prepare(self.root, self.upstream, 'base-image', 'workflows', self.out)
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), self.base)
        self.assertFalse((self.out / 'candidate.patch').exists())

    def test_dirty_clone_rejected(self):
        (self.root / 'untracked').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'clean'):
            prepare(self.root, self.upstream, 'base-image', 'workflows', self.out)

    def test_mismatched_provenance_rejected(self):
        with self.assertRaisesRegex(ValueError, 'provenance'):
            prepare(self.root, self.upstream, 'base-image', 'alpinevpn', self.out)

    def test_missing_provenance_rejected(self):
        git(self.root, 'rm', '.upstream.json')
        self.commit('remove metadata')
        with self.assertRaises(FileNotFoundError):
            prepare(self.root, self.upstream, 'base-image', 'workflows', self.out)

    def test_invalid_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'revision'):
            prepare(self.root, '--all', 'base-image', 'workflows', self.out)


class WebsiteSyncTests(SyncFixture):
    def site_history(self, conflict=None):
        source = Path(__file__).resolve().parent.parent / 'hweb-content'
        git(self.root, 'checkout', '--detach', self.upstream)
        files = ['includes/wireguard.md', 'includes/annotations.md',
                 'docs/javascripts/tablesort.js', 'docs/javascripts/tagcopy.js',
                 'docs/stylesheets/extra-13.css', 'docs/containers/jackett.md',
                 'docs/containers/jackett-tags.json', 'docs/containers/seerr.md',
                 'docs/containers/seerr-tags.json', 'docs/img/image-logos/jackett.svg',
                 'docs/guides/old.md', 'docs/scripts/old.md']
        for name in files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('original\n')
        tags = self.root / 'docs/containers/caddy-tags.json'
        tags.write_text('{"retained":"original"}\n')
        previous = self.commit('website upstream')
        from site_overlay import apply_overlay
        apply_overlay(self.root, source)
        (self.root / '.upstream.json').write_text(json.dumps({
            'repository': 'hotio/website', 'branch': 'master', 'revision': previous}) + '\n')
        if conflict:
            (self.root / conflict).write_text('destination edit\n')
        base = self.commit('website customization')
        git(self.root, 'checkout', '--detach', previous)
        for name in files[5:]:
            (self.root / name).write_text('updated upstream\n')
        (self.root / 'docs/containers/new-upstream-only.md').write_text('new page\n')
        tags.write_text('{"retained":"updated"}\n')
        if conflict:
            (self.root / conflict).write_text('upstream edit\n')
        upstream = self.commit('website upstream update')
        git(self.root, 'checkout', '--detach', base)
        return source, base, upstream

    def test_excluded_modify_delete_and_new_pages_do_not_block_update(self):
        source, base, upstream = self.site_history()
        result = prepare(self.root, upstream, 'website', 'master', self.out, source)
        self.assertEqual(result['base'], base)
        self.assertEqual(result['upstream'], upstream)
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD^'), base)
        self.assertEqual(json.loads((self.root / 'docs/containers/caddy-tags.json').read_text()),
                         {'retained': 'original'})
        self.assertFalse((self.root / 'docs/containers/jackett.md').exists())
        self.assertFalse((self.root / 'docs/containers/seerr-tags.json').exists())
        self.assertFalse((self.root / 'docs/containers/new-upstream-only.md').exists())
        self.assertFalse((self.root / 'docs/guides').exists())
        self.assertFalse((self.root / 'docs/scripts').exists())
        self.assertFalse((self.root / 'docs/img/image-logos/jackett.svg').exists())
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        recovered = Path(self.temp.name) / 'site-recovered'
        subprocess.run(['git', 'clone', str(self.out / 'candidate.bundle'), str(recovered)],
                       check=True, capture_output=True)
        self.assertEqual(git(recovered, 'rev-parse', 'HEAD'), result['candidate'])
        git(recovered, 'fsck', '--full')

    def test_shared_asset_conflicts_still_stop(self):
        for conflict in ('includes/wireguard.md',):
            with self.subTest(conflict=conflict):
                source, base, upstream = self.site_history(conflict)
                with self.assertRaisesRegex(ValueError, 'conflicts'):
                    prepare(self.root, upstream, 'website', 'master', self.out, source)
                self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), base)
                self.assertEqual(git(self.root, 'status', '--porcelain'), '')
                self.assertFalse(self.out.exists())

    def test_destination_tags_and_canonical_pages_win_upstream_edits(self):
        source, base, upstream = self.site_history()
        tags = self.root / 'docs/containers/caddy-tags.json'
        tags.write_text('{"edbfi":"published-digest"}\n')
        self.commit('published destination tags')
        prepare(self.root, upstream, 'website', 'master', self.out, source)
        self.assertEqual(json.loads(tags.read_text()), {'edbfi': 'published-digest'})
        self.assertEqual((self.root / 'docs/containers/caddy.md').read_bytes(),
                         (source / 'docs/containers/caddy.md').read_bytes())
