"""Author Sparrow-owned E arrow surface from the inspected Holy Arrow outline.

Only M_SparrowHolyArrow is saved. Paragon source texture/materials remain read-only.
Native E retains six shots, its existing travel speed, hit rules and recovery.
"""
import json
from pathlib import Path

import unreal


MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowHolyArrow'
TEXTURE = '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'


def author(out):
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(TEXTURE)
    assert isinstance(texture, unreal.Texture2D), TEXTURE
    material = unreal.load_asset(MATERIAL)
    if material is None:
        folder, name = MATERIAL.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material), MATERIAL
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **values):
        result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
        for key, value in values.items():
            result.set_editor_property(key, value)
        return result

    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code=r'''
struct FArrowShape {
    float Stroke(float2 p, float2 a, float2 b, float width) {
        float2 ab=b-a;
        float t=saturate(dot(p-a,ab)/max(dot(ab,ab),.0001));
        float d=length(p-a-ab*t);
        return 1.-smoothstep(width,width+.009,d);
    }
    float Triangle(float2 p,float2 a,float2 b,float2 c) {
        float2 e0=b-a,e1=c-b,e2=a-c;
        float s=sign(e0.x*(c-a).y-e0.y*(c-a).x);
        float d0=s*(e0.x*(p-a).y-e0.y*(p-a).x)/length(e0);
        float d1=s*(e1.x*(p-b).y-e1.y*(p-b).x)/length(e1);
        float d2=s*(e2.x*(p-c).y-e2.y*(p-c).x)/length(e2);
        return smoothstep(-.009,.009,min(d0,min(d1,d2)));
    }
};
FArrowShape S;
float2 p=(UV-.5)*2.;
float shaft=S.Stroke(p,float2(-.85,0.),float2(.80,0.),.019);
float head=S.Triangle(p,float2(.07,-.105),float2(.97,0.),float2(.07,.105));
float fins=0.;
float veins=0.;
for(int side=-1;side<=1;side+=2){
    float2 q=float2(p.x,p.y*side);
    fins=max(fins,S.Triangle(q,float2(-.10,.035),float2(.74,.33),float2(.28,.105)));
    fins=max(fins,S.Triangle(q,float2(-.29,.022),float2(.37,.47),float2(.02,.14)));
    veins=max(veins,S.Stroke(q,float2(-.18,.035),float2(.64,.29),.010));
}
float tail=S.Stroke(p,float2(-.94,0.),float2(-.48,0.),.031)*smoothstep(-.99,-.62,p.x);
float spark=(1.-smoothstep(.014,.060,length(p-float2(-.60,0.))))*.52;
float texture=Texture2DSample(Detail,DetailSampler,float2(UV.x*2.-Clock*.48,UV.y*1.4)).r;
float grain=.80+.20*saturate(texture);
float mask=saturate(max(max(shaft,head),max(fins,tail))+spark);
float3 white=float3(1.9,1.81,1.38)*(head+fins*.82)*grain;
float3 gold=float3(1.65,.89,.17)*(shaft*.72+tail*.32+veins*.50+spark*.55);
float3 color=white+gold;
return float4(color*Strength,mask*saturate(Strength));
''')
    inputs = []
    for name in ('UV', 'Clock', 'Strength', 'Detail'):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    shader.set_editor_property('inputs', inputs)
    for source, target in ((node('TextureCoordinate'), 'UV'), (node('Time'), 'Clock'),
                           (node('ScalarParameter', parameter_name='Strength', default_value=1.), 'Strength'),
                           (node('TextureObject', texture=texture), 'Detail')):
        assert lib.connect_material_expressions(source, '', shader, target)
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        assert lib.connect_material_expressions(shader, '', mask, '')
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'passed': True, 'saved_material': MATERIAL, 'source_texture_read_only': TEXTURE,
              'source_materials_saved': False, 'outline': 'platinum spear tip with two symmetric split fins, narrow gold shaft and short rear point',
              'reference': 'sparrow-E-15_433.png', 'gameplay_changed_by_author': False,
              'visual_acceptance': 'pending actual E gameplay review'}
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/'holy-arrow-surface.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
