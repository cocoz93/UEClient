"""Make Aurora's own TopDown anim blueprint: copy the original Paragon Aurora_AnimBlueprint (left untouched) to
/Game/TopDown/Characters/Aurora/Animations/ABP_Aurora_TopDown, link Idle<->Run directly like the Countess copy
(AuroraAssetQA.RewireTopDownLocomotion), save it, and dump its state machines for the record."""
import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = '/Game/ParagonAurora/Characters/Heroes/Aurora/Aurora_AnimBlueprint'
SOURCE_FILE = ROOT / 'Content/ParagonAurora/Characters/Heroes/Aurora/Aurora_AnimBlueprint.uasset'
ASSET = '/Game/TopDown/Characters/Aurora/Animations/ABP_Aurora_TopDown'
report = {'passed': False, 'source': SOURCE, 'asset': ASSET}


def run(text):
    unreal.SystemLibrary.execute_console_command(None, text)


try:
    report['source_sha256_before'] = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
    run('CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
    asset = unreal.load_asset(ASSET)
    report['copied'] = asset is None
    if asset is None:
        asset = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, ASSET)
    if asset is None:
        raise RuntimeError('Could not copy the Aurora anim blueprint')
    run('AuroraAssetQA.RewireTopDownLocomotion ' + ASSET + '.ABP_Aurora_TopDown')
    rewire = json.loads((qa / 'aurora-rewire.json').read_text(encoding='utf-8-sig'))
    report['rewire'] = rewire
    if not rewire.get('passed'):
        raise RuntimeError('Rewire failed (already rewired, or graph differs from the inspected original)')
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ABP_Aurora_TopDown')
    run('AuroraAssetQA.DumpStateMachines ' + ASSET + '.ABP_Aurora_TopDown')
    report['source_sha256_after'] = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
    report['original_unchanged'] = report['source_sha256_after'] == report['source_sha256_before']
    report['passed'] = report['original_unchanged']
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'aurora-topdown-anim.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
