"""Keep the older wrapper assets and author vortex texture for A's native rims.

The live geometry uses the existing two gear planes, without enclosing shells.
Travel, rotation, crackle and hit handling remain native.
"""
import hashlib
import json
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026'
FORM_ROOT = '/Game/TopDown/Characters/Sparrow/Materials/ArsenalAscended20261026'
FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
FORM_FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_PerlinPlasma_Noisey_Packed'

COMMON = r'''
float2 p=(UV-.5)*2.;
float r=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.65,.003);
float n=Texture2DSample(Flow,FlowSampler,UV*2.1+float2(Age*.17,-Age*.38)+Index*.13).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*7.1+float2(-Age*.41,Age*.25)+Index*.19).g;
float3 gold=float3(1.35,.38,.035);
float3 warm=float3(2.8,1.3,.23);
float3 white=float3(4.3,3.2,1.2);
float3 rgb=0.; float alpha=0.;
'''

BODY = r'''
// Larger, darker wind faces surround the existing gear; the central opening
// deliberately carries no body opacity or glow.
float2 q=float2(p.x*.92,p.y*1.08);
float rr=length(q); float ang=atan2(q.y,q.x);
float hollow=smoothstep(.42,.58,rr);
float edge=1.-smoothstep(.77,.97,rr);
float mask=hollow*edge;
float phase=ang*3.-rr*9.5+Age*13.+Index*2.15;
float tongue=pow(saturate(cos(phase+n*1.6)),2.6);
float crest=pow(saturate(cos(phase+.24+n*1.6)),20.);
float broken=smoothstep(.19,.68,n*.7+fine*.4);
float tissue=tongue*(.18+n*.65+fine*.25)*mask;
float glint=crest*mask*broken;
float innerFlow=pow(saturate(cos(ang*5.+rr*17.-Age*19.+Index)),12.);
innerFlow*=exp(-pow((rr-.65)/.085,2.))*broken;
float outerDust=pow(saturate(fine*1.9-.8),5.)*exp(-pow((rr-.85)/.12,2.));
rgb=gold*(tissue*2.0+outerDust*.65)+warm*(tissue*.65+innerFlow*.75)+white*glint*.55;
alpha=tissue*.56+glint*.30+innerFlow*.26+outerDust*.21;
'''

RIM = r'''
// A broken spiral around the front gear's outside edge, never a solid halo.
float hollow=smoothstep(.55,.64,r);
float outer=1.-smoothstep(.84,.97,r);
float mask=hollow*outer;
float phase=a*3.-r*14.+Age*11.;
float tongue=pow(saturate(cos(phase+n*1.4)),2.);
float crest=pow(saturate(cos(phase+.26+n*1.4)),14.);
float grain=smoothstep(.20,.72,n*.72+fine*.45);
float tissue=tongue*(.22+grain*.72)*mask;
float glint=crest*mask*pow(saturate(fine*.7+n*.65),2.8);
float shards=0.;
for(int i=0;i<18;++i) {
    float h=frac(sin(float(i)*47.23)*1751.93);
    float angle=float(i)*2.39996-Age*(1.7+h*.8);
    float2 radial=float2(cos(angle),sin(angle));
    float2 d=p-radial*(.72+h*.17);
    float axial=dot(d,radial), lateral=d.x*radial.y-d.y*radial.x;
    float gate=pow(saturate(sin(Age*8.+h*19.)),3.);
    shards+=exp(-pow(axial/(.015+h*.013),2.)-pow(lateral/(.028+h*.035),2.))*gate;
}
rgb=gold*tissue*1.75+warm*(tissue*.65+shards*.6)+white*glint*.55;
alpha=tissue*.62+glint*.38+shards*.45;
'''

END = r'''
float frame=smoothstep(0.,.025,UV.x)*(1.-smoothstep(.975,1.,UV.x))*smoothstep(0.,.025,UV.y)*(1.-smoothstep(.975,1.,UV.y));
float envelope=smoothstep(.0,.09,Age)*frame;
return float4(rgb*envelope*(1.+Pulse*.32),saturate(alpha)*envelope);
'''

# The form adds narrow branching energy veins in the outer wind faces.
# Both veins and fragments are masked outside the central gear opening.
ASCENDED_BODY = BODY + r'''
float arc=0.;
for(int j=0;j<3;++j) {
    float phase2=ang*4.-rr*11.+Age*17.+j*2.094+Index*1.4;
    float fork=sin(rr*45.+Age*9.+j)*.22+sin(rr*89.-Age*7.+j)*.09;
    float vein=pow(saturate(cos(phase2+fork)),30.);
    float gate=pow(saturate(sin(ang*2.-Age*8.+j*3.2)),2.);
    arc+=vein*gate*mask;
}
float reverse=pow(saturate(cos(ang*5.+rr*14.-Age*19.+Index)),5.)*mask*(.22+fine*.65);
rgb=rgb*1.15+warm*reverse*.8+white*arc*.68;
alpha=saturate(alpha+reverse*.22+arc*.36);
'''

