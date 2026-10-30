"""Install the user-requested posture variant, saving only declared Sparrow copies."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / 'Tools/CharacterPipeline'))
from baseline import verify

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
profile = json.loads((root / 'Tools/CharacterPipeline/Profiles/sparrow.json').read_text(encoding='utf-8'))
variant = profile['presentation_contract']['pose_variant']
baseline = Path(os.environ['CHARACTER_PIPELINE_BASELINE'])
hero = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations'
dest = '/Game/TopDown/Characters/Sparrow/Animations'
report = {'passed': False, 'mode': 'user_requested_variant', 'original_game_behavior': 'unverified'}
assets = []

def protected_check():
    result = verify(baseline)
    prefix = 'Content/TopDown/Characters/Sparrow/Animations/'
    allowed = {prefix + name + '.uasset' for name in variant['owned_assets']}
    result['allowed_owned_pose_changes'] = [p for p in result['mismatches'] if p in allowed]
    result['mismatches'] = [p for p in result['mismatches'] if p not in allowed]
    result['passed'] = not result['mismatches']
    return result

def duplicate(original, name):
    target = dest + '/' + name
    asset = unreal.load_asset(target) or unreal.EditorAssetLibrary.duplicate_asset(original, target)
    if asset is None:
        raise RuntimeError('Cannot create owned pose copy: ' + target)
    if isinstance(asset, unreal.AnimSequence):
        unreal.AnimationLibrary.remove_all_animation_notify_tracks(asset)
        asset.set_editor_property('enable_root_motion', False)
        asset.set_editor_property('force_root_lock', True)
    assets.append(asset)
    return asset

try:
    report['baseline_before'] = protected_check()
    if not report['baseline_before']['passed']:
        raise RuntimeError('Protected source assets changed before pose installation')
    selection = variant['idle_segment']
    for relative, expected in variant['source_hashes'].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Source pose selection must be remeasured: ' + relative)
    duplicate(hero + '/idle_relaxed', 'A_Sparrow_RelaxedIdle')
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump "' + hero + '/Blendspaces/SprintFwdSlopeLean"')
    inventory = json.loads((qa / 'sparrow-native-inventory.json').read_text(encoding='utf-8-sig'))
    movement = next(a for a in inventory['assets'] if a['path'].endswith('SprintFwdSlopeLean.SprintFwdSlopeLean'))
    for original in sorted({s['animation'] for s in movement['samples']}):
        duplicate(original, 'A_Sparrow_Move_' + original.rsplit('.', 1)[1])
    duplicate(hero + '/Blendspaces/SprintFwdSlopeLean', 'BS_Sparrow_RelaxedMove')
    blueprint = unreal.load_asset(dest + '/ABP_Sparrow_TopDown')
    if blueprint is None:
        raise RuntimeError('Existing Sparrow AnimBP missing')
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None,
        f'SparrowAssetQA.ConfigurePose {selection["start_frame"]} {selection["end_frame"]}')
    configuration = json.loads((qa / 'sparrow-pose-configuration.json').read_text(encoding='utf-8-sig'))
    if not configuration.get('passed'):
        raise RuntimeError('Native pose configuration failed: ' + configuration.get('error', 'pin connection'))
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    assets.append(blueprint)
    for asset in assets:
        if not asset.get_path_name().startswith(dest + '/'):
            raise RuntimeError('Saving source packages is forbidden')
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('Cannot save pose copy: ' + asset.get_path_name())
    report.update(selection=selection, saved_assets=[a.get_path_name() for a in assets],
                  baseline_after=protected_check())
    report['passed'] = report['baseline_after']['passed']
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'pose-installation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
