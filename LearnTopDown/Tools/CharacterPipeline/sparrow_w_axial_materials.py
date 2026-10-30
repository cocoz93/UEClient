"""Owned W materials: restrained ring accent, textured axial wind and a brief bow flash."""
import json
from pathlib import Path
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials'


def author_volley_fan(output):
    lib = unreal.MaterialEditingLibrary
    name = 'M_SparrowVolleyFan'
    path = FOLDER + '/' + name
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items(): item.set_editor_property(key, value)
        return item

    shader = '''
float2 p = float2(UV.x, (UV.y - 0.5) * 0.9);
float r = length(p);
float a = atan2(p.y, max(p.x, 0.0001));
float d = min(abs(a), min(min(abs(a-0.20944),abs(a+0.20944)),min(abs(a-0.418879),abs(a+0.418879))));
float edge = 1-smoothstep(0.425,0.46,abs(a));
float radial = smoothstep(0.04,0.13,r)*(1-smoothstep(0.82,1.03,r));
float front = 1-smoothstep(Progress,Progress+0.12,r);
float rays = exp(-pow(d/0.010,2))*0.7 + exp(-pow(d/0.032,2))*0.55;
float mask = saturate((rays+0.025)*(.25+.75*Noise)*edge*radial*front*Envelope);
return float4(12,7.5,2.5,mask);
'''
    custom = node('Custom', code=shader, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for name in ('UV', 'Noise', 'Progress', 'Envelope'):
        pin = unreal.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    custom.set_editor_property('inputs', pins)
    uv = node('TextureCoordinate')
    pan = node('Panner', speed_x=-2.8, speed_y=.18)
    assert lib.connect_material_expressions(uv, '', pan, 'Coordinate')
    texture = node('TextureSample', texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'))
    assert lib.connect_material_expressions(pan, '', texture, 'UVs')
    assert lib.connect_material_expressions(uv, '', custom, 'UV')
    assert lib.connect_material_expressions(texture, 'R', custom, 'Noise')
    for name, default in (('Progress', 0), ('Envelope', 0)):
        assert lib.connect_material_expressions(node('ScalarParameter', parameter_name=name, default_value=default), '', custom, name)
    for prop, rgba in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)), (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
        mask = node('ComponentMask', r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3])
        assert lib.connect_material_expressions(custom, '', mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report = {'passed': True, 'asset': path, 'fan_degrees': 48, 'textured_rays': 5, 'forward_length_cm': 700}
    (Path(output)/'volley-fan-material.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def author_hail_indicator(output):
    """Crisp Q boundary only; the original W air material remains unchanged."""
    lib = unreal.MaterialEditingLibrary
    name = 'M_SparrowHailBoundary'
    path = FOLDER + '/' + name
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items(): item.set_editor_property(key, value)
        return item

    def c(value): return node('Constant', r=float(value))

    def op(kind, a, b=None):
        item = node(kind)
        names = list(lib.get_material_expression_input_names(item))
        assert lib.connect_material_expressions(a, '', item, names[0])
        if b is not None: assert lib.connect_material_expressions(b, '', item, names[1])
        return item

    uv = node('TextureCoordinate')
    radius = op('Length', op('Subtract', uv, node('Constant2Vector', r=.5, g=.5)))
    # UV radius .36 still matches the existing 300cm gameplay radius. Full line width is about 5cm.
    shape = op('Power', op('Saturate', op('Subtract', c(1), op('Multiply',
        op('Abs', op('Subtract', radius, c(.36))), c(330)))), c(.5))
    envelope = node('ScalarParameter', parameter_name='Envelope', default_value=0)
    body = op('Multiply', shape, op('Multiply', envelope, c(1/.55)))
    color = node('Constant3Vector', constant=unreal.LinearColor(2.0, 1.45, .55, 1))
    assert lib.connect_material_property(op('Multiply', body, color), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert lib.connect_material_property(op('Multiply', body, c(.9)), '', unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'asset': path, 'passed': True, 'radius_cm': 300, 'full_line_width_cm': 5.05,
              'noise': False, 'refraction': False, 'fade_envelope_unchanged': True}
    (Path(output)/'hail-boundary-material.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def author_materials(output):
    lib = unreal.MaterialEditingLibrary
    noise_texture = unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur')
    assert noise_texture is not None, 'original Sparrow wind texture must exist'
    result = []
    for suffix in ('AirAccent', 'WindAxis', 'Pressure'):
        name = 'M_SparrowShot' + suffix
        path = FOLDER + '/' + name
        material = unreal.load_asset(path)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        assert material is not None, path
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        material.set_editor_property('refraction_method', unreal.RefractionMode.RM_INDEX_OF_REFRACTION)

        def node(kind, **props):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for key, value in props.items():
                item.set_editor_property(key, value)
            return item

        def c(value):
            return node('Constant', r=float(value))

        def op(kind, first, second=None):
            item = node(kind)
            names = list(lib.get_material_expression_input_names(item))
            assert lib.connect_material_expressions(first, '', item, names[0]), kind
            if second is not None:
                assert lib.connect_material_expressions(second, '', item, names[1]), kind
            return item

        def output_expr(expr, prop):
            assert lib.connect_material_property(expr, '', prop)

        uv = node('TextureCoordinate')
        center = node('Constant2Vector', r=.5, g=.5)
        centered = op('Subtract', uv, center)
        radius = op('Length', centered)
        envelope = node('ScalarParameter', parameter_name='Envelope', default_value=0)
        pan = node('Panner', speed_x=-2.8 if suffix == 'WindAxis' else .13,
                   speed_y=.12 if suffix == 'WindAxis' else .65)
        tiling = node('Constant2Vector', r=.65 if suffix == 'WindAxis' else 2,
                      g=5 if suffix == 'WindAxis' else 2)
        assert lib.connect_material_expressions(op('Multiply', uv, tiling), '', pan, 'Coordinate')
        texture = node('TextureSample', texture=noise_texture)
        assert lib.connect_material_expressions(pan, '', texture, 'UVs')
        noise = node('ComponentMask', r=True, g=False, b=False, a=False)
        assert lib.connect_material_expressions(texture, '', noise,
                                               lib.get_material_expression_input_names(noise)[0])
        if suffix == 'AirAccent':
            shape = op('Power', op('Saturate', op('Subtract', c(1), op('Multiply',
                op('Abs', op('Subtract', radius, c(.36))), c(16)))), c(1.8))
            texture_mask = op('Add', c(.12), op('Multiply', noise, c(.88)))
            opacity = .27
            color = (2.0, 1.45, .7)
            distortion = .1
        elif suffix == 'WindAxis':
            axis_masks = []
            for channel, exponent in (('r', .45), ('g', 1.8)):
                mask = node('ComponentMask', r=channel == 'r', g=channel == 'g', b=False, a=False)
                assert lib.connect_material_expressions(centered, '', mask,
                                                       lib.get_material_expression_input_names(mask)[0])
                axis_masks.append(op('Power', op('Saturate', op('Subtract', c(1),
                    op('Multiply', op('Abs', mask), c(2)))), c(exponent)))
            shape = op('Multiply', *axis_masks)
            texture_mask = op('Power', op('Saturate', op('Multiply',
                op('Subtract', noise, c(.08)), c(2.5))), c(1.2))
            opacity = .80
            color = (16.0, 10.0, 4.5)
            distortion = .12
        else:
            shape = op('Power', op('Saturate', op('Subtract', c(1),
                op('Multiply', radius, c(2)))), c(1.2))
            texture_mask = op('Add', c(.25), op('Multiply', op('Power', noise, c(.7)), c(.75)))
            opacity = .85
            color = (28.0, 20.0, 10.0)
            distortion = .12
        body = op('Multiply', op('Multiply', shape, texture_mask), envelope)
        output_expr(op('Multiply', body, c(opacity)), unreal.MaterialProperty.MP_OPACITY)
        gold = node('Constant3Vector', constant=unreal.LinearColor(*color, 1))
        # Axial wind and pressure use the mask in opacity once; squaring it here hid thin wisps.
        emissive = op('Multiply', body, gold) if suffix == 'AirAccent' else gold
        output_expr(emissive, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        refraction = op('Add', c(1), op('Multiply', op('Multiply', body,
            op('Subtract', noise, c(.5))), c(distortion)))
        output_expr(refraction, unreal.MaterialProperty.MP_REFRACTION)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), path
        result.append({'asset': path, 'opacity_multiplier': opacity,
                       'emissive': color, 'source_texture': noise_texture.get_path_name()})
    Path(output).mkdir(parents=True, exist_ok=True)
    (Path(output) / 'W-axial-materials.json').write_text(
        json.dumps({'passed': True, 'materials': result}, indent=2), encoding='utf-8')
    return result
