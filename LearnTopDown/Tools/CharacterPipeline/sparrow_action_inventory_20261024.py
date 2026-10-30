"""Read-only project action inventory and source-motion auditions.

author(out) records every registered project animation, loads the complete
Sparrow source-animation folder and selected donor actions, and samples poses.
sequence(rig) displays original animations on their matching source meshes.
It installs no move, composite attack, animation asset, material, or retarget.
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy

import unreal


SPARROW = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
ROGUE = SPARROW + '/Skins/Rogue/Meshes/Sparrow_Rogue'
HERO = '/Game/Paragon{0}/Characters/Heroes/{0}'
SOURCE_ACTIONS = (
    ('M01_primary_fast', 'Primary_Fire_Fast', '빠른 기본 사격 원본'),
    ('M02_heavy_release', 'RMB_Fire', '강한 단발 사격 원본'),
    ('M03_ultimate_fire', 'R_Ability_Med_Fire', '궁극 사격 원본'),
    ('M04_sky_fire', 'Q_Ability', '하늘 사격과 원본 후속 동작'),
    ('M05_back_jog', 'Jog_Bwd', '뒤로 이동하는 원본: 사격은 포함하지 않음'),
    ('M06_spin_cw', 'Jog_FwdToBwd_SpinCW', '방향 전환 회전: 사격은 포함하지 않음'),
    ('M07_spin_ccw', 'Jog_BwdToFwd_SpinCCW', '반대 방향 회전: 사격은 포함하지 않음'),
    ('M08_bow_balance', 'Emote_BowBalance_Rouge', '활 균형 이모트: 공격으로 편집 가능한지 검토'),
    ('M09_handstand', 'Emote_Handstand_T3', '곡예 이모트 원본: 짧은 도약 구간 후보'),
    ('M10_kick_dust', 'Emote_Taunt_KickUpDust_M2', '발차기 이모트 원본: 짧은 근접 모션 후보'),
    ('M11_bow_emote', 'Emote_Bow_M1', 'Bow 이모트: 활 타격인지 이름으로 단정하지 않음'),
)
DONORS = (
    ('M12_aurora_back', HERO.format('Aurora') + '/Animations/Ability_RMB_Bwd', HERO.format('Aurora') + '/Meshes/Aurora', 'Aurora 후방 회피 원본'),
    ('M13_aurora_air', HERO.format('Aurora') + '/Animations/Melee_Attack_Air', HERO.format('Aurora') + '/Meshes/Aurora', 'Aurora 공중 근접 원본'),
    ('M14_countess_cut', HERO.format('Countess') + '/Animations/Primary_Attack_B_Normal_InMotion', HERO.format('Countess') + '/Meshes/SM_Countess', 'Countess 이동 검격 원본'),
    ('M15_yin_air', HERO.format('Yin') + '/Animations/Primary_Attack_In_Air', HERO.format('Yin') + '/Meshes/Yin', 'Yin 공중 공격 원본'),
    ('M16_manny_dash', '/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash', '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple', 'Manny 대시 원본'),
    ('M17_quaternius_roll', '/Game/TopDown/Characters/Sparrow/Mobility/Quaternius/AS_QuaterniusRoll', '/Game/TopDown/Characters/Sparrow/Mobility/Quaternius/SK_QuaterniusRoll', '현재 보유한 Quaternius 구르기 원본'),
)


def _object_path(obj):
    return obj.get_path_name() if obj else None


def _property(obj, name):
    try:
        value = obj.get_editor_property(name)
        if isinstance(value, (str, int, float, bool, type(None))):
            return value
        return _object_path(value) if hasattr(value, 'get_path_name') else str(value)
    except Exception as error:
        return {'unavailable': str(error)}


def _sample(anim, mesh=None, count=17):
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    if mesh:
        options.set_editor_property('optional_skeletal_mesh', mesh)
    first = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, 0., options)
    bones = set(str(n) for n in unreal.AnimPoseExtensions.get_bone_names(first))
    selected = [n for n in ('root', 'pelvis', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r') if n in bones]
    samples = []
    for i in range(count):
        t = max(0., min(anim.get_play_length() - 0.00001, anim.get_play_length()*i/(count-1)))
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, options)
        row = {'seconds': round(t, 5), 'bones_component_space': {}}
        for name in selected:
            value = unreal.AnimPoseExtensions.get_bone_pose(pose, name, unreal.AnimPoseSpaces.WORLD)
            v, q = value.translation, value.rotation
            row['bones_component_space'][name] = {'position': [round(v.x, 3), round(v.y, 3), round(v.z, 3)], 'quaternion': [round(q.x, 5), round(q.y, 5), round(q.z, 5), round(q.w, 5)]}
        samples.append(row)
    return samples


def _categories(name):
    matches = []
    for category, pattern in (
        ('shoot_or_attack', r'(primary|attack|fire|melee)'),
        ('ability', r'(ability|rmb|cast)'),
        ('evasion_or_traversal_name_candidate', r'(roll|dash|dodge|slide|vault|leap|jump|bound)'),
        ('turn_or_back_movement', r'(spin|pivot|turn|bwd)'),
        ('emote_segment_candidate', r'(emote|taunt)'),
    ):
        if re.search(pattern, name, re.I):
            matches.append(category)
    return matches


def author(out):
    out = Path(out).resolve()
    root = Path(unreal.Paths.project_dir()).resolve()
    assert out.is_relative_to(root/'Saved/QA')
    out.mkdir(parents=True, exist_ok=True)
    if os.environ.get('SPARROW_ACTION_Q_ONLY') == '1':
        mesh = unreal.load_asset(ROGUE)
        rows = []
        for name in ('Q_Ability', 'Q_Ability_Targeting', 'Travel_Mode_Idle_BowDown', 'idle', 'idle_relaxed'):
            animation = unreal.load_asset(SPARROW+'/Animations/'+name)
            row = {'name': name, 'path': animation.get_path_name(), 'length_seconds': animation.get_play_length(), 'skeleton': _object_path(animation.get_editor_property('skeleton')), 'pose_samples': _sample(animation, mesh, 61 if name == 'Q_Ability' else 5)}
            if name == 'Q_Ability':
                times, values = unreal.AnimationLibrary.get_float_keys(animation, 'DissolveAmount')
                row['arrow_dissolve_curve'] = {'times': list(times), 'values': list(values)}
                row['notifies'] = [{'name': str(n.get_editor_property('notify_name')), 'time': unreal.AnimationLibrary.get_anim_notify_event_trigger_time(n)} for n in unreal.AnimationLibrary.get_animation_notify_events(animation)]
            rows.append(row)
        result = {'passed': True, 'read_only': True, 'assets_saved': False, 'clips': rows}
        (out/'sparrow-q-source-motion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    rows = []
    # Registry enumeration covers ALL project roots, including action clips
    # whose folders are not named Animations. Name tags remain candidate hints.
    for data in registry.get_assets_by_path('/Game', recursive=True):
        klass = str(data.asset_class_path.asset_name)
        if klass not in ('AnimSequence', 'AnimMontage', 'AnimComposite', 'BlendSpace', 'BlendSpace1D'):
            continue
        path = str(data.package_name)
        tags = {}
        for tag in ('Skeleton', 'SequenceLength', 'NumFrames', 'RateScale', 'AdditiveAnimType'):
            try:
                tags[tag] = str(data.get_tag_value(tag))
            except Exception:
                pass
        rows.append({'path': path, 'class': klass, 'name_categories': _categories(str(data.asset_name)), 'registry_tags': tags})
    rows.sort(key=lambda x: x['path'])
    mesh = unreal.load_asset(ROGUE)
    reference = mesh.get_editor_property('skeleton')
    load_paths = {r['path'] for r in rows if r['path'].startswith(SPARROW+'/Animations/') and r['class'] == 'AnimSequence'}
    load_paths.update(path for _, path, _, _ in DONORS)
    # Include all non-additive donor combat and traversal candidates in metadata.
    # Loading individual candidates gives exact duration/skeleton rather than
    # treating a filename match as animation or retarget compatibility proof.
    for row in rows:
        name = row['path'].rsplit('/', 1)[-1]
        if row['class'] != 'AnimSequence' or row['path'].startswith('/Game/ParagonMinions/'):
            continue
        categories = row['name_categories']
        if any(c in categories for c in ('shoot_or_attack', 'ability', 'evasion_or_traversal_name_candidate')) and not re.search(r'(MSA|Additive|_Add$|AimOffset|Targeting|Recovery|Slow|Fast|^Jog|^Sprint)', name, re.I):
            load_paths.add(row['path'])
    detail = []
    pose_paths = {SPARROW+'/Animations/'+name for _, name, _ in SOURCE_ACTIONS}
    pose_paths.update(path for _, path, _, _ in DONORS)
    for path in sorted(load_paths):
        anim = unreal.load_asset(path)
        if not isinstance(anim, unreal.AnimSequence):
            detail.append({'path': path, 'present': bool(anim), 'is_anim_sequence': False})
            continue
        skel = anim.get_editor_property('skeleton')
        filename = root/'Content'/(path[6:]+'.uasset')
        row = {'path': path, 'present': True, 'is_anim_sequence': True, 'skeleton': _object_path(skel), 'same_skeleton_as_sparrow': skel == reference, 'length_seconds': anim.get_play_length(), 'name_categories': _categories(anim.get_name()), 'root_motion': _property(anim, 'enable_root_motion'), 'additive_type': _property(anim, 'additive_anim_type'), 'rate_scale': _property(anim, 'rate_scale'), 'sha256': hashlib.sha256(filename.read_bytes()).hexdigest() if filename.exists() else None}
        if path in pose_paths:
            row['pose_samples'] = _sample(anim, mesh if skel == reference else None)
        if path == SPARROW+'/Animations/Q_Ability':
            row['pose_samples'] = _sample(anim, mesh, 61)
            row['notifies'] = [{'name': str(n.get_editor_property('notify_name')), 'time': unreal.AnimationLibrary.get_anim_notify_event_trigger_time(n)} for n in unreal.AnimationLibrary.get_animation_notify_events(anim)]
        detail.append(row)
    result = {'passed': all(r.get('is_anim_sequence') for r in detail), 'read_only': True, 'source_assets_saved': False, 'retargeted': False, 'movement_or_attack_installed': False, 'scope': 'All current project animation registry; complete Sparrow source sequence metadata plus donor action candidates. No external projects or Game Animation Sample.', 'registry_count': len(rows), 'loaded_sequence_count': len(detail), 'registry_counts_by_root': dict(collections.Counter(r['path'].split('/')[2] for r in rows)), 'source_skeleton': _object_path(reference), 'registry_assets': rows, 'loaded_animations': detail, 'notes': ['Filename categories are search hints, not verified motion semantics.', 'Matching skeleton means directly playable source, not proof a composite action or gameplay ability already exists.', 'Different skeleton requires retargeting for Sparrow body, or original matching mesh for a temporary silhouette.', 'No newly imported external animation.']}
    (out/'sparrow-action-inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'passed': result['passed'], 'registry_count': len(rows), 'loaded_sequence_count': len(detail), 'report': str(out/'sparrow-action-inventory.json')}


def sequence(rig):
    if os.environ.get('SPARROW_QA_COMPACT_MEMORY') == '1':
        rig['cmd']('r.Streaming.PoolSize 384')
        rig['cmd']('r.Shadow.Virtual.MaxPhysicalPages 512')
        yield .5
    helper = runpy.run_path(str(Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline/sparrow_bow_audit.py'))
    candidates = [(key, SPARROW+'/Animations/'+name, ROGUE, title) for key, name, title in SOURCE_ACTIONS] + list(DONORS)
    wanted = set(filter(None, os.environ.get('SPARROW_ACTION_IDS', '').split(',')))
    if wanted:
        candidates = [r for r in candidates if r[0] in wanted]
    # Individual slices use JSON {"M09_handstand": [1.2, 2.2]} where the
    # values are source start seconds and source duration, not a speed change.
    slices = json.loads(os.environ.get('SPARROW_ACTION_SLICES', '{}'))
    max_seconds = min(6., max(.2, float(os.environ.get('SPARROW_ACTION_MAX_SECONDS', '6'))))
    rig['switch']('sparrow')
    yield .6
    p = rig['pawn']()
    original = p.get_editor_property('mesh')
    original_visibility = original.is_visible()
    transform = original.get_world_transform()
    live = []
    rows = []
    try:
        for key, path, mesh_path, title in candidates:
            rig['case'](key)
            rig['layout']([(1050, 650), (1050, -650), (-850, -650)])
            anim, mesh = unreal.load_asset(path), unreal.load_asset(mesh_path)
            assert isinstance(anim, unreal.AnimSequence) and isinstance(mesh, unreal.SkeletalMesh), key
            assert anim.get_editor_property('skeleton') == mesh.get_editor_property('skeleton'), key+' source skeleton mismatch'
            actor = helper['spawn_preview'](rig['world'](), rig['cmd'])
            live.append(actor)
            component = actor.get_editor_property('skeletal_mesh_component')
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property('disable_cloth_simulation', True)
            component.set_cast_shadow(False)
            component.set_forced_lod(1)
            actor.set_actor_transform(transform, False, True)
            original.set_visibility(False, False)
            source_length = anim.get_play_length()
            requested = slices.get(key, [0., source_length])
            start = max(0., min(source_length-.0001, float(requested[0])))
            duration = max(.0001, min(source_length-start, max_seconds, float(requested[1])))
            component.play_animation(anim, False)
            if start > 0.:
                component.set_position(start, False)
            rig['STATE']['video_clip'] = {'case': key, 'prefix': key+'_video', 'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()), 'frame_times': []}
            frames = max(1, math.ceil(duration*rig['FPS']))
            shot_frames = {int(frames*f) for f in (.15, .4, .7)}
            for frame in range(frames+1):
                if frame in shot_frames:
                    rig['capture'](key+'_pose_'+str(frame))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            rows.append({'id': key, 'title': title, 'animation': path, 'donor_mesh': mesh_path, 'source_seconds': source_length, 'source_start_seconds': start, 'preview_seconds': duration, 'playback_rate': 1., 'retargeted': False, 'gameplay_installed': False})
            actor.destroy_actor()
            live.remove(actor)
            original.set_visibility(original_visibility, False)
            yield .1
    finally:
        rig['finish_video_clip']()
        original.set_visibility(original_visibility, False)
        for actor in live:
            if unreal.SystemLibrary.is_valid(actor):
                actor.destroy_actor()
    rig['check'](original.is_visible() == original_visibility, 'action audition restores player visibility')
    (rig['OUT']/'sparrow-action-auditions.json').write_text(json.dumps({'passed': True, 'source_assets_saved': False, 'retargeted': False, 'gameplay_installed': False, 'auditions': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
