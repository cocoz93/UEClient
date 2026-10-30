"""Installed A rollback, S flame texture, and D moving formation verification.

Only author() saves one project material. The parent serializes all UE/GPU work.
No original pack asset, movement input binding, or source animation is changed.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


FLAME = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowWingFlame'
FIRE = '/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D'


def _write(output, name, value):
    (Path(output) / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def author(output):
    root = Path(unreal.Paths.project_dir()).resolve()
    output = Path(output).resolve()
    assert output.is_relative_to(root / 'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True, exist_ok=True)
    # Reuse the established material-node helpers, without rewriting the S body.
    helper = runpy.run_path(str(root / 'Tools/CharacterPipeline/sparrow_s_silhouette.py'))
    node, wire = helper['_node'], helper['_wire']
    lib = unreal.MaterialEditingLibrary
    material = helper['_material'](FLAME, False)
    texture = unreal.load_asset(FIRE)
    assert isinstance(texture, unreal.Texture2D)
    shader = helper['_custom'](material, '''
float h = saturate(1.0 - UV.y);
float t = Clock * 0.19 + Phase;
float2 drift = float2(UV.x * 1.65 + sin(h * 4.7 - t * 2.1) * 0.10, UV.y * 1.3 + t);
float a = Texture2DSample(Fire, FireSampler, drift).r;
float b = Texture2DSample(Fire, FireSampler, drift * float2(1.73, 0.83) + float2(0.29, -t * 0.31)).g;
float curl = sin(h * 7.0 - t * 2.3 + Phase) * (0.03 + h * 0.12);
float centre = 0.5 + curl;
float width = lerp(0.48, 0.065, pow(h, 0.75));
float shape = pow(saturate(1.0 - abs(UV.x - centre) / width), 1.25);
float ends = smoothstep(0.0, 0.11, h) * (1.0 - smoothstep(0.64, 1.0, h));
float heat = saturate((a * 0.72 + b * 0.28 - 0.20) * 2.1);
float body = shape * ends * (0.10 + heat * 0.90);
float embers = 0.0;
for (int k = 0; k < 3; ++k)
{
    float fk = (float)k;
    float life = frac(Clock * (0.23 + fk * 0.025) + Phase * 0.31 + fk * 0.33);
    float px = 0.27 + fk * 0.23 + sin(life * 4.0 + Phase + fk) * 0.08;
    float py = 0.17 + life * 0.77;
    float2 dist = float2((UV.x - px) * 1.45, h - py);
    embers += exp(-dot(dist, dist) * 6500.0) * sin(life * 3.14159265);
}
float alpha = saturate((body * 0.48 + embers * 0.65) * Envelope);
float3 gold = lerp(float3(0.62, 0.27, 0.035), float3(1.65, 1.18, 0.35), heat);
float3 light = gold + float3(0.45, 0.36, 0.19) * (heat * heat + embers);
return float4(light, alpha);
''', ('UV', 'Clock', 'Envelope', 'Phase', 'Fire'), unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    wire(node(material, 'TextureCoordinate'), shader, 'UV')
    wire(node(material, 'Time'), shader, 'Clock')
    wire(node(material, 'ScalarParameter', parameter_name='Envelope', default_value=0.0), shader, 'Envelope')
    wire(node(material, 'ScalarParameter', parameter_name='Phase', default_value=0.0), shader, 'Phase')
    wire(node(material, 'TextureObject', texture=texture), shader, 'Fire')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node(material, 'ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        wire(shader, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report = {'passed': True, 'material': FLAME, 'texture': FIRE,
              'saved_original_pack': False, 'S_body_unchanged': True,
              'intent': 'Six small curling fire-texture wisps and sparse embers following the original Serath wing bones.'}
    _write(output, 'sparrow-forms-assets.json', report)
    return report


def _begin_clip(rig, name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name + '_video',
                                    'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                                    'frame_times': []}


def _clones(rig):
    return sorted(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher),
                  key=lambda a: a.get_name())


def _vec(v):
    return [v.x, v.y, v.z]


def sequence(rig):
    """Short installed-value checks plus actual locomotion/turn and S captures.

    Movement uses right-click input on the real controller; no actor teleport
    is used to manufacture the running footage. Post-stop aim rotation isolates
    the previous orbit jump from actual navigation.
    """
    report = {'passed': False, 'A': {}, 'D': {}, 'S': {}}
    rig['switch']('sparrow')
    yield .8
    pawn = rig['pawn']()
    ds = rig['layout']([(900, 0), (1250, 0), (900, 420)])
    yield .2
    _begin_clip(rig, 'A_restored_primary')
    rig['use']('A', ds[0])
    yield .50
    arrows = rig['tagged']('SparrowGearArrow')
    rig['check'](len(arrows) >= 1, 'A rollback emits gear arrow')
    gear = arrows[0]
    p0 = gear.get_actor_location()
    t0 = unreal.GameplayStatics.get_time_seconds(rig['world']())
    parts = list(gear.get_components_by_class(unreal.StaticMeshComponent))
    rig['check'](not any('GearWake' in p.get_name() for p in parts), 'A rejected long crossed wake is removed')
    source = pawn.get_editor_property('mesh')
    axis = source.get_socket_location('bow_shaft_top_03') - source.get_socket_location('bow_shaft_bott_03')
    report['A']['bow_vertical_fraction'] = abs(axis.z) / max(axis.length(), .001)
    yield .35
    t1 = unreal.GameplayStatics.get_time_seconds(rig['world']())
    speed = (gear.get_actor_location() - p0).length() / (t1 - t0)
    rig['check'](abs(speed - 220.0) < 1.0, 'A restored speed is220cm/s')
    report['A'].update({'speed': speed, 'long_wake_removed': True})
    rig['capture']('A_restored_primary')
    yield .85
    rig['finish_video_clip']()

    # Fresh pawn removes lingering arrows and previous damage stacks.
    rig['switch']('countess')
    yield .2
    rig['switch']('sparrow')
    yield .6
    pawn = rig['pawn']()
    ds = rig['layout']([(900, 0), (1250, 0), (900, 420)])
    yield .2
    _begin_clip(rig, 'D_moving_formation')
    rig['use']('D', ds[0])
    yield 1.0
    clones = _clones(rig)
    rig['check'](len(clones) == 2, 'D still creates two mirrors')
    meshes = [a.get_components_by_class(unreal.SkeletalMeshComponent)[0] for a in clones]
    rig['check'](all(not m.is_material_section_shown(i, 0) for m in meshes for i in (3, 7)),
                 'D hides unsimulated cloak and straps')
    start = pawn.get_actor_location()
    controller = pawn.get_controller()
    samples = []
    # Moving away from the target keeps the 10second D duration for the echo check.
    for offset in (unreal.Vector(0, 280, 0), unreal.Vector(-240, 120, 0)):
        goal = rig['ground'](start.x + offset.x, start.y + offset.y)
        rig['cmd'](f'CountessComboQA.Mouse Move Left {goal.x} {goal.y} {goal.z}')
        rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield 1.0 / rig['FPS']
        rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        for _ in range(21):
            yield 1.0 / 30.0
            samples.append({'owner': _vec(pawn.get_actor_location()),
                            'echoes': [_vec(a.get_actor_location()) for a in clones],
                            'speed': pawn.get_velocity().length()})
    controller.stop_movement()
    yield .25
    before = [a.get_actor_location() for a in clones]
    owner_before = pawn.get_actor_location()
    rotation = pawn.get_actor_rotation()
    pawn.set_actor_rotation(unreal.Rotator(rotation.pitch, rotation.yaw + 180.0, rotation.roll), True)
    yield .10
    owner_delta = pawn.get_actor_location() - owner_before
    orbit = [(a.get_actor_location() - p - owner_delta).length() for a, p in zip(clones, before)]
    rig['check'](max(orbit) < 20.0, 'D stationary180degree aim does not orbit the mirrors')
    rig['check'](max(s['speed'] for s in samples) > 100.0, 'D footage includes actual character locomotion')
    rig['check']((pawn.get_actor_location() - start).length() > 100.0, 'D follows a character that actually moved')
    old_counts = [a.get_echo_shot_count() for a in clones]
    rig['use']('W', ds[0])
    yield .85
    rig['check'](all(a.get_echo_shot_count() > n for a, n in zip(clones, old_counts)),
                 'D still echoes W after moving and turning')
    report['D'] = {'samples': samples, 'stationary_turn_displacement': orbit,
                   'echo_counts': [a.get_echo_shot_count() for a in clones]}
    rig['capture']('D_after_moving_and_firing')
    rig['finish_video_clip']()

    _begin_clip(rig, 'S_smouldering_wings')
    rig['use']('S', ds[0])
    yield .8
    wing_actors = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))
    rig['check'](len(wing_actors) == 1, 'S still creates one wing actor')
    wings = wing_actors[0]
    wisps = [c for c in wings.get_components_by_class(unreal.StaticMeshComponent)
             if 'SparrowWingFlame' in [str(t) for t in c.get_editor_property('component_tags')]]
    rig['check'](len(wisps) == 6 and all(c.is_visible() for c in wisps), 'S six smouldering wisps are active')
    rig['check'](all(c.get_material(0).get_base_material().get_path_name().startswith(FLAME + '.') for c in wisps),
                 'S wisps use the authored flame material')
    rig['check'](rig['skills']().get_ascension_remaining() > 39.0, 'S retains40second duration')
    rig['check'](all(len(a.get_components_by_class(unreal.SkeletalMeshComponent)) == 1 for a in _clones(rig)),
                 'D still has no wings during S')
    rig['capture']('S_smouldering_wings_entry')
    yield 1.4
    rig['capture']('S_smouldering_wings_hold')
    yield 1.0
    rig['finish_video_clip']()
    report['S'] = {'wisps': len(wisps), 'remaining': rig['skills']().get_ascension_remaining(),
                   'geometry': 'Original Serath wings; six texture wisps only'}
    rig['switch']('countess')
    yield .35
    rig['check'](not _clones(rig) and not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings),
                 'D and S attached effects retire with their owner')
    report['passed'] = True
    _write(rig['OUT'], 'sparrow-forms-repair.json', report)
