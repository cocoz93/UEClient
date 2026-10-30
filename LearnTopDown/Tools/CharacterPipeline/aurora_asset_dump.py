"""Dump Aurora ability animation facts (length, notifies, root/pelvis travel) for the C++-only Aurora character.
Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/'
NAMES = ['Primary_Attack_A_Montage', 'Primary_Attack_B_Montage', 'Primary_Attack_C_Montage',
         'Ability_Q', 'Ability_Q_InMotion', 'Ability_Q_Targeting', 'Ability_Q_Targeting_Intro', 'Ability_Q_Stop',
         'Jog_Fwd_Ability_Q', 'Ability_E', 'Ability_E_V2', 'Ability_E_InMotion', 'Ability_R', 'Ability_R_InPlace',
         'Ability_R_InPlace_V2', 'Ability_R_InMotion', 'Ability_R_Targeting', 'Ability_RMB_Fwd', 'Ability_RMB_Bwd',
         'Ability_RMB_Left', 'Ability_RMB_Right', 'Cast', 'Recall', 'Emote_Slice', 'Emote_Ice_Sculpture',
         'Emote_Minion_Kick', 'Melee_Attack_Air', 'Primary_Attack_Slow_A', 'Primary_Attack_Slow_B']


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def bone_track(anim, bone, length):
    samples = []
    for i in range(9):
        t = length * i / 8
        try:
            pose = unreal.AnimationLibrary.get_bone_pose_for_time(anim, bone, t, False)
            samples.append([round(t, 3)] + vec(pose.translation))
        except Exception as error:
            return str(error)
    return samples


result = {'passed': True, 'anims': {}}
try:
    for name in NAMES:
        anim = unreal.load_asset(ROOT + name)
        if anim is None:
            result['anims'][name] = None
            continue
        length = anim.get_play_length()
        entry = {'class': anim.get_class().get_name(), 'length': round(length, 3),
                 'rate_scale': anim.get_editor_property('rate_scale')}
        try:
            entry['notify_names'] = [str(n) for n in unreal.AnimationLibrary.get_animation_notify_event_names(anim)]
        except Exception as error:
            entry['notify_names'] = str(error)
        try:
            events = unreal.AnimationLibrary.get_animation_notify_events(anim)
            entry['notifies'] = []
            for event in events:
                item = {}
                for prop in ('notify_name', 'trigger_time_offset', 'duration'):
                    try:
                        item[prop] = str(event.get_editor_property(prop))
                    except Exception:
                        pass
                try:
                    item['time'] = round(event.get_editor_property('link_value'), 3)
                except Exception:
                    pass
                try:
                    notify = event.get_editor_property('notify')
                    item['notify_class'] = notify.get_class().get_name() if notify else None
                except Exception:
                    pass
                entry['notifies'].append(item)
        except Exception as error:
            entry['notifies'] = str(error)
        if isinstance(anim, unreal.AnimSequence):
            entry['root_motion'] = anim.get_editor_property('enable_root_motion')
            entry['root'] = bone_track(anim, 'root', length)
            entry['pelvis'] = bone_track(anim, 'pelvis', length)
        result['anims'][name] = entry
    skeleton = unreal.load_asset('/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora_Skeleton')
    if skeleton:
        try:
            result['sockets'] = [str(s.get_editor_property('socket_name')) for s in skeleton.get_editor_property('sockets')]
        except Exception as error:
            result['sockets'] = str(error)
except Exception:
    result = {'passed': False, 'error': traceback.format_exc(), 'partial': result}
(qa / 'aurora-assets.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
