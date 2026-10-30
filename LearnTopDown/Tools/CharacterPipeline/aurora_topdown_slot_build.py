"""Add the AuroraFullBody skill slot right before the output of Aurora's own TopDown anim blueprint
(/Game/TopDown/Characters/Aurora/Animations/ABP_Aurora_TopDown, AuroraAssetQA.InstallFullBodySlot) and save it.
Skills then play as montages in that slot so their start and end blend with walking (same as the Countess copy)."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ASSET = '/Game/TopDown/Characters/Aurora/Animations/ABP_Aurora_TopDown'
report = {'passed': False, 'asset': ASSET}


def run(text):
    unreal.SystemLibrary.execute_console_command(None, text)


try:
    run('CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
    asset = unreal.load_asset(ASSET)
    if asset is None:
        raise RuntimeError('ABP_Aurora_TopDown is missing (run aurora_topdown_anim_build.py first)')
    run('AuroraAssetQA.InstallFullBodySlot ' + ASSET + '.ABP_Aurora_TopDown')
    slot = json.loads((qa / 'aurora-slot.json').read_text(encoding='utf-8-sig'))
    report['slot'] = slot
    if not slot.get('passed'):
        raise RuntimeError('Slot install failed (the output pose is not a single link)')
    if slot.get('installed') and not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ABP_Aurora_TopDown')
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'aurora-topdown-slot.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
