"""Read-only original/private Sparrow pose-space and travel-mode candidate measurements."""
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
HERO = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
ORIGINAL = HERO + '/Animations'
PRIVATE = '/Game/TopDown/Characters/Sparrow/Animations'
BONES = ('root', 'pelvis', 'spine_03', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r')
report = {'passed': False, 'read_only': True, 'saved_assets': [], 'clips': [],
    'evaluation_note': 'RAW pose; incorporate_root_motion_into_pose=False respects asset force-root-lock; True deliberately ignores root lock for comparison',
    'style_acceptance_decided': False}


def file_for(path):
    return ROOT / 'Content' / (path.removeprefix('/Game/').split('.')[0] + '.uasset')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serial_property(asset, name):
    try:
        value = asset.get_editor_property(name)
        return value if isinstance(value, (bool, int, float, str)) or value is None else str(value)
    except Exception as error:
        return {'unavailable': str(error)}


def transform_row(transform):
    p, q = transform.translation, transform.rotation
    return {'translation': [p.x, p.y, p.z], 'rotation_quaternion': [q.x, q.y, q.z, q.w]}


def sample_pose(asset, seconds, options):
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(asset, seconds, options)
    if not unreal.AnimPoseExtensions.is_valid(pose):
        raise RuntimeError('Invalid evaluated pose: ' + asset.get_path_name())
    bones = {name: transform_row(unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.WORLD))
             for name in BONES}
    return {'time': seconds, 'bones_component_space': bones,
        'head_minus_draw_hand_z': bones['head']['translation'][2] - bones['hand_r']['translation'][2]}


def mean_point(points):
    return [statistics.fmean(p[axis] for p in points) for axis in range(3)]


def summary(samples):
    rows = {}
    for bone in BONES:
        points = [sample['bones_component_space'][bone]['translation'] for sample in samples]
        rows[bone] = {'mean': mean_point(points), 'minimum': [min(p[i] for p in points) for i in range(3)],
                      'maximum': [max(p[i] for p in points) for i in range(3)],
                      'first_to_last_distance_cm': math.dist(points[0], points[-1])}
    gaps = [sample['head_minus_draw_hand_z'] for sample in samples]
    return {'bones': rows, 'head_minus_draw_hand_z_min': min(gaps), 'head_minus_draw_hand_z_mean': statistics.fmean(gaps),
            'head_minus_draw_hand_z_max': max(gaps)}


