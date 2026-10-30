"""A1 candidate: a small convecting sun, uneven prominences and trailing fire.

Only owned SunArrow20261027 materials/meshes are saved.  Style 0 remains the
restored native saw.  The projectile, damage, speed and collision are unchanged.
Run author(output) in the existing serialized UE authoring session.
"""
import hashlib
import json
import math
from pathlib import Path
import runpy

import unreal


ROOT = '/Game/TopDown/Characters/Sparrow/Materials/SunArrow20261027'
MESH_ROOT = '/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027'
FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_PerlinPlasma_Noisey_Packed'
ART = '/Game/TopDown/Characters/Sparrow/FX/FDesign20261027/T_FDesignGoldenFlow'
VERSION = '1'

# This source is sRGB.  Its visual grayscale is a density, not linear light:
# median R .267 becomes .058 after sampling.  Decode only this data channel;
# do not change the shared source texture or gamma-correct the final emission.
DENSITY = r'''
struct FSunDensity {
 float Read(float value) {
  float v=saturate(value);
  return v<=.0031308 ? v*12.92 : 1.055*pow(v,1./2.4)-.055;
 }
};
FSunDensity Density;
'''

CORE = DENSITY + r'''
// Volumetric warped cells carry the luminous area. A bright iso-contour alone
// turns into a neon ring at the gameplay camera's small projected size.
struct FSunCells {
 float Hash(float3 p) { return frac(sin(dot(p,float3(127.1,311.7,74.7)))*43758.5453); }
 float Noise(float3 p) {
  float3 i=floor(p),f=frac(p); f=f*f*(3.-2.*f);
  return lerp(lerp(lerp(Hash(i),Hash(i+float3(1,0,0)),f.x),
                   lerp(Hash(i+float3(0,1,0)),Hash(i+float3(1,1,0)),f.x),f.y),
              lerp(lerp(Hash(i+float3(0,0,1)),Hash(i+float3(1,0,1)),f.x),
                   lerp(Hash(i+float3(0,1,1)),Hash(i+float3(1,1,1)),f.x),f.y),f.z);
 }
 float Cells(float3 p) { return Noise(p)*.56+Noise(p*2.13+5.7)*.28+Noise(p*4.37+11.4)*.16; }
};
FSunCells Cells;
float3 sphere=normalize(Normal);
float3 p=sphere*3.7+float3(Age*.14,-Age*.11,Age*.08);
float3 warp=float3(Cells.Noise(p*.71+4.1),Cells.Noise(p*.83+8.3),Cells.Noise(p*.79+14.7))-.5;
p+=warp*.85;
float raw=Density.Read(Texture2DSample(Flow,FlowSampler,UV*float2(2.,1.)+float2(Age*.021,-Age*.012)).r);
float thermal=saturate(Cells.Cells(p)+(raw-.3)*.09);
float heat=smoothstep(.31,.66,thermal);
float hot=smoothstep(.56,.73,thermal);
float brokenVein=exp(-pow((thermal-.555)/.040,2.))*smoothstep(.36,.68,Cells.Noise(p*1.7+17.));
float illumination=.58+.42*saturate(dot(sphere,normalize(float3(.30,-.45,.8)))*.5+.5);
float3 darkAmber=float3(.12,.025,.0035), molten=float3(2.1,.71,.085);
float3 gold=float3(3.2,1.8,.51), ivory=float3(4.6,3.6,1.6);
float3 rgb=lerp(darkAmber,molten,pow(heat,1.25))*illumination;
rgb+=gold*brokenVein*.23+ivory*hot*.38;
float facing=saturate(abs(dot(sphere,normalize(ViewDirection))));
float brokenLimb=pow(1.-facing,5.)*smoothstep(.36,.64,thermal);
rgb+=gold*brokenLimb*.12;
if(Style>1.5) rgb*=.78+.22*heat;
return float4(rgb*(1.+Pulse*.24+Ascended*.06),1.);
'''

CORE_WPO = DENSITY + r'''
float n=Density.Read(Texture2DSampleLevel(Flow,FlowSampler,UV+float2(Age*.017,-Age*.012),0).r);
return normalize(Normal)*((n-.30)*1.6+sin(UV.x*12.56637+Age*1.5)*.18);
'''

