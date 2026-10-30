"""Create a smooth-stop Sparrow AnimBP copy while preserving every existing asset."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
TOOLS = ROOT / 'Tools/CharacterPipeline'
sys.path.insert(0, str(TOOLS))
from baseline import verify

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
SOURCE = '/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown'
SOURCE_RELATIVE = 'Content/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown.uasset'
IDLE_SOURCE = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Travel_Mode_Idle_BowDown'
IDLE_SOURCE_RELATIVE = 'Content/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Travel_Mode_Idle_BowDown.uasset'
IDLE_ASSET = '/Game/TopDown/Characters/Sparrow/Animations/A_Sparrow_TravelIdle'
ASSET = '/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_SmoothStop'
RELATIVE = 'Content/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_SmoothStop.uasset'
OBJECT = ASSET + '.ABP_Sparrow_SmoothStop'
PREFIX = OBJECT + ':AnimGraph.AnimGraphNode_StateMachine_5.Ground Locomotion.'
TARGETS = (('AnimStateTransitionNode_1', 'AnimStateNode_1', 'AnimStateNode_2', .08),
           ('AnimStateTransitionNode_6', 'AnimStateNode_2', 'AnimStateNode_1', .18))
report = {'passed': False, 'asset': ASSET, 'copied_from': SOURCE, 'saved_packages': [], 'changes': []}


def inventory():
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + OUT.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump "' + ASSET + '"')
    value = json.loads((OUT / 'sparrow-native-inventory.json').read_text(encoding='utf-8-sig'))
    asset = next(row for row in value['assets'] if row['path'] == OBJECT)
    graph = next(row for row in asset['graphs'] if row['name'] == 'Ground Locomotion')
    return {row['path'].rsplit('.', 1)[-1]: row for row in graph['nodes']}


def check_link(nodes, name, previous, following):
    row = nodes[name]
    pins = {pin['name']: pin for pin in row['pins']}
    if pins['In']['links'] != [PREFIX + previous + ':Out'] or pins['Out']['links'] != [PREFIX + following + ':In']:
        raise RuntimeError('Private Sparrow transition no longer connects the inspected Idle and Run: ' + name)
    if row['properties']['BlendMode'] != 'HermiteCubic':
        raise RuntimeError('Private Sparrow transition blend curve changed: ' + name)
    return float(row['properties']['CrossfadeDuration'] or 0)


try:
    if not OUT.is_relative_to(ROOT / 'Saved/QA'):
        raise ValueError('Evidence must remain inside Saved/QA')
    baseline_path = os.environ.get('CHARACTER_PIPELINE_BASELINE')
    if baseline_path is None:
        baseline_path = json.loads(Path(os.environ['CHARACTER_PIPELINE_JOB']).read_text(encoding='utf-8'))['baseline']
    baseline = Path(baseline_path)
    report['baseline_before'] = verify(baseline)
    if not report['baseline_before']['passed']:
        raise RuntimeError('Protected baseline changed before Sparrow pose installation')
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError('Baseline Sparrow animation blueprint is unavailable')
    report['source_sha256_before'] = hashlib.sha256((ROOT / SOURCE_RELATIVE).read_bytes()).hexdigest()
    report['sha256_before'] = hashlib.sha256((ROOT / RELATIVE).read_bytes()).hexdigest() if (ROOT / RELATIVE).is_file() else None
    asset = unreal.load_asset(ASSET) or unreal.EditorAssetLibrary.duplicate_asset(SOURCE, ASSET)
    if asset is None:
        raise RuntimeError('Private Sparrow animation blueprint is unavailable')
    report['idle_source_sha256_before'] = hashlib.sha256((ROOT / IDLE_SOURCE_RELATIVE).read_bytes()).hexdigest()
    idle = unreal.load_asset(IDLE_ASSET) or unreal.EditorAssetLibrary.duplicate_asset(IDLE_SOURCE, IDLE_ASSET)
    if not isinstance(idle, unreal.AnimSequence):
        raise RuntimeError('Owned travel-idle copy is unavailable')
    unreal.AnimationLibrary.remove_all_animation_notify_tracks(idle)
    idle.set_editor_property('enable_root_motion', False)
    idle.set_editor_property('force_root_lock', True)
    if not unreal.EditorAssetLibrary.save_loaded_asset(idle, False):
        raise RuntimeError('Could not save new owned travel-idle copy')
    report['saved_packages'].append(IDLE_ASSET)
    report['idle_copy'] = {'asset': IDLE_ASSET, 'source': IDLE_SOURCE, 'length': idle.get_play_length(),
        'cropped': False, 'bone_keys_modified': False, 'root_motion': False, 'force_root_lock': True,
        'animation_notify_tracks_removed': True}
    before = inventory()
    for name, previous, following, duration in TARGETS:
        old = check_link(before, name, previous, following)
        node = unreal.find_object(None, PREFIX + name)
        if node is None:
            raise RuntimeError('Inspected Sparrow transition object is unavailable: ' + name)
        asset.modify()
        node.modify()
        node.set_editor_property('CrossfadeDuration', duration)
        report['changes'].append({'transition': name, 'from': previous, 'to': following,
                                  'duration_before': old, 'duration_after': duration, 'curve': 'HermiteCubic'})
    configuration_path = OUT / 'sparrow-stop-idle-configuration.json'
    if configuration_path.exists():
        configuration_path.unlink()
    unreal.SystemLibrary.execute_console_command(None, 'SparrowStopQA.ConfigureIdle')
    if not configuration_path.is_file():
        raise RuntimeError('SparrowStopQA.ConfigureIdle is unavailable; load the new editor module')
    configuration = json.loads(configuration_path.read_text(encoding='utf-8-sig'))
    report['idle_configuration'] = configuration
    if not configuration.get('passed', False):
        raise RuntimeError('Owned travel-idle configuration failed: ' + configuration.get('error', 'unknown graph mismatch'))
    unreal.BlueprintEditorLibrary.compile_blueprint(asset)
    after = inventory()
    for name, previous, following, duration in TARGETS:
        if abs(check_link(after, name, previous, following) - duration) > .000001:
            raise RuntimeError('Compiled Sparrow transition does not retain requested duration')
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save private Sparrow animation blueprint')
    report['saved_packages'].append(ASSET)
    report['sha256_after'] = hashlib.sha256((ROOT / RELATIVE).read_bytes()).hexdigest()
    report['source_sha256_after'] = hashlib.sha256((ROOT / SOURCE_RELATIVE).read_bytes()).hexdigest()
    report['original_abp_unchanged'] = report['source_sha256_after'] == report['source_sha256_before']
    report['idle_source_sha256_after'] = hashlib.sha256((ROOT / IDLE_SOURCE_RELATIVE).read_bytes()).hexdigest()
    report['original_idle_unchanged'] = report['idle_source_sha256_after'] == report['idle_source_sha256_before']
    report['baseline_after'] = verify(baseline)
    report['passed'] = report['baseline_after']['passed'] and report['original_abp_unchanged'] and report['original_idle_unchanged']
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'sparrow-stop-assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
