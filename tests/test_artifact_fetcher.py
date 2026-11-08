import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.fetch_reference_artifact import md5, EXPECTED_MD5

class ArtifactFetcherTests(unittest.TestCase):
    def test_md5_matches_known_payload(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'payload.bin'
            p.write_bytes(b'abc')
            self.assertEqual(md5(p), hashlib.md5(b'abc').hexdigest())
    def test_expected_md5_is_32_hex_chars(self):
        self.assertEqual(len(EXPECTED_MD5),32)
        int(EXPECTED_MD5,16)

if __name__=='__main__': unittest.main()
