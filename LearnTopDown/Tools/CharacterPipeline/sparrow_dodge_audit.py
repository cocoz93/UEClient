"""Read local dodge-like animation candidates; no retargeting or asset installation."""
import json
from pathlib import Path
import re

import unreal


SPARROW = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/'
CANDIDATES = [
    ('Dash candidate, not confirmed as a roll', '/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash'),
    ('Native jump preparation, not a roll', SPARROW + 'Jump_Start'),
    ('Native landing, not a roll', SPARROW + 'Jump_Land'),
    ('Native acrobatic emote; inspect before considering any short segment', SPARROW + 'Emote_Handstand_T3'),
    ('Native forward knock reaction, not authored as dodge', SPARROW + 'Knock_Fwd'),
    ('Native backward knock reaction, not authored as dodge', SPARROW + 'Knock_Bwd'),
    ('Other hero directional movement candidate', '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_Fwd'),
    ('Other hero directional movement candidate', '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_Bwd'),
    ('Other hero directional movement candidate', '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_Left'),
    ('Other hero directional movement candidate', '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Ability_RMB_Right'),
]


def author(out):
    out = Path(out)
    root = Path(unreal.Paths.project_content_dir()).resolve()
    files = list(root.rglob('*.uasset'))
    keyword_hits = [str(path.relative_to(root)).replace('\\', '/') for path in files
                    if re.search(r'roll|dodge|evade|tumble|somersault', path.stem, re.I)]
    rogue = unreal.load_asset('/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue')
    reference = rogue.get_editor_property('skeleton') if rogue else None
    rows = []
    for note, path in CANDIDATES:
        asset = unreal.load_asset(path)
        row = {'path': path, 'note': note, 'present': bool(asset), 'is_anim_sequence': isinstance(asset, unreal.AnimSequence)}
        if asset:
            row['class'] = asset.get_class().get_name()
        if row['is_anim_sequence']:
            skeleton = asset.get_editor_property('skeleton')
            row['skeleton'] = skeleton.get_path_name() if skeleton else None
            row['same_skeleton_as_rogue'] = skeleton == reference
            row['length_seconds'] = asset.get_play_length()
            row['bone_samples_local'] = {}
            try:
                tracks = {str(name) for name in unreal.AnimationLibrary.get_animation_track_names(asset)}
                for bone in ('root', 'pelvis'):
                    if bone not in tracks:
                        continue
                    samples = []
                    for index in range(9):
                        moment = row['length_seconds'] * index / 8.
                        pose = unreal.AnimationLibrary.get_bone_pose_for_time(asset, bone, moment, False)
                        t, q = pose.translation, pose.rotation
                        samples.append({'seconds': round(moment, 4),
                                        'position': [round(t.x, 3), round(t.y, 3), round(t.z, 3)],
                                        'quaternion': [round(q.x, 5), round(q.y, 5), round(q.z, 5), round(q.w, 5)]})
                    row['bone_samples_local'][bone] = samples
            except Exception as exc:
                row['bone_samples_error'] = str(exc)
            for field in ('enable_root_motion', 'root_motion_root_lock', 'force_root_lock', 'rate_scale', 'additive_anim_type'):
                try:
                    value = asset.get_editor_property(field)
                    row[field] = value if isinstance(value, (bool, float, int, str)) else str(value)
                except Exception as exc:
                    row[field] = {'unavailable': str(exc)}
            row['installation'] = 'same skeleton; actual motion still needs visual review' if skeleton == reference else 'retargeting required; not applied to Sparrow'
        rows.append(row)
    result = {'passed': bool(reference) and all(row['is_anim_sequence'] for row in rows),
              'read_only': True, 'assets_saved': False, 'scope': 'Current project Content only; no external project or Game Animation Sample access',
              'uasset_count': len(files), 'filename_keyword_hits': keyword_hits,
              'reference_skeleton': reference.get_path_name() if reference else None,
              'candidates': rows, 'visual_review': 'pending; names alone do not prove a roll animation'}
    (out / 'sparrow-dodge-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'passed': result['passed'], 'read_only': True, 'assets_saved': False,
            'report': str(out / 'sparrow-dodge-audit.json')}


def sequence(rig):
    """Optional native-skeleton pose audition, then restore the running AnimBP."""
    rig['switch']('sparrow')
    yield .6
    rows = []
    for name in ('Jump_Start', 'Jump_Land', 'Emote_Handstand_T3'):
        rig['case']('sparrow_dodge_audit_' + name)
        rig['layout']([(700, 250), (800, 450), (850, -350)])
        mesh = rig['pawn']().get_editor_property('mesh')
        sequence_asset = unreal.load_asset(SPARROW + name)
        reference = mesh.get_editor_property('skeletal_mesh_asset').get_editor_property('skeleton')
        rig['check'](sequence_asset.get_editor_property('skeleton') == reference,
                     'only exact-skeleton animation may be auditioned on Sparrow')
        original_class = mesh.get_anim_instance().get_class()
        length = sequence_asset.get_play_length()
        samples = [.18, .42] if name != 'Emote_Handstand_T3' else [1.2, 2.2, 3.2]
        samples = [min(length * .9, moment) for moment in samples]
        previous = 0.
        try:
            mesh.play_animation(sequence_asset, False)
            for index, moment in enumerate(samples):
                yield max(.0167, moment - previous)
                rig['capture']('dodge_audit_' + name + '_' + str(index))
                previous = moment
            rows.append({'animation': name, 'sample_seconds': samples, 'retargeted': False})
        finally:
            mesh.set_anim_instance_class(original_class)
            mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
        yield .3
        rig['check'](mesh.get_anim_instance().get_class() == original_class, 'original AnimBP restored after audition')
    (rig['OUT'] / 'sparrow-dodge-preview.json').write_text(json.dumps({
        'passed': True, 'temporary_pose_audition': True, 'movement_or_skill_added': False,
        'assets_saved': False, 'samples': rows, 'visual_review': 'pending'}, indent=2), encoding='utf-8')
