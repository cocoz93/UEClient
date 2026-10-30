"""D1-4 physical-bow material family; baseline D and original assets are untouched.

author(output) is executed only by the parent editor session. Four interpolated
instance values provide continuous UVs across each skeletal-bone-following path.
"""
import hashlib
import json
from pathlib import Path

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/FX/BowMuzzle20261027'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
WISPS = '/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps'
RAYS = '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays'

COMMON = r'''
float x=PathStart+UV.x*PathSpan;
float y=UV.y;
float2 adv=float2(x*2.8+Age*1.35+Seed*.71,y*.85+Seed*.31);
float n=Texture2DSample(Noise,NoiseSampler,adv).r;
float fine=Texture2DSample(Noise,NoiseSampler,float2(x*11.+Age*3.2,y*3.7+Seed)).g;
float3 wisp=Texture2DSample(Wisps,WispsSampler,float2(x*1.25+Age*.87+Seed,.08+y*.84)).rgb;
float3 ray=Texture2DSample(Rays,RaysSampler,float2(frac(x*.43+Age*.62+Seed*.23),y)).rgb;
float ends=smoothstep(0.,.022,x)*(1.-smoothstep(.97,1.,x));
float3 amber=float3(.68,.17,.013), gold=float3(2.6,1.08,.11), ivory=float3(4.8,3.45,1.25);
// Only the combined D4 reduces the white overlap. Existing D1-3 default to zero.
ivory*=lerp(1.,.70,Confluence);
float level=(.68+Charge*.32+Pulse*.55)*Envelope*OpacityScale;
'''

COATING = r'''
if (Refinement > .5) {
    float y0=abs(y-.5)*2.;
    float body=1.-smoothstep(.64,.96,y0);
    float spine=exp(-pow((y-.5)/.065,2.));
    float barbs=pow(saturate(cos(x*105.-y0*12.)),10.)*body;
    float pulse=pow(saturate(.5+.5*cos(x*16.+Age*9.+Seed)),16.);
    float3 col=float3(.22,.105,.018)+gold*(body*.27+barbs*.36)+ivory*(spine*.27+pulse*barbs*.45);
    return float4(col,(body*.52+barbs*.34+spine*.18)*ends*level);
}
// A textured surface hugs the limb. Dark channels remain between its gold fibres.
float d=abs(y-.5);
float veil=exp(-d*d*12.)*saturate(.29+n*.35+wisp.r*.42);
float centre=.5+(n-.5)*.10;
float core=exp(-pow((y-centre)/.135,2.))* (.58+.28*ray.g+.14*n);
float seams=pow(saturate(cos((y*3.+n*.13)*6.283)),8.)*exp(-d*d*14.)*wisp.g;
float coverage=saturate(veil*.90+core*.65+seams*.25)*ends;
float3 color=gold*(.42+veil*.8)+ivory*core*.30;
return float4(color*(1.+Pulse*.25),coverage*level);
'''

CURRENT = r'''
// Several slim silk-like currents follow the actual limb, with a soft, torn lip.
float centre=.5+sin(x*13.+Age*4.1+Seed*6.)*.065+(n-.5)*.13;
float d=abs(y-centre);
float body=exp(-d*d*17.)*saturate(.32+wisp.r*.36+n*.35);
float fibre=exp(-pow(d/.12,2.))*(.55+.30*ray.g+.15*n);
float side=exp(-pow((d-.22)/.07,2.))*wisp.g*.24;
float alpha=saturate(body*.95+fibre*.60+side)*ends;
float3 color=gold*(.45+body*.85+side)+ivory*fibre*.34;
return float4(color,alpha*level);
'''

THREAD = r'''
// The fan must read as taut strings rather than wavering arcs or a filled veil.
float d=abs(y-.5);
float core=exp(-d*d*48.);
float halo=exp(-d*d*13.)*.28;
float packet=pow(saturate(cos((x+Age*2.2+Seed*.37)*14.)),20.);
float brightness=.90+packet*(.25+Refinement*.45)+Pulse*.35;
return float4((gold*.73+ivory*core*.30)*brightness,(core*.78+halo)*ends*level);
'''

