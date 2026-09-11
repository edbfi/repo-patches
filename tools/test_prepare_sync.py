import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from prepare_sync import prepare, git


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.out = Path(self.temp.name) / 'evidence'
        git(self.root, 'init', '-b', 'main')
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
