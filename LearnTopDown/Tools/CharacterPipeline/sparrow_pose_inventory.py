"""Evaluate original Sparrow poses without inferring stance from asset filenames."""
import hashlib
import json
import os
import math
from pathlib import Path
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
if not qa.is_relative_to(root / 'Saved/QA'):
    raise ValueError('Pose evidence must remain in Saved/QA')
hero = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
report = {'passed': False, 'read_only': True, 'clips': []}
try:
    mesh = unreal.load_asset(hero + '/Skins/Rogue/Meshes/Sparrow_Rogue')
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', mesh)
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    for name in ('idle', 'idle_relaxed', 'Jog_Fwd', 'Sprint_Fwd'):
        animation = unreal.load_asset(hero + '/Animations/' + name)
        length = animation.get_play_length()
        filename = root / 'Content' / (animation.get_path_name().split('.')[0][6:] + '.uasset')
        row = {'asset': animation.get_path_name(), 'length': length,
               'sha256': hashlib.sha256(filename.read_bytes()).hexdigest(), 'samples': []}
        for step in range(11):
            seconds = min(length - 0.00001, length * step / 10)
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, seconds, options)
            bones = {}
            for bone in ('root', 'pelvis', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r'):
                transform = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
                v = transform.translation
                bones[bone] = [v.x, v.y, v.z]
            row['samples'].append({'time': seconds, 'bones_component_space': bones,
                'head_minus_draw_hand_z': bones['head'][2] - bones['hand_r'][2]})
        report['clips'].append(row)
    paths = [hero + '/Animations/Blendspaces/' + name for name in ('JogFwdSlopeLean', 'SprintFwdSlopeLean')]
    relaxed = unreal.load_asset(hero + '/Animations/idle_relaxed')
    seconds_per_frame = unreal.AnimationLibrary.get_time_at_frame(relaxed, 1)
    dense = []
    bones_to_match = ('pelvis', 'spine_03', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r')
    for frame in range(round(6 / seconds_per_frame), round(27 / seconds_per_frame) + 1, 3):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(relaxed, frame * seconds_per_frame, options)
        positions = []
        rotations = []
        for bone in bones_to_match:
            t = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
            v, q = t.translation, t.rotation
            positions.append([v.x, v.y, v.z])
            rotations.append([q.x, q.y, q.z, q.w])
        dense.append({'frame': frame, 'positions': positions, 'rotations': rotations,
                      'head_minus_draw_hand_z': positions[2][2] - positions[4][2]})
    best = None
    for i, first in enumerate(dense):
        for last in dense[i + 1:]:
            duration = (last['frame'] - first['frame']) * seconds_per_frame
            if not 5 <= duration <= 15:
                continue
            if any(s['head_minus_draw_hand_z'] < 30 for s in dense[i:] if s['frame'] <= last['frame']):
                continue
            errors = [math.dist(a, b) for a, b in zip(first['positions'], last['positions'])]
            angles = [math.degrees(2 * math.acos(min(1.0, abs(sum(x * y for x, y in zip(a, b))))))
                      for a, b in zip(first['rotations'], last['rotations'])]
            score = sum(errors) / len(errors) + 0.05 * sum(angles) / len(angles)
            if best is None or score < best['score']:
                best = {'source': relaxed.get_path_name(), 'start_frame': first['frame'],
                        'end_frame': last['frame'], 'seconds_per_frame': seconds_per_frame,
                        'duration': duration, 'score': score, 'bones': bones_to_match,
                        'boundary_position_errors_cm': errors, 'boundary_angles_degrees': angles,
                        'minimum_head_minus_draw_hand_z': min(s['head_minus_draw_hand_z'] for s in dense[i:] if s['frame'] <= last['frame'])}
    if best is None:
        raise RuntimeError('No source relaxed segment keeps the draw hand lowered')
    report['relaxed_loop_selection'] = best
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + p + '"' for p in paths))
    report['passed'] = len(report['clips']) == 4
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'pose-inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
