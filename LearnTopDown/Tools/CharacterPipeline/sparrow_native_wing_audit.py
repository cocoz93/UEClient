"""Read Serath's original skeletal wing clips; never modify or save assets."""
import json
from pathlib import Path

import unreal


BASE = '/Game/ParagonSerath/Characters/Heroes/Serath/'
CLIPS = ('Wings_Unfold', 'Wings_Fold', 'Idle_Pose_Wings', 'Idle_Wings',
         'E_Ability_Wing_Flap_Holy', 'E_Ability_Wing_Flap', 'E_Ability_Tucked_Pose')


def xyz(value):
    return [round(value.x, 5), round(value.y, 5), round(value.z, 5)]


def author(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    mesh = unreal.load_asset(BASE + 'Meshes/Serath')
    skeleton = mesh.get_editor_property('skeleton') if mesh else None
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', mesh)
    options.set_editor_property('extract_root_motion', False)
    report = {'passed': False, 'read_only': True, 'assets_saved': False,
              'mesh': mesh.get_path_name() if mesh else None,
              'skeleton': skeleton.get_path_name() if skeleton else None, 'clips': []}
    for name in CLIPS:
        clip = unreal.load_asset(BASE + 'Animations/' + name)
        row = {'name': name, 'path': BASE + 'Animations/' + name,
               'valid': isinstance(clip, unreal.AnimSequence), 'samples': []}
        report['clips'].append(row)
        if not row['valid']:
            continue
        row['same_skeleton'] = clip.get_editor_property('skeleton') == skeleton
        row['length'] = clip.get_play_length()
        row['rate_scale'] = clip.get_editor_property('rate_scale')
        row['additive_type'] = str(clip.get_editor_property('additive_anim_type'))
        names = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(clip)]
        row['wing_tracks'] = [n for n in names if 'wing' in n.lower()]
        moments = [min(i / 30., row['length']) for i in range(int(row['length'] * 30.) + 2)]
        for moment in sorted(set(moments)):
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(clip, moment, options)
            selected = ['root', 'spine_03'] + row['wing_tracks']
            bones = {n: xyz(unreal.AnimPoseExtensions.get_bone_pose(
                pose, n, unreal.AnimPoseSpaces.WORLD).translation) for n in selected}
            anchor = unreal.AnimPoseExtensions.get_bone_pose(pose, 'spine_03', unreal.AnimPoseSpaces.WORLD)
            row['samples'].append({'time': round(moment, 5), 'component_bones': bones,
                                   'spine_rotation': [round(v, 6) for v in (
                                       anchor.rotation.x, anchor.rotation.y, anchor.rotation.z, anchor.rotation.w)]})
    report['passed'] = bool(mesh) and all(r['valid'] and r.get('same_skeleton') and r['samples']
                                        for r in report['clips'])
    target = out / 'serath-native-wing-audit.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'passed': report['passed'], 'read_only': True, 'assets_saved': False, 'report': str(target)}
