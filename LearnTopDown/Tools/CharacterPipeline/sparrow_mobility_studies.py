"""Local locomotion auditions and a motion-asset-free light-step visual study.

All actors and displacement belong to PIE previews. No movement ability,
collision bypass, animation retarget, or source asset is installed.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


SPARROW = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/'
AURORA = '/Game/ParagonAurora/Characters/Heroes/Aurora/'
CANDIDATES = (
    ('M1_native_hop', SPARROW+'Animations/Jump_Start_TravelMode', SPARROW+'Skins/Rogue/Meshes/Sparrow_Rogue', .6),
    ('M2_native_backstep', SPARROW+'Animations/Knock_Bwd', SPARROW+'Skins/Rogue/Meshes/Sparrow_Rogue', .8),
    ('M3_mannequin_dash', '/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Dash', '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple', .97),
    ('M4_aurora_evasion', AURORA+'Animations/Ability_RMB_Fwd', AURORA+'Meshes/Aurora', 1.2),
)


def author(out):
    out = Path(out)
    reference = unreal.load_asset(SPARROW+'Meshes/Sparrow_Skeleton')
    rows = []
    for name, path, mesh_path, duration in CANDIDATES:
        anim, mesh = unreal.load_asset(path), unreal.load_asset(mesh_path)
        assert isinstance(anim, unreal.AnimSequence) and isinstance(mesh, unreal.SkeletalMesh), name
        skeleton = anim.get_editor_property('skeleton')
        assert skeleton == mesh.get_editor_property('skeleton'), name+' donor must match animation'
        row = {'id': name, 'animation': path, 'donor_mesh': mesh_path,
               'length': anim.get_play_length(), 'preview_seconds': duration,
               'same_skeleton_as_sparrow': skeleton == reference,
               'root_motion_enabled': anim.get_editor_property('enable_root_motion')}
        rows.append(row)
    result = {'passed': True, 'read_only': True, 'source_assets_saved': False,
              'retargeted': False, 'movement_installed': False, 'candidates': rows}
    (out/'mobility-assets.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def _clip(rig, name):
    rig['STATE']['video_clip'] = {'case': name, 'prefix': name+'_video',
        'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()), 'frame_times': []}


def sequence(rig):
    helper = runpy.run_path(str(Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline/sparrow_bow_audit.py'))
    rig['switch']('sparrow')
    yield .6
    fps = rig['FPS']
    p = rig['pawn']()
    original = p.get_editor_property('mesh')
    transform = original.get_world_transform()
    proxies = []
    rows = []
    try:
        for name, path, mesh_path, duration in (() if os.environ.get('SPARROW_MOBILITY_GOLD_ONLY') == '1' else CANDIDATES):
            rig['case'](name)
            rig['layout']([(900, 350), (900, -350), (-600, -450)])
            actor = helper['spawn_preview'](rig['world'](), rig['cmd'])
            proxies.append(actor)
            visual = actor.get_editor_property('skeletal_mesh_component')
            asset, anim = unreal.load_asset(mesh_path), unreal.load_asset(path)
            visual.set_skeletal_mesh_asset(asset)
            visual.set_editor_property('disable_cloth_simulation', True)
            visual.set_forced_lod(1)
            visual.set_cast_shadow(False)
            actor.set_actor_transform(transform, False, True)
            original.set_visibility(False, False)
            visual.play_animation(anim, False)
            _clip(rig, name)
            for frame in range(round(fps*duration)):
                if frame in (round(fps*.16), round(fps*.42)):
                    rig['capture'](name+'_'+str(frame))
                yield 1/fps
            rig['finish_video_clip']()
            rows.append({'id': name, 'actual_donor_animation': True, 'retargeted': False})
            actor.destroy_actor()
            proxies.remove(actor)
            original.set_visibility(True, False)
            yield .15

        # Freeze the visible idle body and move only a tagged preview actor.
        # This demonstrates a solid-color magical step, not a skeletal roll.
        name = 'M5_gold_lightstep'
        rig['case'](name)
        material = unreal.load_asset('/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho')
        assert material is not None
        for index in range(4):
            actor = helper['spawn_preview'](rig['world'](), rig['cmd'])
            proxies.append(actor)
            visual = actor.get_editor_property('skeletal_mesh_component')
            visual.set_skeletal_mesh_asset(original.get_editor_property('skeletal_mesh_asset'))
            visual.set_leader_pose_component(original, False, False)
            visual.set_editor_property('disable_cloth_simulation', True)
            visual.set_cast_shadow(False)
            visual.set_forced_lod(1)
            tint = visual.create_dynamic_material_instance(0, material)
            tint.set_vector_parameter_value('BodyTint', unreal.LinearColor(2.2, 1.45, .28, 1))
            # Echo Visibility also dissolves the noise mask: low values erase
            # whole silhouettes, so stagger clear forms instead of using it as alpha.
            tint.set_scalar_parameter_value('Visibility', 1. if index == 0 else 1.-index*.08)
            for slot in range(visual.get_num_materials()):
                visual.set_material(slot, tint)
            for lod in range(5):
                for slot in (3, 7, 13):
                    visual.show_material_section(slot, -1, False, lod)
            actor.set_actor_transform(transform, False, True)
            visual.set_visibility(False, False)
        original.set_visibility(False, False)
        _clip(rig, name)
        for frame in range(round(fps*.9)):
            elapsed = frame/fps
            for index, actor in enumerate(proxies):
                phase = max(0., min(1., (elapsed-index*.045)/.30))
                visual = actor.get_editor_property('skeletal_mesh_component')
                visible = elapsed >= index*.045 and elapsed < .36+index*.045
                visual.set_visibility(visible, False)
                location = transform.translation + unreal.Vector(360.*(1.-(1.-phase)**2), 0, 0)
                actor.set_actor_location(location, False, True)
                actor.set_actor_scale3d(unreal.Vector(1.05, 1.12, 1.-.24*math.sin(phase*math.pi)))
            if frame in (round(fps*.10), round(fps*.23)):
                rig['capture'](name+'_'+str(frame))
            yield 1/fps
        rig['finish_video_clip']()
        rows.append({'id': name, 'uses_movement_animation': False,
                     'prototype_only': True, 'actual_player_displaced': False,
                     'kind': 'solid gold light step with three afterimages; not anatomical roll'})
    finally:
        rig['finish_video_clip']()
        original.set_visibility(True, False)
        for actor in proxies:
            if unreal.SystemLibrary.is_valid(actor):
                actor.destroy_actor()
    rig['check'](original.is_visible(), 'mobility study restores live character visibility')
    rig['check'](not any(a.actor_has_tag('SparrowBowAuditPreview') for a in
                        unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SkeletalMeshActor)),
                 'mobility preview actors cleaned')
    (rig['OUT']/'mobility-studies.json').write_text(json.dumps({
        'passed': True, 'movement_installed': False, 'assets_saved': False, 'studies': rows}, indent=2), encoding='utf-8')