CORONA = DENSITY + r'''
float u=saturate(UV.x), v=UV.y-.5;
float n=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*1.7-Age*.41+Index*.19,UV.y*.9+Age*.05)).r);
float fine=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*4.1-Age*.91,UV.y*1.9+Index*.27)).g);
float curl=sin(u*11.-Age*3.1+Index)*(.025+u*.07)+(n-.3)*.12;
float end=smoothstep(.0,.055,u)*(1.-smoothstep(.78,1.,u));
float tissue=exp(-pow((v-curl)/.34,2.))*(.34+n*.66);
float ridge=exp(-pow((v-curl-.11)/.070,2.))*smoothstep(.25,.52,fine);
float split=exp(-pow((v-curl+.17*sin(u*8.+Index))/.085,2.))*smoothstep(.27,.55,n);
float breathing=.63+.37*saturate(sin(Age*3.7+Index*2.4-u*6.));
float packet=smoothstep(.10,.43,n+.19*sin(u*16.-Age*7.3+Index));
float opacity=saturate(tissue*.92*packet+ridge*.44+split*.25)*end*breathing;
// Color and coverage are separate: multiplying the soft body twice previously
// left just the narrow bright strand visible after translucent composition.
float3 rgb=float3(2.3,.77,.10)*(.62+n*.38)+float3(4.1,2.7,.84)*(ridge*.35+split*.22);
rgb*=1.+Pulse*.24+Ascended*.10;
return float4(rgb,opacity*smoothstep(.0,.10,Age));
'''

ORBIT = CORONA.replace('float tissue=exp(-pow((v-curl)/.34,2.))*(.34+n*.66);',
    'float tissue=exp(-pow((v-curl)/.38,2.))*(.42+n*.58);').replace(
    'float breathing=.63+.37*saturate(sin(Age*3.7+Index*2.4-u*6.));',
    'float breathing=.78+.22*saturate(sin(Age*3.7+Index*2.4-u*6.));')

TAIL = DENSITY + r'''
float u=saturate(UV.x), v=UV.y-.5;
float n=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*1.5-Age*.40+Index*.23,UV.y*.65+Age*.06)).r);
float detail=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*4.-Age*.84,UV.y*1.1+Index*.29)).g);
float bend=(n-.30)*.25+sin(u*21.-Age*4.1+Index)*.025;
float endFade=(1.-smoothstep(.72,1.,u))*smoothstep(.0,.045,u);
float front=frac(u*2.3-Age*.62+Index*.197);
float packet=smoothstep(.02,.13,front)*(1.-smoothstep(.72,.96,front));
float width=.035+.32*pow(1.-front,.72);
float body=exp(-pow((v-bend)/width,2.))*(.12+n*.78)*(.12+packet*.88);
float seam=exp(-pow((v-bend)/.038,2.))*smoothstep(.19,.49,detail)*packet;
float curl=exp(-pow((v-bend-.14*sin(u*9.+Index))/.065,2.))*smoothstep(.25,.55,n)*packet*.50;
float knot=pow(saturate(sin(u*14.-Age*6.8+Index*2.3)),12.)*seam;
float3 rgb=float3(2.0,.60,.055)*(.65+n*.35)+float3(4.3,2.1,.36)*(seam*.36+curl*.30)+float3(5.6,3.7,1.1)*knot*.18;
float opacity=saturate(body*.92+seam*.43+curl*.32)*endFade;
return float4(rgb*(1.+Pulse*.36+Ascended*.08),opacity*smoothstep(.03,.18,Age));
'''

AXIS = r'''
float striation=.6+.4*pow(saturate(sin(UV.y*31.+UV.x*4.)),5.);
return float4(float3(3.3,1.65,.38)*striation,1.);
'''

