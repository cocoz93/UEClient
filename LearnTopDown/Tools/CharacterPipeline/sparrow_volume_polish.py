"""Production atmosphere material and scoped real-game review for Sparrow FX depth."""
import json
import unreal


def author(out):
    lib = unreal.MaterialEditingLibrary
    folder = '/Game/TopDown/Characters/Sparrow/Materials'
    name = 'M_SparrowHailAtmosphere'
    material = unreal.load_asset(folder + '/' + name)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert material
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    custom = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom.set_editor_property('code', '''
float2 p=(UV-.5)*2.;
float r=length(p);
float edge=pow(saturate(1.-r*r),1.6);
float cloud=Texture2DSample(Cloud,CloudSampler,UV*1.8+float2(T*.035,-T*.021)).r;
float grain=Texture2DSample(Cloud,CloudSampler,UV.yx*3.7+float2(-T*.026,T*.018)).r;
float wisp=pow(saturate(cloud*.9+grain*.7-.37),1.6);
float flow=.68+.32*sin(r*15.-T*2.3+cloud*4.);
float mask=edge*wisp*flow*Envelope;
return float4(float3(3.2,2.1,.7)*(.7+wisp),saturate(mask*.65));
''')
    inputs = []
    for n in ('UV', 'T', 'Envelope', 'Cloud'):
        i = unreal.CustomInput()
        i.set_editor_property('input_name', n)
        inputs.append(i)
    custom.set_editor_property('inputs', inputs)
    uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
    time = lib.create_material_expression(material, unreal.MaterialExpressionTime)
    envelope = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
    envelope.set_editor_property('parameter_name', 'Envelope')
    envelope.set_editor_property('default_value', 1.)
    texture = lib.create_material_expression(material, unreal.MaterialExpressionTextureObject)
    texture.set_editor_property('texture', unreal.load_asset(
        '/Game/ParagonSparrow/FX/Textures/Smoke/T_TilingClouds_01'))
    assert texture.get_editor_property('texture')
    for node, n in ((uv, 'UV'), (time, 'T'), (envelope, 'Envelope'), (texture, 'Cloud')):
        assert lib.connect_material_expressions(node, '', custom, n)
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
        mask = lib.create_material_expression(material, unreal.MaterialExpressionComponentMask)
        for key, value in zip(('r','g','b','a'), channels):
            mask.set_editor_property(key, value)
        assert lib.connect_material_expressions(custom, '', mask, '')
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'passed': True, 'saved_materials': [folder+'/'+name], 'original_pack_saved': False}
    (out/'volume-materials.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def sequence(rig):
    """Reuse the arsenal checks; add native E and preparation/final-impact visual samples."""
    case, use, capture = rig['case'], rig['use'], rig['capture']
    rig['switch']('sparrow')
    yield .8
    case('W_volume_release')
    targets = rig['layout']([(650,0),(750,350),(750,-350)])
    yield .2
    use('W', targets[0])
    yield .67
    capture('W_pressure_peak')
    yield .10
    capture('W_pressure_tail')
    yield 1.7
    rig['recovered']()
    case('E_volume_native')
    targets = rig['layout']([(850,0),(850,350),(850,-350)])
    yield .2
    # Resetting a training dummy's HP does not clear Sparrow's target-specific passive stacks.
    initial_stacks = rig['skills']().get_relentless_stacks(targets[0])
    expected_health = 100. - sum(10. * (1. + min(initial_stacks + i, 10) * .0175) for i in range(6))
    use('E', targets[0])
    yield .26
    capture('E_release')
    yield .29
    capture('E_flight_and_hit')
    yield .35
    capture('E_final_volley')
    yield .8
    rig['check'](abs(rig['health'](targets[0])-expected_health)<.02, 'E retains six-shot damage and passive cadence')
    rig['recovered']()
    case('Q_volume_finish')
    targets = rig['layout']([(570,80),(450,430),(-600,-400)])
    yield .2
    use('Q', offset=(450,0))
    yield .9
    capture('Q_volume')
    yield 2.95
    capture('Q_final_impact')
    yield 1.
    rig['recovered']()
    case('A_volume_impact')
    targets = rig['layout']([(450,0),(750,0),(450,350)])
    yield .2
    use('A', targets[0])
    yield .8
    capture('A_volume_flight')
    yield .9
    capture('A_volume_impact')
    yield 4.7
    rig['recovered']()
    case('S_volume_unfold')
    use('S', offset=(650,0))
    yield .52
    capture('S_unfold')
    yield 8.3
    rig['recovered']()
    case('D_volume_arrival')
    use('D', offset=(650,0))
    yield .18
    capture('D_materializing')
    yield .28
    capture('D_arrival')
    yield .8
    targets = rig['layout']([(850,0),(850,350),(850,-350)])
    use('E', targets[0])
    yield .5
    capture('D_volley')
    yield 1.
    rig['switch']('countess')
    yield .7
    rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowMirrorArcher),
                 'volume review owner switch cleans mirrors')
