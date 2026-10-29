import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "github_radar.py"
spec = importlib.util.spec_from_file_location("github_radar", SOURCE)
radar = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = radar
spec.loader.exec_module(radar)

NOW = datetime(2026, 10, 29, 11, 0, tzinfo=timezone.utc)
RSS = b"""<rss version="2.0"><channel>
<item><title>OpenAI launches new tools for scientists</title><link>https://openai.com/news/science</link><description>Official announcement.</description><pubDate>Wed, 28 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Nvidia launches new speech model</title><link>https://nvidia.com/news/speech</link><pubDate>Wed, 28 Oct 2026 09:00:00 GMT</pubDate></item>
<item><title>Old model from months ago</title><link>https://nvidia.com/old</link><pubDate>Wed, 01 Jul 2026 09:00:00 GMT</pubDate></item>
</channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Google reveals a new AI research study</title><link href="https://blog.google/ai/study" rel="alternate"/><updated>2026-10-27T12:00:00Z</updated><summary>New work</summary></entry>
<entry><title>Meta reveals AI safety assessment</title><link href="https://about.meta.com/ai"/><updated>2026-10-26T12:00:00Z</updated></entry>
</feed>"""

class BackupTests(unittest.TestCase):
    def test_rss_and_atom(self):
        self.assertEqual(len(radar.parse_feed(RSS, "RSS")), 3)
        self.assertEqual(len(radar.parse_feed(ATOM, "ATOM")), 2)
    def test_old_items_excluded(self):
        selected = radar.select(radar.parse_feed(RSS,"RSS")+radar.parse_feed(ATOM,"ATOM"),[],NOW)
        self.assertFalse(any("months ago" in x["headline_original"] for x in selected))
        self.assertTrue(all(x["published"] is False and x["media_rights_verified"] is False for x in selected))
    def test_episode_overlap_excluded(self):
        episode={"numero":17,"descripcion":"Esta semana: 1. OpenAI launches new tools for scientists | 2. Anthropic opens new platform. Fuentes: https://example.com/"}
        selected=radar.select(radar.parse_feed(RSS,"RSS"),[episode],NOW)
        self.assertFalse(any("OpenAI launches new tools" in x["headline_original"] for x in selected))
    def test_partial_source_failure(self):
        def reader(url):
            if "broken" in url: raise TimeoutError()
            return RSS
        report=radar.build({"ok":"https://example.com/feed","broken":"https://example.com/broken"},[],NOW,reader)
        self.assertEqual(report["sources_ok"],1)
        self.assertIn("broken",report["sources_failed"])
        self.assertFalse(report["published"])
    def test_all_sources_fail(self):
        with self.assertRaises(RuntimeError):
            radar.build({"bad":"https://example.com"},[],NOW,lambda _: (_ for _ in ()).throw(TimeoutError()))
    def test_no_private_media_or_meta(self):
        report=radar.build({"ok":"https://example.com/feed"},[],NOW,lambda _: RSS)
        self.assertFalse(report["media_licensing_verified"])
        self.assertEqual(report["account"],"inteligenciaartificialaldia")

if __name__ == "__main__":
    unittest.main()