ANNULAR_RING = DENSITY + r'''
// Keep the original central arrow / hollow circular envelope relationship.
// Angular motion lives in the material; no opaque sphere fills the opening.
float2 p=(UV-.5)*2.;
float radius=length(p),angle=atan2(p.y,p.x)/6.2831853+.5;
float radial=saturate((radius-.29)/.67);
float angular=angle-Age*(.21+Index*.035)+Index*.31;
float4 art=Texture2DSample(Art,ArtSampler,float2(angular*2.,radial));
float n=Density.Read(Texture2DSample(Flow,FlowSampler,float2(angle*3.+Age*.19,radius*1.8-Index*.13)).r);
float fine=Density.Read(Texture2DSample(Flow,FlowSampler,float2(angle*7.-Age*.42,radius*3.1)).g);
float light=dot(art.rgb,float3(.30,.59,.11));
float hot=smoothstep(.30,.74,light);
float inner=smoothstep(.29,.40,radius);
float raggedEdge=.89+(n-.31)*.16;
float outer=1.-smoothstep(raggedEdge-.08,raggedEdge+.025,radius);
float veinRadius=.62+(n-.31)*.19+sin(angle*18.8496-Age*3.)*.035;
float vein=exp(-pow((radius-veinRadius)/.026,2.))*smoothstep(.18,.43,fine);
float filament=exp(-pow((radius-(.77+sin(angle*31.416+Age*2.)*.018))/.012,2.))*smoothstep(.22,.48,n);
float body=art.a*(.30+pow(saturate(light*2.),.65)*.69)*inner*outer;
float alpha=saturate(body+vein*.43+filament*.31)*inner*outer;
float3 rgb=lerp(float3(.52,.14,.012),float3(2.7,1.19,.14),pow(saturate(light*1.8),.65));
rgb+=float3(3.4,2.65,1.0)*(hot*.40+vein*.32+filament*.23);
return float4(rgb*(1.+Ascended*.14+Pulse*.12),alpha*smoothstep(.015,.10,Age));
'''

ANNULAR_AXIS = r'''
float side=saturate(dot(normalize(Normal),normalize(float3(.30,-.45,.82)))*.5+.5);
float seam=pow(saturate(cos(UV.y*12.56637)),12.);
float pulse=exp(-pow((UV.x-frac(Age*.75))/.09,2.));
float3 rgb=lerp(float3(.45,.15,.025),float3(2.0,1.17,.30),side);
rgb+=float3(2.9,2.2,1.0)*(seam*.26+pulse*.10);
return float4(rgb,1.);
'''


SOLAR_CRESCENT = DENSITY + r'''
float u=saturate(UV.x),v=saturate(UV.y);
float raw=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*2.-Age*.35,v*1.2+Index*.19)).r);
float fine=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*6.+Age*.8,v*3.)).g);
float side=saturate(dot(normalize(Normal),normalize(float3(.55,-.24,.8)))*.5+.5);
float edge=pow(abs(v-.5)*2.,10.);
float hot=exp(-pow((v-.83)/.024,2.));
float channel=exp(-pow((v-.44-.09*sin(u*19.-Age*3.)-.08*(raw-.4))/.033,2.))*smoothstep(.25,.49,raw);
float fractures=exp(-pow((raw-.37)/.028,2.))*smoothstep(.24,.45,fine);
float cavity=smoothstep(.22,.49,raw);
float3 rgb=lerp(float3(.025,.012,.003),float3(.57,.25,.035),side)*(.45+cavity*.55);
rgb+=float3(2.3,1.43,.37)*(edge*.45+channel*.54+fractures*.27)+float3(3.6,3.0,1.6)*hot*.48;
float coverage=.69+.29*cavity;
return float4(rgb*(1.+Pulse*.40+Ascended*.08),coverage*smoothstep(0.,.09,Age));
'''

SOLAR_WAKE = DENSITY + r'''
float u=saturate(UV.x),v=UV.y-.5;
float raw=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*1.9-Age*.55+Index*.31,UV.y*1.4)).r);
float detail=Density.Read(Texture2DSample(Flow,FlowSampler,float2(u*5.-Age*1.3,UV.y*3.+Index*.4)).g);
float4 art=Texture2DSample(Art,ArtSampler,float2(u*1.1-Age*.68,UV.y));
float light=pow(saturate(dot(art.rgb,float3(.3,.59,.11))*2.2),.60);
float bend=(raw-.3)*.19+sin(u*17.-Age*4.+Index)*.055;
float body=exp(-pow((v-bend)/.34,2.))*smoothstep(.10,.39,raw+light*.16);
float vein=exp(-pow((v-bend-.11)/.045,2.))*smoothstep(.18,.45,detail);
float end=smoothstep(.0,.04,u)*(1.-smoothstep(.70,1.,u))*(1.-smoothstep(.30,.5,abs(v)));
float3 rgb=lerp(float3(.72,.18,.013),float3(2.7,1.02,.12),light)+float3(3.6,2.75,1.)*vein*.35;
return float4(rgb*(1.+Pulse*.45+Ascended*.12),saturate(body*(.30+art.a*.45)+vein*.38)*end*smoothstep(.01,.12,Age));
'''


