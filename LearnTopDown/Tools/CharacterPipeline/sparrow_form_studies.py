"""S energy body authoring and runtime-only D/A visual studies.

author(output) runs BEFORE PIE: save S's energy material plus D2's isolated
preview material and read the two required skin meshes. sequence(rig) uses
new_skills_probe callbacks. SPARROW_FORM_AUTHOR_D2_ONLY=1 authors only the draft.
D silhouettes and A impact variants are NEVER saved or installed on the Pawn.
"""
import json
import math
import os
from pathlib import Path
import runpy
import traceback

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/Materials'
ENERGY = FOLDER + '/M_SparrowAscensionEnergy'
UPPER_BODY_STUDY = FOLDER + '/M_SparrowUpperBodySpiritStudy'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'
STUDIES = (
    {'id': 'D1_floating_bows', 'label': '부유하는 Raven 활', 'skin': 'Raven', 'slots': [3, 4, 7]},
    {'id': 'D2_armor_spirits', 'label': '허리 아래가 사라지는 상반신 수호령', 'skin': 'Raven', 'slots': list(range(11))},
    {'id': 'D3_raven_sentinels', 'label': '투구와 어깨가 있는 Raven 궁수령', 'skin': 'Raven', 'slots': list(range(11))},
)


def _helper():
    return runpy.run_path(str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_bow_audit.py'))


def _path(value):
    return value.get_path_name() if value else None


def _write(output, name, report):
    (output / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def author(output):
    """Create S's dedicated material; never alter M_SparrowAscensionEcho."""
    if os.environ.get('SPARROW_FORM_AUTHOR_D2_ONLY') == '1':
        return author_d2(output)
    output = Path(output).resolve()
    root = Path(unreal.Paths.project_dir()).resolve()
    assert output.is_relative_to(root / 'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(NOISE)
    assert texture is not None
    report = {'passed': False, 'source_assets_saved': False, 'D_A_installed': False,
              'saved_materials': [], 'skin_audit': [], 'D_studies': list(STUDIES)}
    material = unreal.load_asset(ENERGY)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_SparrowAscensionEnergy', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True, 'used_with_skeletal_mesh': True,
                       'used_with_clothing': True, 'used_with_instanced_static_meshes': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **properties):
        value = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, setting in properties.items():
            value.set_editor_property(key, setting)
        return value

    def wire(source, target, name, output_pin=''):
        assert lib.connect_material_expressions(source, output_pin, target, name)

    uv = node('TextureCoordinate')
    samples = []
    for scale, x, y in ((2.3, .075, -.21), (5.8, -.12, .11)):
        scaled = node('Multiply', const_b=scale)
        wire(uv, scaled, 'A')
        panner = node('Panner', speed_x=x, speed_y=y)
        wire(scaled, panner, 'Coordinate')
        sample = node('TextureSample', texture=texture)
        wire(panner, sample, 'UVs')
        samples.append(sample)
    code = '''
float flow = saturate(Flow);
float grain = saturate(Grain);
float facing = saturate(Facing);
float visible = saturate(Visibility);
// Long moving filaments sit inside denser angular islands; no metal lighting.
float strandPhase = frac(UV.y * 5.0 - UV.x * 1.7 + flow * 0.7 - Clock * 0.30);
float strands = pow(saturate(1.0 - abs(strandPhase * 2.0 - 1.0)), 12.0);
float islands = smoothstep(0.34, 0.70, abs(flow - grain) * 1.6);
float fragments = smoothstep(1.0 - visible - 0.15, 1.0 - visible + 0.10, flow);
float3 gold = lerp(float3(0.50,0.22,0.025), BodyTint, 0.40);
float3 deep = float3(0.045,0.028,0.095) * (1.0-flow) * (1.0-facing);
float3 color = deep + gold * (0.18 + 0.35*flow + 0.65*islands);
color += float3(1.65,1.40,0.78) * strands * (0.36 + 0.42*grain);
color += float3(1.15,0.82,0.34) * facing * (0.55 + 0.55*grain);
float alpha = visible * fragments * (0.48 + 0.24*islands + 0.20*facing);
return float4(color, saturate(alpha));
'''
    custom = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for key in ('Flow', 'Grain', 'Facing', 'UV', 'Clock', 'Visibility', 'BodyTint'):
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    wire(samples[0], custom, 'Flow', 'R')
    wire(samples[1], custom, 'Grain', 'R')
    wire(node('Fresnel', exponent=2.8, base_reflect_fraction=.04), custom, 'Facing')
    wire(uv, custom, 'UV')
    wire(node('Time'), custom, 'Clock')
    wire(node('ScalarParameter', parameter_name='Visibility', default_value=1.0), custom, 'Visibility')
    wire(node('VectorParameter', parameter_name='BodyTint',
              default_value=unreal.LinearColor(.95, .64, .16, 1)), custom, 'BodyTint')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        wire(custom, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report['saved_materials'].append(ENERGY)
    helper = _helper()
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    for name in ('Rogue', 'Raven'):
        mesh = unreal.load_asset(helper['SKINS'][name])
        assert isinstance(mesh, unreal.SkeletalMesh)
        row = helper['_inspect'](name, mesh, subsystem)
        assert 'error' not in row, row.get('error')
        report['skin_audit'].append(row)
    assert len({row['skeleton'] for row in report['skin_audit']}) == 1
    report['D2_preview_material'] = author_d2(output)
    report['passed'] = True
    _write(output, 'sparrow-form-assets.json', report)
    return report


def author_d2(output):
    """Save one preview-only material using the Echo formula plus a waist fade.

    This never opens or edits the production Echo/Energy materials. The source
    noise texture is read only. No native actor references this study material.
    """
    output = Path(output).resolve()
    root = Path(unreal.Paths.project_dir()).resolve()
    assert output.is_relative_to(root / 'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(UPPER_BODY_STUDY)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_SparrowUpperBodySpiritStudy', FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    texture = unreal.load_asset(NOISE)
    assert texture is not None
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True, 'used_with_skeletal_mesh': True,
                       'used_with_clothing': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **properties):
        value = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, setting in properties.items():
            value.set_editor_property(key, setting)
        return value

    def wire(source, target, name, output_pin=''):
        assert lib.connect_material_expressions(source, output_pin, target, name)

    uv = node('TextureCoordinate')
    panner = node('Panner', speed_x=.14, speed_y=.06)
    wire(uv, panner, 'Coordinate')
    sample = node('TextureSample', texture=texture)
    wire(panner, sample, 'UVs')
    custom = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float grain = saturate(Noise);
float visible = saturate(Visibility);
float fragments = smoothstep(1.0-visible-0.12, 1.0-visible+0.08, grain);
float alpha = visible * fragments * (0.28 + 0.40 * Facing) * (0.75 + 0.25 * grain);
float3 color = BodyTint * (0.50 + 0.65 * grain) + float3(1.5,0.88,0.18) * Facing * (0.65 + 0.45 * grain);
// Foot-space height follows the runtime proxy, including animation/following.
// Below 75 cm nothing survives; 75-110 cm softly dissolves into the torso.
float height = WorldPos.z - CutBaseZ;
float upperBody = smoothstep(75.0 + grain * 5.0, 110.0, height);
return float4(color, saturate(alpha * upperBody));
''')
    pins = []
    for key in ('Noise', 'Facing', 'Visibility', 'BodyTint', 'WorldPos', 'CutBaseZ'):
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    wire(sample, custom, 'Noise', 'R')
    wire(node('Fresnel'), custom, 'Facing')
    wire(node('ScalarParameter', parameter_name='Visibility', default_value=1.), custom, 'Visibility')
    wire(node('ScalarParameter', parameter_name='CutBaseZ', default_value=0.), custom, 'CutBaseZ')
    wire(node('VectorParameter', parameter_name='BodyTint',
              default_value=unreal.LinearColor(.7, .39, .06, 1)), custom, 'BodyTint')
    wire(node('WorldPosition'), custom, 'WorldPos')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        wire(custom, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report = {'passed': True, 'preview_only': True, 'production_materials_saved': False,
              'saved_materials': [UPPER_BODY_STUDY], 'height_fade_cm': [75, 110],
              'bow_slots_preserved': [3, 4, 7], 'source_noise_read_only': NOISE}
    _write(output, 'sparrow-d2-material-study.json', report)
    return report


def _alive(actor):
    return actor is not None and unreal.SystemLibrary.is_valid(actor)


def _components(actor, cls):
    return list(actor.get_components_by_class(cls))


def _native_mesh(actor):
    matches = [c for c in _components(actor, unreal.SkeletalMeshComponent) if c.get_name() == 'MirrorArcherMesh']
    assert len(matches) == 1
    return matches[0]


def _snapshot_body(mesh, audit):
    return {'materials': [_path(mesh.get_material(i)) for i in range(mesh.get_num_materials())],
            'sections': [[bool(mesh.is_material_section_shown(i, lod['lod']))
                          for i in range(mesh.get_num_materials())] for lod in audit['lods']]}


def _start_clip(rig, name):
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name + '_video',
                                    'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                                    'frame_times': []}


def sequence(rig):
    """S native lifecycle evidence, then D3 and A2 actual-world visual drafts."""
    out = Path(rig['OUT'])
    fps = max(1, int(rig.get('FPS', os.environ.get('SPARROW_QA_FPS', '60'))))
    assets_path = Path(os.environ.get('SPARROW_FORM_ASSETS', str(out / 'sparrow-form-assets.json')))
    assets = json.loads(assets_path.read_text(encoding='utf-8'))
    parts = {part.strip().lower() for part in os.environ.get('SPARROW_FORM_PARTS', 's,d,a').split(',') if part.strip()}
    assert parts and parts <= {'s', 'd', 'd1', 'd2', 'd3', 'a', 'a1', 'a2'}, 'Unknown SPARROW_FORM_PARTS selection'
    assert assets['passed']
    skins = {row['skin']: row for row in assets['skin_audit']}
    helper = _helper()
    report = {'passed': False, 'D_A_runtime_only': True, 'assets_saved_during_PIE': False,
              'S_material': ENERGY, 'D_studies': [], 'A_studies': [], 'cleanup': False,
              'selected_parts': sorted(parts), 'asset_audit': str(assets_path)}
    proxies = []
    hidden = []
    particles = []
    held = False
    try:
        rig['switch']('sparrow')
        yield .8
        pawn = rig['pawn']()
        mesh = pawn.get_editor_property('mesh')
        if 's' in parts:
            body_before = _snapshot_body(mesh, skins['Rogue'])
            rig['case']('S_energy_body_and_D_no_wings')
            ds = rig['layout']([(650, 0), (900, 350), (900, -350)])
            yield .2
            rig['use']('D', ds[0])
            yield 1.05
            clones = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))
            rig['check'](len(clones) == 2, 'D creates two native following archers')
            rig['use']('S', ds[0])
            _start_clip(rig, 'S_energy_body_and_D_no_wings')
            yield .65
            body_during = _snapshot_body(mesh, skins['Rogue'])
            native_wings = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))
            rig['check'](len(native_wings) == 1, 'S preserves one native main-body wing actor')
            base_names = [_path(mesh.get_material(i).get_base_material()) for i in range(mesh.get_num_materials())]
            rig['check'](all(name and name.startswith(ENERGY + '.') for name in base_names), 'S uses dedicated energy body on every original material slot')
            rig['check'](all(not row[i] for row in body_during['sections'] for i in (3, 7, 13)), 'S hides hood, cloak, and cloak straps on every LOD')
            clone_components = [[c.get_name() for c in _components(a, unreal.SkeletalMeshComponent)] for a in clones]
            rig['check'](all(names == ['MirrorArcherMesh'] for names in clone_components), 'D has no wing mesh component while S is active')
            rig['capture']('S_energy_body_D_without_wings')
            yield .95
            rig['capture']('S_energy_body_flow_second_pose')
            rig['finish_video_clip']()
            yield rig['skills']().get_ascension_remaining() + .2
            body_after = _snapshot_body(mesh, skins['Rogue'])
            rig['check'](body_after == body_before, 'S expiry restores all original material overrides and section visibility')
            rig['capture']('S_original_body_restored')
            report['S'] = {'before': body_before, 'during': body_during, 'after': body_after,
                           'clone_components_during_S': clone_components, 'material_bases': base_names}
            yield 1.6

        # Actual native clones continue to aim/fire. Only their visible meshes are
        # replaced by tagged temporary actors with the same skeleton leader pose.
        for study in STUDIES:
            if 'd' not in parts and study['id'].split('_')[0].lower() not in parts:
                continue
            rig['case'](study['id'])
            ds = rig['layout']([(650, 0), (900, 350), (900, -350)])
            yield .15
            rig['use']('D', ds[0])
            yield 1.05
            clones = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))
            rig['check'](len(clones) == 2, study['id'] + ' has two live gameplay clones')
            records = []
            faded_materials = {}
            for clone in clones:
                native = _native_mesh(clone)
                proxy = helper['spawn_preview'](rig['world'](), rig['cmd'])
                proxies.append(proxy)
                row = helper['preview_sections'](proxy, study['skin'], study['slots'], skins[study['skin']]['lods'], mesh)
                visual = proxy.get_editor_property('skeletal_mesh_component')
                # Preserve the native D material, pulse and fade; change geometry only.
                for slot in range(visual.get_num_materials()):
                    visual.set_material(slot, native.get_material(0))
                if study['id'] == 'D2_armor_spirits':
                    source = unreal.load_asset(UPPER_BODY_STUDY)
                    assert source is not None, 'Run author_d2 before this D2-only study'
                    fade = visual.create_dynamic_material_instance(0, source)
                    assert fade is not None
                    for slot in range(visual.get_num_materials()):
                        if slot not in (3, 4, 7):
                            visual.set_material(slot, fade)
                    faded_materials[proxy.get_path_name()] = fade
                visual.set_cast_shadow(False)
                visual.set_editor_property('disable_cloth_simulation', True)
                native.set_visibility(False, False)
                hidden.append(native)
                records.append((clone, native, proxy, visual))
                row['silhouette'] = study['label']
            _start_clip(rig, study['id'])
            target = rig['aim'](ds[0])
            rig['cmd'](f'CountessComboQA.Mouse Press Left {target.x} {target.y} {target.z}')
            held = True
            before_echoes = [a.get_echo_shot_count() for a in clones]
            frame_labels = {round(fps * seconds): label for seconds, label in ((.25, 15), (.75, 45), (4 / 3, 80))}
            for frame in range(round(fps * 5 / 3)):
                for clone, native, proxy, visual in records:
                    if _alive(clone):
                        proxy.set_actor_transform(native.get_world_transform(), False, True)
                        fade = faded_materials.get(proxy.get_path_name())
                        if fade is not None:
                            original = native.get_material(0)
                            fade.set_scalar_parameter_value('CutBaseZ', native.get_world_location().z)
                            fade.set_scalar_parameter_value('Visibility', original.get_scalar_parameter_value('Visibility'))
                            fade.set_vector_parameter_value('BodyTint', original.get_vector_parameter_value('BodyTint'))
                if frame in frame_labels:
                    rig['capture'](study['id'] + '_' + str(frame_labels[frame]))
                yield 1 / fps
            rig['cmd'](f'CountessComboQA.Mouse Release Left {target.x} {target.y} {target.z}')
            held = False
            after_echoes = [a.get_echo_shot_count() for a in clones]
            rig['check'](all(b > a for a, b in zip(before_echoes, after_echoes)), study['id'] + ' keeps native attack echo events')
            rig['finish_video_clip']()
            report['D_studies'].append({**study, 'echo_before': before_echoes, 'echo_after': after_echoes,
                                         'native_gameplay_unchanged': True, 'prototype_only': True})
            for clone, native, proxy, visual in records:
                native.set_visibility(True, False)
                hidden.remove(native)
                helper['cleanup_preview'](proxy)
                proxies.remove(proxy)
            # Let native lifecycle finish: do not bypass its ten-second duration.
            yield max(a.get_remaining_seconds() for a in clones) + .25

        # A studies react to the existing damage event. Extra bursts cannot hit,
        # push, slow, or change the 70 cm collision radius / 90 damage.
        for variant, label in (('A1_cutting_sparks', '연속 절삭 불티'), ('A2_compressed_fracture', '응축 후 양옆 파열')):
            if 'a' not in parts and variant.split('_')[0].lower() not in parts:
                continue
            rig['case'](variant)
            ds = rig['layout']([(430, 0), (900, 350), (900, -350)])
            yield .2
            initial_health = rig['health'](ds[0])
            rig['use']('A', ds[0])
            _start_clip(rig, variant)
            seen = set()
            pending = []
            hit_time = None
            contact_captured = False
            emissions = []
            for frame in range(round(fps * 3.5)):
                now = unreal.GameplayStatics.get_time_seconds(rig['world']())
                if hit_time is None and rig['health'](ds[0]) < initial_health:
                    hit_time = now
                for accent in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionAccent):
                    if accent.get_path_name() in seen:
                        continue
                    seen.add(accent.get_path_name())
                    fx = _components(accent, unreal.ParticleSystemComponent)[0]
                    template = fx.get_editor_property('template')
                    if not template or 'FeatherImpact' not in template.get_name():
                        continue
                    location = accent.get_actor_location()
                    rotation = accent.get_actor_rotation()
                    if variant == 'A1_cutting_sparks':
                        # Hide this instance's large flame/wisp impact. Its saved
                        # template stays intact; four small spark-only pulses
                        # make a .3-second friction streak with one native hit.
                        fx.set_visibility(False, False)
                        fx.set_emitter_enable('Main Flames', False)
                        fx.set_emitter_enable('Wisps', False)
                        yaw = math.radians(rotation.yaw)
                        forward = unreal.Vector(math.cos(yaw), math.sin(yaw), 0)
                        right = unreal.Vector(-math.sin(yaw), math.cos(yaw), 0)
                        for index, delay in enumerate((.00, .08, .16, .24)):
                            side = -1 if index % 2 == 0 else 1
                            spot = location + right * (22 * side) + forward * (index * 5 - 7) + unreal.Vector(0, 0, 6)
                            pending.append((now + delay, template, spot, rotation, .38, True))
                    else:
                        for side in (-1, 1):
                            pending.append((now + .065, template, location + unreal.Vector(0, side * 18, 8), rotation, .37, False))
                for item in pending[:]:
                    due, template, location, rotation, scale, sparks_only = item
                    if now < due:
                        continue
                    pending.remove(item)
                    fx = unreal.GameplayStatics.spawn_emitter_at_location(rig['world'](), template, location, rotation,
                                                                         unreal.Vector(scale, scale, scale), False)
                    assert fx is not None
                    fx.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                    fx.set_editor_property('generate_overlap_events', False)
                    fx.set_editor_property('custom_time_dilation', 1.7)
                    if sparks_only:
                        fx.set_emitter_enable('Main Flames', False)
                        fx.set_emitter_enable('Wisps', False)
                    else:
                        fx.set_emitter_enable('Sparks', False)
                    particles.append(fx)
                    emissions.append((now, fx))
                for born, fx in emissions[:]:
                    if now - born > .055:
                        fx.deactivate()
                    if now - born > .7:
                        fx.destroy_component(fx)
                        particles.remove(fx)
                        emissions.remove((born, fx))
                contact_delay = .20 if variant == 'A1_cutting_sparks' else .08
                if hit_time is not None and not contact_captured and now - hit_time >= contact_delay:
                    rig['capture'](variant + '_contact')
                    contact_captured = True
                yield 1 / fps
            actual_damage = initial_health - rig['health'](ds[0])
            rig['check'](abs(actual_damage - 90) < .01, variant + ' keeps exactly one 90-damage native hit')
            rig['finish_video_clip']()
            report['A_studies'].append({'id': variant, 'label': label, 'hit_observed': hit_time is not None,
                                         'damage': actual_damage, 'radius': 70, 'speed': 220,
                                         'small_blade_unchanged': True, 'prototype_only': True})
            for fx in particles[:]:
                if _alive(fx):
                    fx.destroy_component(fx)
                particles.remove(fx)
            yield 5.3
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        rig['finish_video_clip']()
        if held:
            rig['cmd']('CountessComboQA.Mouse Release Left 0 0 0')
        for native in hidden:
            if _alive(native):
                native.set_visibility(True, False)
        for proxy in proxies:
            if _alive(proxy):
                helper['cleanup_preview'](proxy)
        for fx in particles:
            if _alive(fx):
                fx.destroy_component(fx)
        report['cleanup'] = True
        _write(out, 'sparrow-form-studies.json', report)