ASCENDED_RIM = RIM + r'''
float paired=pow(saturate(cos(a*6.+r*17.-Age*16.)),18.);
paired*=exp(-pow((r-.78)/.12,2.))*(.35+fine*.65);
float teeth=pow(saturate(cos(a*12.+Age*9.)),20.)*exp(-pow((r-.66)/.075,2.));
rgb=rgb*1.15+white*paired*.72+warm*teeth*.9;
alpha=saturate(alpha+paired*.40+teeth*.30);
'''

# The old vortex's amber tissue/white crest now follows each tooth, within the
# native gear footprint. Its flow remains textured instead of becoming a halo.
GEAR_RIM = RIM.replace('float hollow=smoothstep(.55,.64,r);',
    'float hollow=smoothstep(.48,.58,r);').replace(
    'float outer=1.-smoothstep(.84,.97,r);',
    'float tipRadius=.73+.16*smoothstep(.08,.82,cos(a*10.-r*5.2));\nfloat outer=1.-smoothstep(tipRadius-aa,tipRadius+aa,r);').replace(
    'float tissue=tongue*(.22+grain*.72)*mask;',
    'float tissue=(.16+tongue*.84)*(.22+grain*.72)*mask;').replace(
    'rgb=gold*tissue*1.75', 'shards*=mask;\nrgb=gold*tissue*1.75') + r'''
float toothEdge=exp(-pow((r-tipRadius)/(.010+aa),2.))*hollow*(.18+grain*.5);
float innerSeam=exp(-pow((r-.585)/(.010+aa),2.))*(.16+tongue*.45);
rgb+=white*toothEdge*.38+warm*innerSeam*.45;
alpha+=toothEdge*.35+innerSeam*.30;
'''
ASCENDED_GEAR_RIM = GEAR_RIM.replace(
    'float tipRadius=.73+.16*smoothstep(.08,.82,cos(a*10.-r*5.2));',
    'float bladeSector=frac((a+3.14159265)*1.43239449-r*.18);\nfloat bladeTip=pow(saturate(min(bladeSector/.18,(1.-bladeSector)/.82)),2.2);\nfloat tipRadius=.66+.31*bladeTip;').replace(
    'float toothEdge=exp(-pow((r-tipRadius)/(.010+aa),2.))*hollow*(.18+grain*.5);',
    'float toothEdge=exp(-pow((r-tipRadius)/(.006+aa*.30),2.))*hollow*(.35+grain*.55);') + r'''
// A dense rotating storm stays inside the actual gear, with a dark core and
// separated bright crests. The outside silhouette still follows its teeth.
float stormMask=smoothstep(.055,.13,r)*(1.-smoothstep(.74,.88,r));
float stormField=Texture2DSample(Flow,FlowSampler,float2(a*.31830989+r*.19+Age*.31,r*1.7-Age*.54)).r;
float stormDetail=Texture2DSample(Flow,FlowSampler,float2(a*.63661977-r*.27-Age*.18,r*3.2+Age*.37)).g;
float stormPhase=a*3.-r*7.0+Age*12.+stormField*.65;
float stormErosion=smoothstep(.14,.64,stormField*.72+stormDetail*.50);
float stormFace=pow(saturate(.58+.42*cos(stormPhase)),1.4)*stormMask*(.40+stormErosion*.60);
float stormCrest=pow(saturate(cos(stormPhase+.28)),13.)*stormMask*smoothstep(.18,.64,stormDetail);
float innerTurn=pow(saturate(.35+.65*cos(a*2.+r*9.-Age*15.)),2.6)*exp(-pow((r-.36)/.23,2.))*(.22+stormDetail*.62);
float nearEye=exp(-pow((r-.19)/.048,2.))*(.25+pow(saturate(cos(a*3.-Age*18.)),7.));
float bolt=0.;
float beatClock=floor(Age*15.);
for(int j=0;j<3;j++) {
 float seed=float(j)*2.094+sin(beatClock*4.13+float(j)*8.21)*.24;
 float jag=sin(r*35.+seed*7.+beatClock*1.7)*.11+sin(r*72.-seed*3.)*.055;
 float delta=sin(a-seed-r*3.0-Age*1.35+jag);
 float boltCore=exp(-pow(delta/max(.016,aa*.35),2.));
 float branch=exp(-pow(sin(a-seed-r*4.4-Age*1.35-jag*.8)/max(.012,aa*.30),2.))*smoothstep(.32,.50,r);
 float flicker=pow(saturate(sin(Age*31.+float(j)*2.7)),3.);
 bolt+=(boltCore+branch*.46)*stormMask*(.12+flicker*.88);
}
float afterglow=pow(saturate(cos(stormPhase-.45)),3.)*stormMask*(.20+stormField*.35);
float toothFlash=pow(saturate(cos(a*10.-Age*8.)),16.)*mask*(.20+stormDetail*.50);
float bladeFace=pow(bladeTip,.65)*smoothstep(.61,.73,r)*(1.-smoothstep(tipRadius-.025,tipRadius+.005,r));
float chamfer=exp(-pow((r-(tipRadius-.045))/(.010+aa*.24),2.))*smoothstep(.62,.72,r)*pow(bladeTip,.8);

rgb=rgb*.72+float3(1.65,.67,.10)*(stormFace*1.85+afterglow*.65)+float3(2.7,1.4,.28)*(innerTurn*.90+nearEye*.55)+white*(stormCrest*.24+bolt*.31+toothFlash*.30+chamfer*.34)+warm*bladeFace*.48;
alpha=saturate(alpha+stormFace*.72+afterglow*.17+innerTurn*.31+nearEye*.21+stormCrest*.20+bolt*.30+bladeFace*.35+chamfer*.32);
'''


