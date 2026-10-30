"""S9-10 comparison through the existing actual-arrow review; no second test rig.

SERAPH_S_CASES defaults to S9,S10. Set S4,S9,S10 for a baseline comparison.
SERAPH_S_MODES defaults to normal,form. Each clip is two seconds.
"""
import os
from pathlib import Path
import runpy
import unreal


def sequence(rig):
    previous = {key: os.environ.get(key) for key in ('ARSENAL_RS_CASES', 'ARSENAL_RS_MODES')}
    os.environ['ARSENAL_RS_CASES'] = os.environ.get('SERAPH_S_CASES', 'S9,S10')
    os.environ['ARSENAL_RS_MODES'] = os.environ.get('SERAPH_S_MODES', 'normal,form')
    try:
        path = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/arsenal_rs_review.py'
        yield from runpy.run_path(str(path))['sequence'](rig)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