try:
    if not OUT.is_relative_to(ROOT / 'Saved/QA'):
        raise ValueError('Evidence must remain inside Saved/QA')
    OUT.mkdir(parents=True, exist_ok=True)
    source_directory = ROOT / 'Content/ParagonSparrow/Characters/Heroes/Sparrow/Animations'
    paths = []
    inventory = []
    for file in sorted(source_directory.glob('*.uasset')):
        name = file.stem
        if name.startswith(('Walk', 'walk', 'Run', 'run', 'Jog_Fwd', 'Sprint_Fwd', 'Travel_')) or \
                name in ('idle', 'idle_relaxed', 'Sparrow_TravelMode_Corrective'):
            path = ORIGINAL + '/' + name
            inventory.append({'name': name, 'path': path, 'sha256': digest(file)})
            paths.append(path)
    report['candidate_asset_inventory'] = inventory
    mandatory = [PRIVATE + '/A_Sparrow_RelaxedIdle', PRIVATE + '/A_Sparrow_Move_Sprint_Fwd',
        ORIGINAL + '/idle', ORIGINAL + '/idle_relaxed', ORIGINAL + '/Sprint_Fwd', ORIGINAL + '/Sprint_Fwd_Stop',
        ORIGINAL + '/Travel_Mode_Idle_BowDown', ORIGINAL + '/Travel_mode_Idle']
    private_directory = ROOT / 'Content/TopDown/Characters/Sparrow/Animations'
    paths += [PRIVATE + '/' + file.stem for file in sorted(private_directory.glob('A_Sparrow_Move_*.uasset'))]
    paths += mandatory
    paths = sorted(set(paths))
    hashes_before = {str(file_for(path).relative_to(ROOT)): digest(file_for(path)) for path in paths}
    mesh = unreal.load_asset(HERO + '/Skins/Rogue/Meshes/Sparrow_Rogue')
    if mesh is None:
        raise RuntimeError('Actual Rogue appearance mesh is unavailable')
    report['mesh'] = mesh.get_path_name()
    for path in paths:
        asset = unreal.load_asset(path)
        if not isinstance(asset, unreal.AnimSequence):
            raise RuntimeError('Candidate is not an animation sequence: ' + path)
        length = asset.get_play_length()
        times = {min(length - .00001, length * index / 32) for index in range(33)}
        if asset.get_name() == 'idle_relaxed':
            times |= {unreal.AnimationLibrary.get_time_at_frame(asset, frame) for frame in range(183, 337, 15)}
            times |= {unreal.AnimationLibrary.get_time_at_frame(asset, frame) for frame in (183, 336)}
        row = {'path': path, 'class': asset.get_class().get_name(), 'length_seconds': length,
            'asset_properties': {name: serial_property(asset, name) for name in
                ('enable_root_motion', 'force_root_lock', 'root_motion_root_lock', 'additive_anim_type',
                 'ref_pose_type', 'ref_frame_index', 'rate_scale')}, 'evaluations': []}
        report['clips'].append(row)
        for incorporate in (True, False):
            options = unreal.AnimPoseEvaluationOptions()
            options.set_editor_property('optional_skeletal_mesh', mesh)
            options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
            options.set_editor_property('extract_root_motion', False)
            options.set_editor_property('incorporate_root_motion_into_pose', incorporate)
            samples = [sample_pose(asset, seconds, options) for seconds in sorted(times)]
            row['evaluations'].append({'mode': 'raw_root_lock_ignored' if incorporate else 'raw_asset_root_lock_respected',
                'incorporate_root_motion_into_pose': incorporate, 'extract_root_motion': False,
                'samples': samples, 'summary': summary(samples)})
    evaluated = {row['path']: row for row in report['clips']}
    report['mandatory_candidates_evaluated'] = all(path in evaluated for path in mandatory)
    move = evaluated[PRIVATE + '/A_Sparrow_Move_Sprint_Fwd']['evaluations'][1]['summary']['bones']
    current_idle = evaluated[PRIVATE + '/A_Sparrow_RelaxedIdle']['evaluations'][1]['summary']['bones']
    comparisons = []
    for path, row in evaluated.items():
        result = row['evaluations'][1]['summary']
        comparisons.append({'path': path, 'head_minus_draw_hand_z_min': result['head_minus_draw_hand_z_min'],
            'mean_xy_distance_to_current_move_cm': {bone: math.dist(result['bones'][bone]['mean'][:2], move[bone]['mean'][:2])
                for bone in ('pelvis', 'head')},
            'mean_xy_distance_to_current_idle_cm': {bone: math.dist(result['bones'][bone]['mean'][:2], current_idle[bone]['mean'][:2])
                for bone in ('pelvis', 'head')},
            'loop_boundary_distance_cm': {bone: result['bones'][bone]['first_to_last_distance_cm']
                for bone in ('pelvis', 'head', 'foot_l', 'foot_r')}})
    report['candidate_measured_comparisons'] = comparisons
    dump_paths = [HERO + '/Sparrow_AnimBlueprint', PRIVATE + '/ABP_Sparrow_SmoothStop',
                  ORIGINAL + '/Blendspaces/SprintFwdSlopeLean', ORIGINAL + '/Blendspaces/JogFwdSlopeLean',
                  PRIVATE + '/BS_Sparrow_RelaxedMove']
    for path in dump_paths:
        if unreal.load_asset(path) is None:
            raise RuntimeError('Required graph/blendspace inspection asset unavailable: ' + path)
        hashes_before[str(file_for(path).relative_to(ROOT))] = digest(file_for(path))
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + OUT.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + path + '"' for path in dump_paths))
    report['graph_inventory'] = str(OUT / 'sparrow-native-inventory.json')
    changed = [name for name, sha in hashes_before.items() if digest(ROOT / name) != sha]
    report['read_only_file_integrity'] = {'passed': not changed, 'checked': len(hashes_before), 'changed': changed,
                                        'input_sha256': hashes_before}
    report['passed'] = report['mandatory_candidates_evaluated'] and not changed
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'sparrow-stop-pose-probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
