import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'content-engine'))
import update_feed as engine

class AssetRetention(unittest.TestCase):
    def test_skipped_day_keeps_all_referenced_mobile_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            site = root / 'site'
            images = site / 'images'
            images.mkdir(parents=True)
            (root / 'topics.json').write_text(json.dumps([{'title': 'Test', 'category': 'Naturen'}]))
            names = ['hero.webp', 'hero-small.webp', 'slide.webp', 'slide-small.webp']
            for name in names + ['orphan.webp']:
                (images / name).write_bytes(b'fixture')
            story = {'id': 'old', 'created': '2000-01-01',
                     'image': 'images/hero.webp', 'imageSmall': 'images/hero-small.webp',
                     'slides': [{'image': 'images/slide.webp', 'imageSmall': 'images/slide-small.webp'}]}
            (site / 'feed.json').write_text(json.dumps({'stories': [story]}))
            with patch.object(engine, 'ROOT', root), patch.object(engine, 'SITE', site), patch.object(engine, 'IMAGES', images), patch.object(engine, 'build_story', return_value=None):
                self.assertEqual(engine.run(1), 0)
            self.assertTrue(all((images / name).exists() for name in names))
            self.assertFalse((images / 'orphan.webp').exists())
            self.assertTrue((site / 'automation-state.json').exists())

    def test_skipped_first_day_creates_image_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            site = root / 'site'
            (root / 'topics.json').write_text(json.dumps([{'title': 'Test', 'category': 'Naturen'}]))
            with patch.object(engine, 'ROOT', root), patch.object(engine, 'SITE', site), patch.object(engine, 'IMAGES', site / 'images'), patch.object(engine, 'build_story', return_value=None):
                self.assertEqual(engine.run(1), 0)
            self.assertTrue((site / 'images').is_dir())