ANNULAR_CRAFT_RING = DENSITY + r'''
float2 p=(UV-.5)*2.;
float radius=length(p),angle=atan2(p.y,p.x)/6.2831853+.5;
float spin=angle-Age*(.16+Index*.055);
float radial=saturate((radius-.47)/.49);
float n=Density.Read(Texture2DSample(Flow,FlowSampler,float2(spin*3.,radius*1.7+Age*.12)).r);
float fine=Density.Read(Texture2DSample(Flow,FlowSampler,float2(spin*8.+Age*.14,radius*4.)).g);
float4 art=Texture2DSample(Art,ArtSampler,float2(spin*2.,radial));
float light=pow(saturate(dot(art.rgb,float3(.3,.59,.11))*1.9),.72);
float aperture=smoothstep(.45,.54,radius);
float outer=1.-smoothstep(.91+(n-.3)*.04,.99,radius);
float membrane=(.25+light*.55)*(.45+art.a*.55)*aperture*outer;
float crease=exp(-pow((radius-(.68+(n-.3)*.12))/.042,2.))*smoothstep(.20,.43,fine);
float cuttingEdge=exp(-pow((radius-(.904+(n-.3)*.035))/.017,2.));
float fold=pow(saturate(.5+.5*cos(angle*50.2655-radius*9.-Age*4.)),10.)*smoothstep(.24,.47,n);
float surge=pow(saturate(.5+.5*sin(spin*18.8496+radius*5.)),14.);
float3 rgb=lerp(float3(.22,.058,.008),float3(1.36,.55,.072),light);
rgb+=float3(2.35,1.72,.69)*(cuttingEdge*.38+crease*.25+fold*.11+surge*.12);
rgb+=float3(2.20,1.24,.25)*Ascended*(crease*.13+fold*.18);
float coverage=saturate(membrane+cuttingEdge*.40+crease*.22)*aperture*outer;
return float4(rgb*(1.+Pulse*.16),coverage*Envelope*smoothstep(.015,.11,Age)*(Index<.5 ? 1. : .72));
'''

ANNULAR_CRAFT_CUFF = DENSITY + r'''
// Circumferential U, front-to-back V. This is an open physical sleeve behind
// the existing annulus; the axis is never filled by a sphere or opaque disk.
float angle=UV.x,depth=UV.y;
float travel=angle+Age*.25;
float n=Density.Read(Texture2DSample(Flow,FlowSampler,float2(travel*2.,depth*1.1-Age*.18)).r);
float detail=Density.Read(Texture2DSample(Flow,FlowSampler,float2(travel*7.,depth*3.+Age*.26)).g);
float4 art=Texture2DSample(Art,ArtSampler,float2(travel*2.,depth));
float light=pow(saturate(dot(art.rgb,float3(.3,.59,.11))*1.85),.72);
float longFlow=exp(-pow((depth-(.48+sin(angle*18.8496-Age*2.)*.13+(n-.3)*.16))/.12,2.));
float rib=pow(saturate(.5+.5*cos(angle*75.398-depth*7.+Age*4.)),14.)*smoothstep(.19,.45,detail);
float rim=exp(-pow(depth/.10,2.));
float breakUp=smoothstep(.10,.34,n+light*.16);
float fade=(1.-smoothstep(.75,1.,depth))*smoothstep(.0,.045,depth);
float coverage=(art.a*(.16+light*.26)*breakUp+longFlow*.18+rib*.12)*fade;
float3 rgb=lerp(float3(.19,.052,.008),float3(1.20,.46,.055),light);
rgb+=float3(2.12,1.48,.55)*(longFlow*.22+rib*.16+rim*.10);
rgb+=float3(2.0,1.10,.24)*Ascended*longFlow*.14;
return float4(rgb*(1.+Pulse*.18),saturate(coverage)*Envelope*smoothstep(.02,.14,Age));
'''