def author(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    content = Path(unreal.Paths.project_content_dir()).resolve()
    protected = [content/'TopDown/Characters/Sparrow/Materials'/name for name in
                 ('M_SparrowGearFeather.uasset', 'M_SparrowAscensionGold.uasset')]
    protected += [path for path in (content/'TopDown/Characters/Sparrow/Materials/Arsenal20261026').glob('M_SparrowSawVortex*.uasset')]
    normal_rim = content/'TopDown/Characters/Sparrow/Materials/Arsenal20261026/M_SparrowSawGearRim.uasset'
    if normal_rim.exists(): protected.append(normal_rim)
    hashes = lambda: {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    before = hashes()
    texture = unreal.load_asset(FLOW)
    assert texture, FLOW
    form_texture = unreal.load_asset(FORM_FLOW)
    assert form_texture, FORM_FLOW
    lib = unreal.MaterialEditingLibrary
    rows = []
    definitions = [(ROOT+'/M_SparrowSawVortex', BODY), (ROOT+'/M_SparrowSawVortexRim', RIM),
                   (FORM_ROOT+'/M_SparrowSawVortexAscended', ASCENDED_BODY),
                   (FORM_ROOT+'/M_SparrowSawVortexRimAscended', ASCENDED_RIM),
                   (ROOT+'/M_SparrowSawGearRim', GEAR_RIM),
                   (FORM_ROOT+'/M_SparrowSawGearRimAscended', ASCENDED_GEAR_RIM)]
    for path, shader_body in definitions:
        gear = 'SawGearRim' in path
        ending = END.replace('smoothstep(.0,.09,Age)*frame;', 'smoothstep(.0,.09,Age)*frame*Envelope;') if gear else END
        code = COMMON+shader_body+ending
        form_gear = path == FORM_ROOT+'/M_SparrowSawGearRimAscended'
        digest = hashlib.sha256((code+(FORM_FLOW if form_gear else '')).encode()).hexdigest()
        material = unreal.load_asset(path)
        reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'SawVortexHash') == digest)
        if not reused:
            if material is None:
                folder, name = path.rsplit('/', 1)
                material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
            assert material, path
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided', True)

            def node(kind, **props):
                obj = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
                for key, value in props.items():
                    obj.set_editor_property(key, value)
                return obj

            shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=form_texture if form_gear else texture)}
            for param, default in (('Age', 0.), ('Index', 0.), ('Pulse', 0.), ('Envelope', 1.)):
                sources[param] = node('ScalarParameter', parameter_name=param, default_value=default)
            pins = []
            for name in sources:
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', name)
                pins.append(pin)
            shader.set_editor_property('inputs', pins)
            for name, source in sources.items():
                assert lib.connect_material_expressions(source, '', shader, name)
            for prop, rgba in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
                mask = node('ComponentMask', r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3])
                assert lib.connect_material_expressions(shader, '', mask, '')
                assert lib.connect_material_property(mask, '', prop)
            lib.recompile_material(material)
            unreal.EditorAssetLibrary.set_metadata_tag(material, 'SawVortexHash', digest)
            assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), path
        rows.append({'path': path, 'hash': digest, 'reused': reused})
    assert before == hashes(), 'The original A gear materials changed'
    result = {'passed': True, 'materials': rows, 'original_gear_materials_unchanged': True,
              'native_surfaces': {'normal': 2, 'ascended': 2}, 'separate_shell_surfaces': 0,
              'damage_collision_changed': False,
              'visual_acceptance': 'pending actual PIE quarter-view review'}
    (out/'saw-vortex-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
