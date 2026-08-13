from __future__ import annotations

import json
import unittest
from pathlib import Path

from collectors.china_official_collector import SOURCE_DIR, _sha256


class ChinaOfficialManifestTests(unittest.TestCase):
    def test_registered_files_exist_and_match_hash(self):
        manifest = json.loads((SOURCE_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["files"])
        for item in manifest["files"]:
            path = SOURCE_DIR / item["file"]
            self.assertTrue(path.exists(), item["file"])
            self.assertEqual(_sha256(path), item["sha256"])
            self.assertTrue(item["publisher"])
            self.assertTrue(item["source_page"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
