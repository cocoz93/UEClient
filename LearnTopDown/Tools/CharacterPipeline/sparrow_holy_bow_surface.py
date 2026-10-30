"""Author only the E-owned curved bow surface; imported packs stay read-only."""
import json
from pathlib import Path
import unreal


def author(out):
    path = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowHolyBowFeather'
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(path)
    if material is None:
        folder, name = path.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)

    def node(kind, **properties):
        result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in properties.items():
            result.set_editor_property(key, value)
        return result

    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code=r'''
struct FBow {
    float2 Curve(float p) {
        float t=p<.64 ? p/.64 : (p-.64)/.36;
        float u=1.-t;
        float2 a=p<.64 ? float2(0,0) : float2(13,89);
        float2 b=p<.64 ? float2(0,35) : float2(-10,106);
        float2 c=p<.64 ? float2(33,57) : float2(-32,123);
        float2 d=p<.64 ? float2(13,89) : float2(-23,140);
        return u*u*u*a+3.*u*u*t*b+3.*u*t*t*c+t*t*t*d;
    }
    float Distance(float2 p,float2 a,float2 b) {
        float2 ab=b-a;
        return length(p-a-ab*saturate(dot(p-a,ab)/max(dot(ab,ab),.0001)));
    }
};
FBow B;
float2 p=(UV-.5)*float2(220.,400.);
p.y/=max(.12,Open);
float2 q=float2(p.x,abs(p.y));
float edge=1000.,center=1000.,nearest=0.,echo=0.,filigree=0.,filigreeHalo=0.,inlay=0.;
for(int i=0;i<32;i++) {
    float a=i/32.,b=(i+1)/32.;
    float2 pa=B.Curve(a),pb=B.Curve(b);
    float d=B.Distance(q,pa,pb);
    float width=lerp(4.4,.7,b)+2.8*sin(b*3.14159265);
    edge=min(edge,d-width);
    if(d<center) {center=d;nearest=b;}
    // Three tapering ribs grow from the same limb. Their open gaps survive the game camera.
    for(int j=1;j<=3;j++) {
        float spanA=sin(saturate((a-.12)/.88)*3.14159265);
        float spanB=sin(saturate((b-.12)/.88)*3.14159265);
        float2 ra=pa+float2(-j*11.*spanA, j*2.4*spanA);
        float2 rb=pb+float2(-j*11.*spanB, j*2.4*spanB);
        float rd=B.Distance(q,ra,rb);
        float rw=(1.4+.75*sin(a*3.14159265))*spanA;
        float mask=smoothstep(.12,.20,a);
        filigree=max(filigree,(1.-smoothstep(rw*.45,rw+.6,rd))*mask);
        filigreeHalo=max(filigreeHalo,exp(-max(0.,rd-rw)*.24)*.22*mask);
    }
    float2 ia=pa+float2(2.5*sin(a*18.),0.);
    float2 ib=pb+float2(2.5*sin(b*18.),0.);
    inlay=max(inlay,exp(-B.Distance(q,ia,ib)*1.8));
    for(int j=1;j<=2;j++) {
        float2 offset=float2(j*9.*sin(a*3.14159265),0.);
        float de=B.Distance(q,pa+offset,pb+offset);
        echo+=exp(-de*1.2)*.36*(1.-smoothstep(.18,.48,Age));
    }
}
float grain=Texture2DSample(Detail,DetailSampler,UV*float2(2.1,3.6)+float2(-Age*.7,Age*.19)).r;
float ornamentEdge=1000.,featherSpine=0.,featherVeins=0.;
// Feather fans share roots with each curved limb. Their longer tips fan backward,
// with open gaps rather than a detached wing in front of the arrow.
float fan=smoothstep(.08,.28,Age);
for(int f=0;f<5;f++) {
    float2 root=B.Curve(.38+f*.13);
    float2 tip=root+float2((-62.+f*7.)*lerp(.28,1.,fan),34.+f*5.);
    float2 c1=root+float2(-22.*fan,4.);
    float2 c2=tip+float2(14.,-18.);
    for(int k=0;k<12;k++) {
        float a=k/12.,b=(k+1)/12.,u=1.-a,v=1.-b;
        float2 pa=u*u*u*root+3.*u*u*a*c1+3.*u*a*a*c2+a*a*a*tip;
        float2 pb=v*v*v*root+3.*v*v*b*c1+3.*v*b*b*c2+b*b*b*tip;
        float width=(5.3-f*.45)*pow(sin(b*3.14159265),.8);
        float distance=B.Distance(q,pa,pb);
        ornamentEdge=min(ornamentEdge,distance-width);
        featherSpine=max(featherSpine,exp(-distance*2.)*sin(b*3.14159265));
        float barbs=pow(saturate(sin(b*88.+distance*1.4)),10.);
        featherVeins=max(featherVeins,barbs*saturate(1.-distance/max(width,.1))*.35);
    }
}
float ornament=1.-smoothstep(-.5,.6,ornamentEdge);
float ornamentRim=exp(-abs(ornamentEdge)*2.);
float ornamentGlow=exp(-max(ornamentEdge,0.)*.26)*.18;
float body=1.-smoothstep(-.8,.9,edge+(grain-.5)*1.4);
float rim=exp(-abs(edge)*1.5);
float halo=exp(-max(edge,0.)*.18)*.24;
float runner=exp(-pow((nearest-saturate(Age/.23))/.095,2.))*(1.-smoothstep(.23,.45,Age));
float stringDistance=B.Distance(q,float2(-23,140),float2(-17.-54.*Draw,0));
float stringCore=exp(-stringDistance*2.8);
float stringGlow=exp(-stringDistance*.45)*.10;
float gem=0.,gemHalo=0.;
for(int g=0;g<3;g++) {
    float2 gp=B.Curve(.23+g*.25);
    float2 v=q-gp;
    float diamond=abs(v.x)/4.5+abs(v.y)/8.;
    gem=max(gem,exp(-abs(diamond-1.)*7.)+exp(-diamond*4.)*.8);
    gemHalo=max(gemHalo,exp(-length(v)*.16)*.28);
}
float3 gold=float3(2.1,1.05,.18);
float3 white=float3(3.0,2.7,1.9);
float veins=pow(saturate(grain),2.)*(.55+.45*sin(nearest*40.-Age*12.));
float3 color=gold*(body*(.32+veins*.33)*(1.-inlay*.72)+halo+echo+stringGlow+filigreeHalo)
    +white*(rim*.68+runner*(body+filigree)*.9+stringCore*.75+filigree*(.55+grain*.3)+gem*.75+gemHalo)
    +gold*(ornament*(.24+grain*.20)+ornamentGlow*.7)
    +white*(ornamentRim*.40+featherSpine*.32+featherVeins);
float alpha=saturate(body*.9+rim*.8+halo+echo+stringCore*.8+stringGlow+filigree+filigreeHalo+gem+gemHalo+ornament+ornamentRim*.5+ornamentGlow);
return float4(color*(1.+Pulse*.35),alpha*Envelope*Open);
''')
    names = ('UV', 'Age', 'Open', 'Draw', 'Pulse', 'Envelope', 'Detail')
    inputs = []
    for name in names:
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    shader.set_editor_property('inputs', inputs)
    texture_path = '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'
    texture = unreal.load_asset(texture_path)
    assert isinstance(texture, unreal.Texture2D)
    sources = {'UV': node('TextureCoordinate'), 'Detail': node('TextureObject', texture=texture)}
    for name, value in (('Age', 0.), ('Open', 1.), ('Draw', 1.), ('Pulse', 0.), ('Envelope', 1.)):
        sources[name] = node('ScalarParameter', parameter_name=name, default_value=value)
    for name, source in sources.items():
        assert lib.connect_material_expressions(source, '', shader, name)
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        assert lib.connect_material_expressions(shader, '', mask, '')
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'passed': True, 'material': path, 'read_only_texture': texture_path,
              'outline': 'enlarged recurved bow with five rooted feather blades per limb, engraved veins and three filigree ribs; no detached front wings',
              'visual_acceptance': 'pending actual game view'}
    (Path(out) / 'holy-bow-surface.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
