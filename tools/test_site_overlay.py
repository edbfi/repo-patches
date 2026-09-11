import json
from pathlib import Path
import tempfile
import unittest
from site_overlay import apply_overlay

SOURCE = Path(__file__).resolve().parent.parent / 'hweb-content'


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for path in ['includes/wireguard.md', 'includes/annotations.md',
                     'docs/javascripts/tablesort.js', 'docs/javascripts/tagcopy.js',
                     'docs/stylesheets/extra-13.css', 'docs/containers/obsolete.md',
                     'docs/containers/obsolete-tags.json', 'docs/img/image-logos/obsolete.svg',
                     'docs/scripts/old.md', 'docs/guides/old.md']:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('inherited')
        (self.root / 'docs/containers/caddy-tags.json').write_text('{"retained": "digest"}\n')

    def test_overlay_preserves_tags_and_dependencies_prunes_excluded_pages(self):
        apply_overlay(self.root, SOURCE)
        self.assertEqual(json.loads((self.root / 'docs/containers/caddy-tags.json').read_text()), {'retained': 'digest'})
        self.assertEqual(json.loads((self.root / 'docs/containers/base-image-tags.json').read_text()), {})
        self.assertEqual((self.root / 'includes/wireguard.md').read_text(), 'inherited')
        self.assertEqual((self.root / 'docs/CNAME').read_text().strip(), 'web.edb.fi')
        self.assertEqual({p.stem for p in (self.root / 'docs/containers').glob('*.md')},
                         {'base-image', 'caddy', 'obzorarr', 'qbittorrent', 'qflood', 'sabnzbd'})
        self.assertFalse((self.root / 'docs/scripts').exists())
        self.assertFalse((self.root / 'docs/img/image-logos/obsolete.svg').exists())
        self.assertTrue((self.root / 'docs/img/image-logos/flood.svg').exists())
        self.assertTrue((self.root / 'overrides/main.html').exists())

    def test_missing_upstream_dependency_rejected(self):
        (self.root / 'includes/wireguard.md').unlink()
        with self.assertRaisesRegex(ValueError, 'inherited'):
            apply_overlay(self.root, SOURCE)

    def test_corrupt_tags_rejected(self):
        (self.root / 'docs/containers/caddy-tags.json').write_text('invalid')
        with self.assertRaises(json.JSONDecodeError):
            apply_overlay(self.root, SOURCE)
