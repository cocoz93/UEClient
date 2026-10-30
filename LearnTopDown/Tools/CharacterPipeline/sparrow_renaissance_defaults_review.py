"""Verify adopted defaults and actual post-shot mouse movement in both forms."""
import json
import os
from pathlib import Path
import runpy
import shutil

import unreal


def sequence(rig):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    environment = runpy.run_path(str(folder / 'sparrow_design_reset_review.py'))['environment']
    expected = {'Sparrow.DesignIngame.Q': 8, 'Sparrow.DesignIngame.V': 7,
                'Sparrow.SunArrow.Style': 6, 'Sparrow.EDesign.Style': 8,
                'Sparrow.FDesign.Style': 7, 'Sparrow.BowMuzzle.Style': 7,
                'Sparrow.Renaissance.W': 0, 'Sparrow.ArsenalStudy.R': 0,
                'Sparrow.ArsenalStudy.S': 0, 'Sparrow.Sharp.Reference': 3}
    actual = {name: unreal.SystemLibrary.get_console_variable_int_value(name) for name in expected}
    rig['check'](actual == expected, 'new process loads all adopted skill defaults without a preview override')
    report = {'passed': False, 'defaults': actual, 'modes': []}
    out = rig['OUT']
    for mode in ('normal', 'form'):
        with environment({'SPARROW_RECOVERY_FORM': '1' if mode == 'form' else '0',
                          'SPARROW_RECOVERY_KEYS': os.environ.get('SPARROW_DEFAULT_REVIEW_KEYS', 'Q,W,E,R,A,S,D,F')}):
            yield from runpy.run_path(str(folder / 'sparrow_recovery_timing.py'))['sequence'](rig)
        destination = out / ('recovery-' + mode + '.json')
        shutil.copyfile(out / 'sparrow-recovery-timing.json', destination)
        data = json.loads(destination.read_text(encoding='utf-8'))
        rig['check'](data['passed'], mode + ' default skills release mouse movement after emission')
        report['modes'].append({'mode': mode, 'passed': data['passed'], 'cases': len(data['cases'])})
    report['passed'] = True
    (out / 'renaissance-defaults.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
