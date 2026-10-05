import json
from pathlib import Path
import tempfile
import unittest
from site_overlay import apply_overlay, container_page

SOURCE = Path(__file__).resolve().parent.parent / 'hweb-content'
TABLE = b'<tbody id="tags-table-body">\n<tr><td>published</td></tr>\n</tbody>'


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
        # Hotio's own tag data for a container edbfi also publishes.
        (self.root / 'docs/containers/caddy-tags.json').write_text('{"hotio": "digest"}\n')
        self.published = {'docs/containers/caddy-tags.json': b'{"retained": "digest"}\n',
                          'docs/containers/caddy.md': b'old page\n' + TABLE + b'\nold footer\n'}

    def overlay(self):
        apply_overlay(self.root, SOURCE, self.published.get)

    def test_overlay_preserves_tags_and_dependencies_prunes_excluded_pages(self):
        self.overlay()
        self.assertEqual(json.loads((self.root / 'docs/containers/caddy-tags.json').read_text()), {'retained': 'digest'})
        self.assertEqual(json.loads((self.root / 'docs/containers/base-image-tags.json').read_text()), {})
        self.assertEqual((self.root / 'includes/wireguard.md').read_text(), 'inherited')
        self.assertEqual((self.root / 'docs/CNAME').read_text().strip(), 'web.edb.fi')
        self.assertEqual({p.stem for p in (self.root / 'docs/containers').glob('*.md')},
                         {'base-image', 'caddy', 'obzorarr', 'otpravkarr', 'qbittorrent', 'qflood', 'sabnzbd', 'zondarr'})
        self.assertFalse((self.root / 'docs/scripts').exists())
        self.assertFalse((self.root / 'docs/img/image-logos/obsolete.svg').exists())
        self.assertTrue((self.root / 'docs/img/image-logos/flood.svg').exists())
        self.assertTrue((self.root / 'overrides/main.html').exists())

    def test_hotio_tag_data_is_never_kept(self):
        del self.published['docs/containers/caddy-tags.json']
        self.overlay()
        self.assertEqual((self.root / 'docs/containers/caddy-tags.json').read_bytes(), b'{}\n')

    def test_published_tags_table_replaces_the_seed_table(self):
        self.overlay()
        page = (self.root / 'docs/containers/caddy.md').read_bytes()
        canonical = (SOURCE / 'docs/containers/caddy.md').read_bytes()
        start = canonical.index(b'<tbody id="tags-table-body">')
        self.assertEqual(page[:start], canonical[:start])
        self.assertIn(TABLE, page)
        self.assertNotIn(b'old page', page)
        self.assertEqual(page.count(b'<tbody id="tags-table-body">'), 1)
        self.assertEqual((self.root / 'docs/containers/zondarr.md').read_bytes(),
                         (SOURCE / 'docs/containers/zondarr.md').read_bytes())

    def test_page_without_a_table_needs_none_published(self):
        self.assertEqual(container_page(b'no table', None), b'no table')
        self.assertEqual(container_page(b'no table', b'no table either'), b'no table')
        with self.assertRaisesRegex(ValueError, 'no tags table'):
            container_page(b'no table', TABLE)

    def test_missing_upstream_dependency_rejected(self):
        (self.root / 'includes/wireguard.md').unlink()
        with self.assertRaisesRegex(ValueError, 'inherited'):
            self.overlay()

    def test_corrupt_tags_rejected(self):
        self.published['docs/containers/caddy-tags.json'] = b'invalid'
        with self.assertRaises(json.JSONDecodeError):
            self.overlay()
