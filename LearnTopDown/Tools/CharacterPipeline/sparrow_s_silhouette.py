"""Author the installed S silhouette/unfurl materials, then verify its lifecycle.

The body deliberately has no skin/albedo/noise texture and no transparency.
Only two project-owned materials are saved; source character packs are read only.
Root owns editor execution: call author(output) before PIE and sequence(rig) in PIE.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/Materials'
BODY = FOLDER + '/M_SparrowArchonSilhouette'
UNFURL = FOLDER + '/M_SparrowWingUnfurlAccent'
REFERENCE = 'https://eu.diablo3.blizzard.com/en-us/class/wizard/active/archon'


def _write(output, name, value):
    (Path(output) / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _material(path, opaque):
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            path.rsplit('/', 1)[1], FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    for key, value in {
            'blend_mode': unreal.BlendMode.BLEND_OPAQUE if opaque else unreal.BlendMode.BLEND_TRANSLUCENT,
            'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
            'two_sided': True, 'used_with_skeletal_mesh': True, 'used_with_clothing': True}.items():
        material.set_editor_property(key, value)
    return material


def _node(material, kind, **properties):
    node = unreal.MaterialEditingLibrary.create_material_expression(
        material, getattr(unreal, 'MaterialExpression' + kind))
    for key, value in properties.items():
        node.set_editor_property(key, value)
    return node


def _wire(source, target, name, pin=''):
    assert unreal.MaterialEditingLibrary.connect_material_expressions(source, pin, target, name)


def _custom(material, code, inputs, output_type):
    node = _node(material, 'Custom', code=code, output_type=output_type)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    node.set_editor_property('inputs', pins)
    return node


def author(output):
    output = Path(output).resolve()
    root = Path(unreal.Paths.project_dir()).resolve()
    assert output.is_relative_to(root / 'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    body = _material(BODY, True)
    silhouette = _custom(body, '''
// A solid, single-color body. No albedo, normal map, UV detail, or alpha holes.
float rim = pow(saturate(Facing), 1.6);
float3 core = BodyTint * (0.68 + 0.12 * saturate(Facing));
return core + float3(0.40, 0.34, 0.20) * rim;
''', ('Facing', 'BodyTint'), unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    _wire(_node(body, 'Fresnel', exponent=2.8, base_reflect_fraction=.035), silhouette, 'Facing')
    _wire(_node(body, 'VectorParameter', parameter_name='BodyTint',
                default_value=unreal.LinearColor(1.0, .72, .22, 1.0)), silhouette, 'BodyTint')
    assert lib.connect_material_property(silhouette, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(body)
    assert unreal.EditorAssetLibrary.save_loaded_asset(body, False)

    unfurl = _material(UNFURL, False)
    quill = _custom(unfurl, '''
float x = saturate(UV.x);
float y = (UV.y - 0.5) * 2.0;
float taper = pow(max(0.0, sin(x * 3.14159265)), 0.60) * (1.0 - 0.45 * x);
float edge = abs(y) / max(0.035, taper);
float body = pow(saturate(1.0 - edge), 1.6);
float spine = exp(-abs(y) * 19.0) * sin(x * 3.14159265);
float grain = 0.76 + 0.24 * sin(x * 82.0 + y * 19.0 - Clock * 7.0);
float fringe = body * grain;
float alpha = saturate((fringe * 0.64 + spine * 0.42) * Envelope);
float3 gold = float3(1.15, 0.72, 0.13) * (0.75 + 0.35 * grain);
float3 color = gold + float3(0.75, 0.65, 0.38) * spine;
return float4(color, alpha);
''', ('UV', 'Clock', 'Envelope'), unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    _wire(_node(unfurl, 'TextureCoordinate'), quill, 'UV')
    _wire(_node(unfurl, 'Time'), quill, 'Clock')
    _wire(_node(unfurl, 'ScalarParameter', parameter_name='Envelope', default_value=0.0), quill, 'Envelope')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = _node(unfurl, 'ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        _wire(quill, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(unfurl)
    assert unreal.EditorAssetLibrary.save_loaded_asset(unfurl, False)
    helper = runpy.run_path(str(root / 'Tools/CharacterPipeline/sparrow_bow_audit.py'))
    mesh = unreal.load_asset(helper['SKINS']['Rogue'])
    audit = helper['_inspect']('Rogue', mesh, unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem))
    assert 'error' not in audit
    report = {'passed': True, 'source_pack_assets_saved': False,
              'saved_materials': [BODY, UNFURL], 'body_is_opaque': True,
              'body_uses_textures': False, 'body_skin_audit': audit,
              'reference': REFERENCE,
              'reference_scope': 'Official text confirms an energy being. No claim that the previous implementation matched official footage.',
              'intent': 'Single-color solid gold silhouette; brief bilateral wing-unfurl rays, existing wing geometry retained.'}
    _write(output, 'sparrow-s-silhouette-assets.json', report)
    return report


def _snapshot(mesh, lods):
    return {'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
            'sections': [[bool(mesh.is_material_section_shown(i, lod['lod']))
                          for i in range(mesh.get_num_materials())] for lod in lods]}


def sequence(rig):
    output = Path(rig['OUT'])
    manifest = Path(os.environ.get('SPARROW_S_ASSETS', str(output / 'sparrow-s-silhouette-assets.json')))
    authored = json.loads(manifest.read_text(encoding='utf-8-sig'))
    lods = authored['body_skin_audit']['lods']
    report = {'passed': False, 'material': BODY, 'expected_duration': 40.0,
              'wing_geometry_changed': False, 'original_materials_restored': False}
    rig['switch']('sparrow')
    yield .8
    pawn = rig['pawn']()
    mesh = pawn.get_editor_property('mesh')
    original = _snapshot(mesh, lods)
    rig['case']('S_solid_silhouette_unfurl')
    ds = rig['layout']([(650, 0), (900, 350), (900, -350)])
    yield .2
    rig['use']('D', ds[0])
    yield 1.05
    rig['use']('S', ds[0])
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': 'S_solid_silhouette_unfurl',
                                    'prefix': 'S_solid_silhouette_unfurl_video',
                                    'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                                    'frame_times': []}
    yield .5
    wings = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))
    rig['check'](len(wings) == 1, 'S creates one native wing actor')
    remaining = rig['skills']().get_ascension_remaining()
    rig['check'](39.0 < remaining <= 40.0, 'S duration starts at40seconds')
    during = _snapshot(mesh, lods)
    parents = [mesh.get_material(i).get_base_material().get_path_name() for i in range(mesh.get_num_materials())]
    rig['check'](all(p.startswith(BODY + '.') for p in parents), 'S body uses solid silhouette material in every slot')
    rig['check'](all(not row[i] for row in during['sections'] for i in (3, 7, 13)), 'S still hides all cloak and hood sections')
    clones = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))
    rig['check'](len(clones) == 2, 'D has two clones during S')
    rig['check'](all(len(a.get_components_by_class(unreal.SkeletalMeshComponent)) == 1 for a in clones), 'D clones do not gain wings')
    quills = [c for c in wings[0].get_components_by_class(unreal.StaticMeshComponent)
              if 'SparrowUnfurlAccent' in [str(t) for t in c.get_editor_property('component_tags')]]
    rig['check'](len(quills) == 12, 'S uses twelve brief outward unfurl quills')
    rig['capture']('S_silhouette_entry_body')
    # The action starts after the cast lead-in. Frame23 (~0.8s from input) shows
    # the outward quills at full spread; the old0.5s capture could precede them.
    yield .3
    rig['capture']('S_silhouette_unfurl_peak')
    yield .6
    rig['capture']('S_solid_body_after_unfurl')
    yield .8
    rig['finish_video_clip']()
    rig['check'](all(not c.is_visible() for c in quills), 'S unfurl accents disappear after the entrance')
    rig['check'](rig['skills']().get_ascension_remaining() > 37.0, 'S remains active after entry accents finish')
    report.update({'remaining_after_entry': rig['skills']().get_ascension_remaining(),
                   'body_materials': parents, 'unfurl_components': len(quills)})
    if os.environ.get('SPARROW_S_SKIP_EXPIRY') != '1':
        yield 7.1
        rig['check'](rig['skills']().get_ascension_remaining() > 30.0, 'S survives the previous8second duration')
        yield rig['skills']().get_ascension_remaining() + .25
        after = _snapshot(mesh, lods)
        rig['check'](after == original, 'S expiry restores every original material and cloth section')
        rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings),
                     'S wing actor is removed after40seconds')
        report['original_materials_restored'] = after == original
        rig['capture']('S_silhouette_original_restored')
    else:
        report['expiry_not_tested'] = True
        rig['switch']('countess')
        yield .4
    report['passed'] = True
    _write(output, 'sparrow-s-silhouette.json', report)
