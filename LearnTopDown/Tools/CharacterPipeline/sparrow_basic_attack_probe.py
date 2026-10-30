"""Read-only source poses and currently configured bow attack montage."""
import json
import os
from pathlib import Path
import traceback
import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = Path(unreal.Paths.project_dir()).resolve()
HERO = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/'
PRIVATE = '/Game/TopDown/Characters/Sparrow/Animations/'
report = {'passed': False, 'read_only': True, 'saved_assets': [], 'clips': []}

def prop(asset, name):
    try:
        value = asset.get_editor_property(name)
        if hasattr(value, 'get_path_name'):
            return value.get_path_name()
        return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)
    except Exception as error:
        return {'unavailable': str(error)}

try:
    assert OUT.is_relative_to(ROOT / 'Saved/QA')
    mesh = unreal.load_asset('/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue')
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', mesh)
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    options.set_editor_property('extract_root_motion', False)
    options.set_editor_property('incorporate_root_motion_into_pose', False)
    paths = [HERO + name for name in ('Primary_Fire_Med', 'Primary_Fire_Fast', 'Primary_Fire_Slow',
             'RMB_Drawback', 'RMB_Fire', 'idle', 'Travel_Mode_Idle_BowDown', 'R_Ability_Med_Fire')]
    paths += [PRIVATE + 'AM_Sparrow_Primary']
    if os.environ.get('SPARROW_PROBE_FAST_ONLY')=='1':
        paths=[HERO+'Primary_Fire_Fast']
    for path in paths:
        asset = unreal.load_asset(path)
        assert isinstance(asset, unreal.AnimSequenceBase), path
        length = asset.get_play_length()
        row = {'path': asset.get_path_name(), 'length': length,
               'properties': {name: prop(asset, name) for name in ('rate_scale', 'enable_root_motion',
                    'force_root_lock', 'blend_in', 'blend_out', 'blend_out_trigger_time',
                    'slot_anim_tracks', 'composite_sections')}, 'notifies': [], 'samples': []}
        for event in unreal.AnimationLibrary.get_animation_notify_events(asset):
            row['notifies'].append({'name': str(event.get_editor_property('notify_name')),
                'trigger_time': unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event)})
        if isinstance(asset, unreal.AnimSequence):
            for index in range(41):
                seconds = min(length - .00001, length * index / 40)
                pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(asset, seconds, options)
                bones = {}
                for bone in ('root', 'pelvis', 'head', 'hand_l', 'hand_r', 'bow_base', 'arrow_anchor', 'foot_l', 'foot_r'):
                    t = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
                    p, q = t.translation, t.rotation
                    bones[bone] = {'translation': [p.x,p.y,p.z], 'rotation': [q.x,q.y,q.z,q.w]}
                row['samples'].append({'time': seconds, 'bones': bones})
        report['clips'].append(row)
    fast=unreal.load_asset(HERO+'Primary_Fire_Fast')
    times,values=unreal.AnimationLibrary.get_float_keys(fast,'DissolveAmount')
    report['fast_arrow_curve']={'times':list(times),'values':list(values)}
    if os.environ.get('SPARROW_PROBE_COUNTESS')=='1':
        countess='/Game/ParagonCountess/Characters/Heroes/Countess'
        countess_mesh=unreal.load_asset(countess+'/Meshes/SM_Countess')
        assert countess_mesh is not None
        countess_options=unreal.AnimPoseEvaluationOptions()
        countess_options.set_editor_property('optional_skeletal_mesh',countess_mesh)
        countess_options.set_editor_property('evaluation_type',unreal.AnimDataEvalType.RAW)
        left=unreal.load_asset(countess+'/Animations/Ability_RMB')
        right=unreal.load_asset(countess+'/Animations/Primary_Attack_B_Normal')
        assert left and right
        tracks=[str(n) for n in unreal.AnimationLibrary.get_animation_track_names(left)]
        common=[n for n in tracks if n in {str(v) for v in unreal.AnimationLibrary.get_animation_track_names(right)}]
        import math
        per_bone={n:{'translation_cm':0,'angle_degrees':0} for n in common}
        for index in range(41):
            poses=[unreal.AnimPoseExtensions.get_anim_pose_at_time(a,min(a.get_play_length()-.00001,a.get_play_length()*index/40),countess_options) for a in (left,right)]
            for bone in common:
                transforms=[unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD) for pose in poses]
                points=[[t.translation.x,t.translation.y,t.translation.z] for t in transforms]
                quats=[[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w] for t in transforms]
                dot=abs(sum(a*b for a,b in zip(*quats)))
                row=per_bone[bone]
                row['translation_cm']=max(row['translation_cm'],math.dist(*points))
                row['angle_degrees']=max(row['angle_degrees'],math.degrees(2*math.acos(min(1,dot))))
        report['countess_W_vs_primary3']={'W':left.get_path_name(),'primary3':right.get_path_name(),
            'lengths':[a.get_play_length() for a in (left,right)],'frame_counts':[unreal.AnimationLibrary.get_num_frames(a) for a in (left,right)],
            'track_counts':[len(unreal.AnimationLibrary.get_animation_track_names(a)) for a in (left,right)],
            'normalized_time_samples':41,'common_bones':len(common),'per_bone_max_errors':per_bone,
            'max_translation_cm':max(v['translation_cm'] for v in per_bone.values()),
            'max_angle_degrees':max(v['angle_degrees'] for v in per_bone.values())}
    cdo = unreal.get_default_object(unreal.load_class(None, '/Game/TopDown/Characters/Sparrow/BP_SparrowCharacter.BP_SparrowCharacter_C'))
    report['cdo'] = {name: prop(cdo, name) for name in ('combo_attacks', 'combo_restart_cooldown')}
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + OUT.as_posix() + '"')
    dump = paths + [PRIVATE + 'ABP_Sparrow_SmoothStop']
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + p + '"' for p in dump))
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'basic-attack-probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