FEATHER = r'''
// Short tongues are attached to the bow. They do not form detached wings.
float centre=.5+sin(x*3.14159)*.11;
float halfWidth=.38*pow(saturate(sin(x*3.14159)),.72);
float d=abs(y-centre);
float body=saturate((halfWidth-d)/.075);
float vein=exp(-pow((y-centre)/.085,2.));
float barbs=pow(saturate(cos((x*4.-d*3.3+n*.08)*6.283)),6.);
float texture=saturate(.24+wisp.r*.35+n*.24+barbs*.28);
float alpha=(body*texture*.95+vein*.45)*ends;
float3 color=gold*(.38+texture*.80+barbs*.16)+ivory*vein*.25;
return float4(color,alpha*level);
'''

EMBER = r'''
float2 q=float2((UV.x-.5)*1.3,(y-.5)*2.4);
float centre=exp(-dot(q,q)*32.);
float halo=exp(-dot(q,q)*8.)*.23;
float twinkle=.64+.36*sin(Age*18.+Seed*37.);
return float4(gold+ivory*centre*.52,(centre+halo)*level*twinkle);
'''


def _material(name, code, textures):
    lib = unreal.MaterialEditingLibrary
    path = FOLDER + '/M_BowMuzzle' + name
    digest = hashlib.sha256((COMMON + code + NOISE + WISPS + RAYS + 'instance-v1').encode()).hexdigest()
    material = unreal.load_asset(path)
    reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'BowMuzzleHash') == digest)
    if not reused:
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                path.rsplit('/', 1)[1], FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        if material is None:
            raise RuntimeError('Cannot create ' + path)
        for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY):
            lib.disconnect_material_property(material, prop)
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)

        def node(kind, **props):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for key, value in props.items():
                item.set_editor_property(key, value)
            return item

        shader = node('Custom', code=COMMON + code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate')}
        for key, texture in zip(('Noise', 'Wisps', 'Rays'), textures):
            sources[key] = node('TextureObject', texture=texture)
        for key, value in [('Age', 0.), ('Envelope', 1.), ('Charge', 1.), ('Pulse', 0.), ('Confluence', 0.), ('Refinement', 0.)]:
            sources[key] = node('ScalarParameter', parameter_name=key, default_value=value)
        for index, (key, default) in enumerate([('PathStart', 0.), ('PathSpan', 1.), ('Seed', 0.), ('OpacityScale', 1.)]):
            instance = node('PerInstanceCustomData', data_index=index, const_default_value=default)
            interpolator = node('VertexInterpolator')
            assert lib.connect_material_expressions(instance, '', interpolator, 'VS')
            sources[key] = interpolator
        inputs = []
        for key in sources:
            value = unreal.CustomInput()
            value.set_editor_property('input_name', key)
            inputs.append(value)
        shader.set_editor_property('inputs', inputs)
        for key, source in sources.items():
            assert lib.connect_material_expressions(source, '', shader, key), key
        for prop, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
            mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
    usage = unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES
    lib.set_material_usage(material, usage)
    if not lib.has_material_usage(material, usage):
        raise RuntimeError('Missing instanced mesh usage: ' + path)
    errors = [str(item) for item in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError(path + ': ' + '\n'.join(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'BowMuzzleHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return {'path': path, 'hash': digest, 'reused': reused, 'compile_errors': errors,
            'instanced_mesh_usage': True, 'continuous_path_uv': True}


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    unreal.EditorAssetLibrary.make_directory(FOLDER)
    result = {'passed': False, 'styles': [1, 2, 3, 4], 'default_style': 0, 'materials': [],
              'original_assets_changed': False, 'gameplay_changed': False,
              'textures': [NOISE, WISPS, RAYS], 'visual_acceptance': 'pending actual game capture'}
    try:
        textures = [unreal.load_asset(path) for path in result['textures']]
        if not all(textures):
            raise RuntimeError('D bow study texture unavailable')
        for name, code in [('Coating', COATING), ('Current', CURRENT), ('Thread', THREAD),
                           ('Feather', FEATHER), ('Ember', EMBER)]:
            result['materials'].append(_material(name, code, textures))
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (output / 'bow-muzzle-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
