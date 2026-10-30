"""Sample Gideon basic attack hand/muzzle positions (component space) over time to find when the hand gesture
peaks, so the projectile fire time can match it. Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = '/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/'
STEPS = os.environ.get('HAND_ANIMS', 'Primary_Attack_A_Medium_Montage,Primary_Attack_B_Medium_Montage,Primary_Attack_C_Medium_Montage').split(',')
POINTS = os.environ.get('HAND_POINTS', 'hand_r,hand_l,Muzzle_01,Muzzle_02,Muzzle_03').split(',')
RATE = 60


def source_sequence(montage):
    if isinstance(montage, unreal.AnimSequence):
        return montage, 0.0
    for track in montage.get_editor_property('slot_anim_tracks'):
        for segment in track.get_editor_property('anim_track').get_editor_property('anim_segments'):
            anim = segment.get_editor_property('anim_reference')
            if anim:
                return anim, segment.get_editor_property('anim_start_time')
    return None, 0.0


def point_location(pose, name):
    space = unreal.AnimPoseSpaces.WORLD
    try:
        transform = unreal.AnimPoseExtensions.get_bone_pose(pose, name, space)
        if transform.translation.length() > 0.001:
            return transform.translation
    except Exception:
        pass
    transform = unreal.AnimPoseExtensions.get_socket_pose(pose, name, space)
    return transform.translation


result = {'passed': True, 'steps': []}
try:
    options = unreal.AnimPoseEvaluationOptions()
    for index, name in enumerate(STEPS):
        montage = unreal.load_asset(ROOT + name)
        anim, start = source_sequence(montage)
        entry = {'montage': name, 'sequence': anim.get_name(), 'segment_start': round(start, 3),
                 'length': round(anim.get_play_length(), 3), 'samples': []}
        previous = {}
        frames = int(min(anim.get_play_length(), float(os.environ.get('HAND_SECONDS', '0.9'))) * RATE)
        for frame in range(frames + 1):
            t = frame / RATE
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, start + t, options)
            row = {'t': round(t, 3)}
            for point in POINTS:
                try:
                    location = point_location(pose, point)
                except Exception as error:
                    row[point] = str(error)
                    continue
                speed = (location - previous[point]).length() * RATE if point in previous else 0.0
                previous[point] = location
                row[point] = [round(location.x, 1), round(location.y, 1), round(location.z, 1), round(speed)]
            entry['samples'].append(row)
        result['steps'].append(entry)
except Exception:
    result = {'passed': False, 'error': traceback.format_exc(), 'partial': result}
(qa / os.environ.get('HAND_OUT', 'gideon-hand-timing.json')).write_text(json.dumps(result, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
