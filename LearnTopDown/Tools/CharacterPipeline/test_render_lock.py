"""A competing job waits; an exited editor wrapper cannot leave an orphan lock."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from render_lock import render_slot

class RenderLockTests(unittest.TestCase):
 def child(self,root,crash=False):
    script='from pathlib import Path; from render_lock import render_slot; import os\nwith render_slot(Path('+repr(str(root))+'),timeout=.2):\n '+('os._exit(17)' if crash else 'pass')
    return subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parent,capture_output=True,timeout=5)
 def test_mutual_exclusion_and_release(self):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        with render_slot(root):
            self.assertNotEqual(self.child(root).returncode,0)
        self.assertEqual(self.child(root).returncode,0)
 def test_process_exit_releases_slot(self):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        self.assertEqual(self.child(root,True).returncode,17)
        with render_slot(root,timeout=.2):pass

if __name__=='__main__':unittest.main()
