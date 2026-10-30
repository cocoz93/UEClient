"""Filesystem safety checks for private derived-content restoration."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from baseline import PROJECT
from content_bundle import restore


class BundleRestoreChecks(unittest.TestCase):
    def setUp(self):
        folder = PROJECT / 'Saved/QA/CharacterPipeline/tool-check-fixtures'
        folder.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='check-', dir=folder))
        self.destination = self.root / 'project'
        self.bundle = self.root / 'content.zip'

    def pack(self, entries):
        with zipfile.ZipFile(self.bundle, 'w') as archive:
            for name, contents in entries:
                archive.writestr(name, contents)
        return hashlib.sha256(self.bundle.read_bytes()).hexdigest()

    def test_restore_and_reapply_are_identical(self):
        checksum = self.pack([('Content/TopDown/Test.uasset', b'asset'), ('Config/DefaultGame.ini', b'config')])
        self.assertEqual(restore(self.bundle, self.destination, checksum)['created'], 2)
        second = restore(self.bundle, self.destination, checksum)
        self.assertEqual((second['created'], second['unchanged'], second['overwritten']), (0, 2, 0))

    def test_conflict_is_checked_before_any_write(self):
        existing = self.destination / 'Config/DefaultGame.ini'
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b'preserve')
        checksum = self.pack([('Content/TopDown/New.uasset', b'new'), ('Config/DefaultGame.ini', b'different')])
        with self.assertRaises(FileExistsError):
            restore(self.bundle, self.destination, checksum)
        self.assertEqual(existing.read_bytes(), b'preserve')
        self.assertFalse((self.destination / 'Content/TopDown/New.uasset').exists())

    def test_archive_path_escape_is_rejected(self):
        checksum = self.pack([('Config/../../escaped', b'unsafe')])
        with self.assertRaises(ValueError):
            restore(self.bundle, self.destination, checksum)
        self.assertFalse(self.destination.exists())

    def test_wrong_checksum_is_rejected(self):
        self.pack([('Content/TopDown/Test.uasset', b'asset')])
        with self.assertRaises(ValueError):
            restore(self.bundle, self.destination, '0' * 64)
        self.assertFalse(self.destination.exists())


if __name__ == '__main__':
    unittest.main()