def _material(name, code, texture, opaque=False, wpo=None):
    path = ROOT+'/'+name
    digest = hashlib.sha256((VERSION+code+str(wpo)+str(opaque)+FLOW+(ART if 'ArtSampler' in code else '')).encode()).hexdigest()
    mat = unreal.load_asset(path)
    if mat and unreal.EditorAssetLibrary.get_metadata_tag(mat, 'SunArrowHash') == digest:
        return mat, {'path': path, 'hash': digest, 'reused': True}
    if mat is None:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    assert mat, path
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE if opaque else unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', not opaque)

    def node(kind, **props):
        result = lib.create_material_expression(mat, getattr(unreal, 'MaterialExpression'+kind))
        for key, value in props.items():
            result.set_editor_property(key, value)
        return result

    sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture),
               'Normal': node('PixelNormalWS'), 'ViewDirection': node('CameraVectorWS')}
    if 'ArtSampler' in code:
        art=unreal.load_asset(ART);assert art,ART
        sources['Art']=node('TextureObject',texture=art)
    for key, default in (('Age', 0.), ('Index', 0.), ('Pulse', 0.), ('Ascended', 0.), ('Style', 1.), ('Envelope', 1.)):
        sources[key] = node('ScalarParameter', parameter_name=key, default_value=default)

    def custom(text, kind, names, overrides=None):
        result = node('Custom', code=text, output_type=kind)
        pins = []
        for key in names:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', key)
            pins.append(pin)
        result.set_editor_property('inputs', pins)
        for key in names:
            source = (overrides or {}).get(key, sources[key])
            assert lib.connect_material_expressions(source, '', result, key), (name, key)
        return result

    shader = custom(code, unreal.CustomMaterialOutputType.CMOT_FLOAT4, tuple(sources))
    rgb = node('ComponentMask', r=True, g=True, b=True, a=False)
    assert lib.connect_material_expressions(shader, '', rgb, '')
    assert lib.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if not opaque:
        alpha = node('ComponentMask', r=False, g=False, b=False, a=True)
        assert lib.connect_material_expressions(shader, '', alpha, '')
        assert lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    if wpo:
        motion = custom(wpo, unreal.CustomMaterialOutputType.CMOT_FLOAT3, ('UV', 'Flow', 'Age', 'Normal'),
                        {'Normal': node('VertexNormalWS')})
        assert lib.connect_material_property(motion, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.set_metadata_tag(mat, 'SunArrowHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat, False), path
    return mat, {'path': path, 'hash': digest, 'reused': False}


def _normalize(v):
    length = math.sqrt(sum(c*c for c in v))
    return tuple(c/max(length, 1.e-8) for c in v)


def _cross(a, b):
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def _ribbon_geometry(kind):
    """Two crossed curved strips: volume survives both side and quarter views."""
    segments = 36
    vertices, uvs, faces = [], [], []

    if kind == 'annular_craft_cuff':
        segments=96;slices=8
        for i in range(segments+1):
            u=i/segments;angle=u*math.tau
            for j in range(slices+1):
                v=j/slices
                radius=72.-23.*v+math.sin(v*math.pi)*4.
                x=-42.*v+math.sin(v*math.pi)*3.
                vertices.append((x,math.cos(angle)*radius,math.sin(angle)*radius))
                # The shared FBX OBJ importer flips V. This new material uses
                # directional depth, so preserve front=0 and rear=1 explicitly.
                uvs.append((u,1.-v))
        for i in range(segments):
            for j in range(slices):
                a=i*(slices+1)+j+1;b=a+slices+1
                faces.extend(((a,a+1,b+1),(a,b+1,b)))
        return vertices,uvs,faces,segments

    if kind == 'solar_crescent':
        # A true faceted airfoil, tapered in length and curved around the real
        # projectile axis. Three instances create interrupted cutting surfaces.
        segments=112; sides=8
        for i in range(segments+1):
            u=i/segments;angle=-.62+u*1.92
            radius=62.+8.*math.sin(u*math.pi)
            width=(1.0+18.*math.sin(u*math.pi)**.75)*(1.-u*.34)
            phase=(u*7.)%1.
            tooth=max(0.,1.-abs((phase-.24)/.24))*17.*math.sin(u*math.pi)**.6
            for j in range(sides):
                v=j/sides;a=v*math.tau
                radial=radius+math.cos(a)*width+max(0.,math.cos(a))*tooth
                depth=math.sin(a)*4.*math.sin(u*math.pi)
                vertices.append((16.*math.sin(u*math.pi*1.3)+depth,math.cos(angle)*radial,math.sin(angle)*radial))
                uvs.append((u,v))
        for i in range(segments):
            for j in range(sides):
                a=i*sides+j+1;b=i*sides+(j+1)%sides+1
                faces.extend(((a,b,b+sides),(a,b+sides,a+sides)))
        return vertices,uvs,faces,segments

    def center(t):
        if kind == 'solar_wake':
            angle=-.62+t*2.30
            radius=66.+t*13.
            return -t*150.+8.*math.sin(t*math.pi),math.cos(angle)*radius,math.sin(angle)*radius
        if kind == 'prominence':
            angle = -.35+1.05*t
            radius = 40.+45.*math.sin(t*math.pi*.60)
            return -20.*t+math.sin(t*math.pi)*6., math.cos(angle)*radius, math.sin(angle)*radius
        if kind == 'orbit':
            angle = -1.30+2.10*t
            radius = 57.+16.*math.sin(t*math.pi)
            return math.sin(t*math.pi*2.)*9., math.cos(angle)*radius, math.sin(angle)*radius
        angle = .26+t*2.35+math.sin(t*9.)*.16
        radius = 33.+t*29.+math.sin(t*math.pi)*7.
        return -t*180., math.cos(angle)*radius, math.sin(angle)*radius

    for crossed in range(2):
        base = len(vertices)
        for step in range(segments+1):
            t = step/segments
            point = center(t)
            before, after = center(max(0., t-.001)), center(min(1., t+.001))
            tangent = _normalize(tuple(b-a for a, b in zip(before, after)))
            axis = (1., 0., 0.) if kind in ('prominence','orbit','solar_wake') else (0., 0., 1.)
            side = _normalize(_cross(tangent, axis))
            if crossed:
                side = _normalize(_cross(tangent, side))
            if kind=='prominence': width=16.*max(.025,math.sin(math.pi*t)**.65)*(1.-t*.45)
            elif kind=='orbit': width=18.*max(.02,math.sin(math.pi*t)**.75)
            elif kind=='solar_wake': width=22.*math.sin(t*math.pi)**.65+.1
            else: width=12.*(1.-t*.88)
            for across in range(5):
                s = across/4.
                vertices.append(tuple(point[i]+side[i]*(s-.5)*width*2. for i in range(3)))
                uvs.append((t, s))
        for step in range(segments):
            for across in range(4):
                a = base+step*5+across+1
                faces.extend(((a, a+1, a+6), (a, a+6, a+5)))
    return vertices, uvs, faces, segments


def _mesh(output, material, name, kind):
    path = MESH_ROOT+'/'+name
    vertices, uvs, faces, segments = _ribbon_geometry(kind)
    digest = hashlib.sha256(repr((vertices, uvs, faces)).encode()).hexdigest()
    mesh = unreal.load_asset(path)
    if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'SunArrowMesh') == digest:
        return {'path': path, 'reused': True, 'triangles': mesh.get_num_triangles(0)}
    size = [max(v[a] for v in vertices)-min(v[a] for v in vertices) for a in range(3)]
    bounds = (size[0], size[1]-.1, size[1]+.1, size[2]-.1, size[2]+.1)
    importer = runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    result = importer(output, material, path, vertices, uvs, faces, 'SunArrowMesh', digest, bounds, len(faces)-4, segments)
    # The OBJ is an exact, owned import intermediate.  Retain the actual uasset
    # and import report, without accumulating disposable source duplicates.
    source = Path(result['source_obj']).resolve()
    assert source.parent == output.resolve() and source.name == name+'.obj'
    source.unlink()
    result['source_obj_removed'] = True
    return result


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    texture = unreal.load_asset(FLOW)
    assert texture, FLOW
    core, core_row = _material('M_SparrowSunCore', CORE, texture, True, CORE_WPO)
    corona, corona_row = _material('M_SparrowSunCorona', CORONA, texture)
    orbit, orbit_row = _material('M_SparrowSunOrbit', ORBIT, texture)
    tail, tail_row = _material('M_SparrowSunTail', TAIL, texture)
    axis, axis_row = _material('M_SparrowSunAxis', AXIS, texture, True)
    annular, annular_row = _material('M_SparrowAnnularRing', ANNULAR_RING, texture)
    annular_axis, annular_axis_row = _material('M_SparrowAnnularAxis', ANNULAR_AXIS, texture, True)
    solar_blade, solar_blade_row = _material('M_SolarCrescent', SOLAR_CRESCENT, texture)
    solar_wake, solar_wake_row = _material('M_SolarWake', SOLAR_WAKE, texture)
    craft_ring, craft_ring_row = _material('M_AnnularCraftRing', ANNULAR_CRAFT_RING, texture)
    craft_cuff, craft_cuff_row = _material('M_AnnularCraftCuff', ANNULAR_CRAFT_CUFF, texture)
    sphere = unreal.load_asset('/Engine/BasicShapes/Sphere')
    assert isinstance(sphere, unreal.StaticMesh), 'Engine sphere is required'
    box = sphere.get_bounding_box()
    extent = box.max-box.min
    assert all(95. < value < 105. for value in (extent.x, extent.y, extent.z)), str(extent)
    meshes = [_mesh(output, corona, 'SM_SparrowSunProminence', 'prominence'),
              _mesh(output, orbit, 'SM_SparrowSunOrbit', 'orbit'),
              _mesh(output, tail, 'SM_SparrowSunTail', 'tail'),
              _mesh(output, solar_blade, 'SM_SolarCrescent', 'solar_crescent'),
              _mesh(output, solar_wake, 'SM_SolarWake', 'solar_wake'),
              _mesh(output, craft_cuff, 'SM_AnnularCraftCuff', 'annular_craft_cuff')]
    cuff_mesh = unreal.load_asset(MESH_ROOT+'/SM_AnnularCraftCuff')
    positions,indices,normals,uvs,tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(cuff_mesh,0,0)
    front_v = [uv.y for point,uv in zip(positions,uvs) if abs(point.x)<.01]
    rear_v = [uv.y for point,uv in zip(positions,uvs) if abs(point.x+42.)<.01]
    cuff_uv_audit = {'front_vertices':len(front_v),'rear_vertices':len(rear_v),
                    'front_v':sum(front_v)/max(1,len(front_v)),'rear_v':sum(rear_v)/max(1,len(rear_v))}
    cuff_uv_audit['passed'] = bool(front_v and rear_v and abs(cuff_uv_audit['front_v'])<.01 and abs(cuff_uv_audit['rear_v']-1.)<.01)
    assert cuff_uv_audit['passed'], 'A5 imported depth UV was flipped: '+json.dumps(cuff_uv_audit)
    result = {'passed': True, 'materials': [core_row, corona_row, orbit_row, tail_row, axis_row, annular_row, annular_axis_row, solar_blade_row, solar_wake_row, craft_ring_row, craft_cuff_row], 'meshes': meshes,
              'cuff_uv_audit':cuff_uv_audit,
              'cvar': {'name': 'Sparrow.SunArrow.Style', 'default': 4, 'candidates': [1,2,3,4,5]},
              'annular_craft_candidate': {'style':5,'a3_arrow_and_ring_scale_preserved':True,'original_ring_diameters_cm':[160.,108.],
                                        'central_sphere':False,'detached_cutting_claws':False,'sleeve_depth_cm':42.,
                                        'sleeve_front_rear_radius_cm':[72.,49.], 'description':'one open textured energy sleeve following the original central arrow and annular silhouette'},
              'solar_rotor_candidate': {'style':4,'real_faceted_airfoils':3,'curved_plasma_wakes':3,'ascended_counterrotor':True,'central_real_arrow':True},
              'annular_candidate': {'style':3,'central_real_arrow':True,'sphere':False,'original_ring_diameters_cm':[160.,108.],
                                    'description':'hollow annular flow surrounding the original central arrow, with fragmented gold-white veins'},
              'normal': {'core_diameter_cm': 85., 'prominences': 5, 'tails': 4},
              'form': {'core_diameter_cm': 90., 'prominences': 7, 'tails': 6},
              'source_texture_srgb': texture.get_editor_property('srgb'),
              'gameplay_changed': False, 'visual_acceptance': 'pending actual game capture'}
    (output/'sun-arrow-author.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
