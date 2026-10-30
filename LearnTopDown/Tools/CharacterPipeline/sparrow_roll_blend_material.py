"""Author only F's owned translucent silhouette; existing form/echo materials stay unchanged."""
import json
from pathlib import Path
import unreal


def author(output):
    output = Path(output).resolve()
    assert output.is_relative_to(Path(unreal.Paths.project_dir()).resolve() / 'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    path = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowRollBlend'
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_SparrowRollBlend', path.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': False, 'used_with_skeletal_mesh': True,
                       'used_with_clothing': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **properties):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in properties.items():
            item.set_editor_property(key, value)
        return item

    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float rim=pow(saturate(Facing),1.6);
float3 body=BodyTint*(.68+.12*saturate(Facing))+float3(.40,.34,.20)*rim;
return float4(body,saturate(Visibility));
''')
    inputs = []
    for key in ('Facing', 'BodyTint', 'Visibility'):
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', key)
        inputs.append(pin)
    shader.set_editor_property('inputs', inputs)
    sources = {'Facing': node('Fresnel', exponent=2.8, base_reflect_fraction=.035),
               'BodyTint': node('VectorParameter', parameter_name='BodyTint',
                                default_value=unreal.LinearColor(1.35, .85, .10, 1.0)),
               'Visibility': node('ScalarParameter', parameter_name='Visibility', default_value=0.0)}
    for key, source in sources.items():
        assert lib.connect_material_expressions(source, '', shader, key)
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        assert lib.connect_material_expressions(shader, '', mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report = {'passed': True, 'saved': path, 'other_materials_modified': False,
              'blend': 'translucent', 'visibility': 'linear opacity'}
    (output / 'roll-blend-material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
