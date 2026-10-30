"""Preview-only D studies; earlier candidates remain available for comparison.

D6 faithfully combines precision rails and segmented wind; D7 compresses wind
around the actual projectile head; D8 opens four torn wind blades at release.
D9 leaves seven light feathers at fixed positions after the real arrow passes.
The operating D, its source materials, arrow, collision, damage and animation
are untouched. Only this script's Previews/DCombined20261024 materials save.
The integrating parent owns shader compilation, GPU execution and video review.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


WRS = runpy.run_path(str(Path(__file__).with_name('sparrow_wrs_tempest_studies.py')))
BASE = WRS['BASE']
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/DCombined20261024'
OPTIONS = ('D6', 'D7', 'D8', 'D9')
DESIGNS = {
    'D6': {'label': '저격선 · 분절 바람창',
           'shape': '가는 황금 저격 레일과 눈금이 먼저 정렬되고, 한 발이 통과한 뒤 질감이 흐르는 짧은 바람 조각들이 차례로 남음',
           'timing': '현재 D의 준비·발사 시점 유지, 이전 D5와 같은 0.40초 분절 잔상',
           'intent': 'D4 백금 저격선과 D5 분절 바람창의 충실한 결합'},
    'D7': {'label': '압축 나선 관통',
           'shape': '두 가는 레일 안에서 흰 핵과 반투명 금빛 바람이 좁아지고, 실제 D 화살 머리를 따라 짧은 축방향 회오리가 관통',
           'timing': '준비 중 응축, 실제 화살 위치를 추적하는 짧은 꼬임과 국소 접촉 파열',
           'intent': '집중된 전방 압력과 저격의 관통감 강조'},
    'D8': {'label': '사풍 파열',
           'shape': '발사 순간 네 개의 찢어진 반투명 바람날이 벌어졌다 전방으로 닫히고, 가는 원래 D 한 발과 짧은 파편만 남음',
           'timing': '실제 발사 직후 0.05초에 펼침 정점, 전방으로 닫히며 약 0.26초에 소멸',
           'intent': '준비보다 발사 순간의 강한 분리·파열 강조'},
    'D9': {'label': '통과 후 깃 잔광',
           'shape': '실제 화살이 지나간 고정 경로에 가벼운 황금·흰 깃 7개가 차례로 피어나고, 조금씩 옆으로 흩어져 사라짐',
           'timing': '각 지점을 통과한 뒤 0.035~0.055초 지연, 깃마다 0.50~0.60초 안에 소멸',
           'intent': '준비 장식이나 화살을 쫓는 꼬리 없이 지나간 자리에만 남는 깃 효과'},
}

SHADER = r'''
struct FShape {
    float Seg(float2 p,float2 a,float2 b) {
        float2 d=b-a;return length(p-a-d*saturate(dot(p-a,d)/max(dot(d,d),.001)));
    }
    float2 Curve(float2 a,float2 b,float2 c,float2 d,float t) {
        float u=1.-t;return u*u*u*a+3.*u*u*t*b+3.*u*t*t*c+t*t*t*d;
    }
    float Edge(float2 p,float2 a,float2 b,float2 c,float2 d,float width) {
        float edge=10000.;
        for(int j=0;j<18;j++) {
            float t=j/18.,n=(j+1)/18.;
            edge=min(edge,Seg(p,Curve(a,b,c,d,t),Curve(a,b,c,d,n))
                     -width*pow(max(sin(n*3.14159265),.001),.70));
        }
        return edge;
    }
    float Beam(float2 p,float2 a,float2 b,float width) {
        return exp(-Seg(p,a,b)/max(width,.2));
    }
};
FShape S;
const int Mode=DESIGN_NUMBER;
const float PI=3.14159265;
float2 p=ContactMode>.5?(UV-.5)*250.:(UV-.5)*float2(1250.,540.)+float2(430.,0.);
float rails=0.,wind=0.,white=0.,flecks=0.;
float shot=ShotAge<0.?-1.:max(Age-ShotAge,0.);
float ready=smoothstep(.015,.28,Age);

if(Mode==9) {
    // D9 has no charge, rail, contact burst, or projectile-attached tail.
    // Both the anchor and every visible pixel must already be behind the
    // actual native head. Each anchor's clock starts after its passage.
    if(ContactMode>.5||shot<0.||p.x>HeadDistance)return float4(0.,0.,0.,0.);
    float featherFace=0.,featherShaft=0.,featherBarbs=0.;
    for(int j=0;j<7;j++) {
        float anchor=110.+j*120.;
        float delay=.035+(j%3)*.010;
        float t=shot-anchor/max(FlightSpeed,1.)-delay;
        float life=.50+(j%3)*.05;
        if(HeadDistance<anchor||t<0.||t>life)continue;
        float seed=frac(sin(j*23.71+4.13)*9271.37),side=j%2==0?1.:-1.;
        float rise=smoothstep(0.,.09,t);
        float fade=1.-smoothstep(.11,life,t);
        // Drift is only a few centimetres around the stationary path anchor.
        float2 center=float2(anchor+side*t*9.,side*(5.+rise*8.+t*29.));
        float angle=side*(.40+seed*.36+sin(t*7.+seed*2.)*.12);
        float2 axis=float2(cos(angle),sin(angle));
        float2 q=p-center;
        float2 local=float2(dot(q,axis),dot(q,float2(-axis.y,axis.x)));
        float featherLength=58.+seed*15.;
        float u=(local.x+featherLength*.43)/featherLength;
        if(u<0.||u>1.)continue;
        float camber=sin(u*PI)*(2.+seed*3.)+u*u*2.;
        float vane=local.y-camber;
        float width=(8.0+seed*2.6)*pow(max(sin(u*PI),.001),.82);
        width*=vane>0.?1.:.76;
        // Angled barb bands and varying missing tips break the leaf outline.
        float barbPhase=u*15.-abs(vane)/max(width,1.)*.73;
        float barbBand=pow(.5+.5*cos(barbPhase*2.*PI),5.);
        float tipBreak=.55+.45*sin(u*73.+j*5.1)*sin(u*41.+1.7);
        float face=1.-smoothstep(width-1.1,width+1.15,abs(vane)+(1.-tipBreak)*2.4);
        float roots=smoothstep(.035,.12,u)*(1.-smoothstep(.88,1.,u));
        float lifeMask=rise*fade;
        float2 textureUV=float2(u*1.8+seed,local.y*.047-t*.12);
        float grain=Texture2DSample(Wind,WindSampler,textureUV).r;
        float softness=.55+.45*grain;
        featherFace=max(featherFace,face*roots*(.24+.22*barbBand)*softness*lifeMask);
        featherBarbs=max(featherBarbs,face*roots*barbBand*.34*lifeMask);
        float stem=exp(-abs(vane)/.62)*smoothstep(0.,.04,u)*(1.-smoothstep(.90,1.,u));
        featherShaft=max(featherShaft,stem*.62*lifeMask);
    }
    float opacity=min(.72,featherFace+featherBarbs*.42+featherShaft*.70);
    // Color is normalized once: translucency must not square faint coverage.
    float3 featherColor=(float3(1.95,1.48,.65)*featherFace
                        +float3(2.3,2.05,1.43)*(featherBarbs*.42+featherShaft*.70))
                       /max(opacity,.025);
    return float4(min(featherColor,float3(2.8,2.8,2.8)),opacity);
}

float2 flowUV=float2(p.x*.013-Age*1.35,p.y*.026+sin(p.x*.021-Age*8.)*.16);
float cloud=Texture2DSample(Smoke,SmokeSampler,flowUV).r;
float grain=Texture2DSample(Wind,WindSampler,flowUV*float2(.73,1.41)+float2(Age*.27,0)).r;
float density=smoothstep(.035,.68,cloud)*(.78+.22*grain);

if(ContactMode>.5) {
    // Add a local contact, never a screen flash or full shockwave disc.
    float fade=1.-smoothstep(.015,.22,Age),snap=exp(-Age*49.);
    if(Mode==6) {
        white=S.Beam(p,float2(-49.,-2.),float2(38.,2.),1.65)*snap
             +S.Beam(p,float2(-11.,-24.),float2(13.,26.),1.1)*snap;
    } else if(Mode==7) {
        white=S.Beam(p,float2(-65.,0),float2(41.,0),2.0)*snap;
        for(int side=-1;side<=1;side+=2) {
            float2 q=float2(p.x,p.y*side);
            float edge=S.Edge(q,float2(-16.,3.),float2(2.,35.),float2(28.,16.),float2(32.,5.),5.5);
            wind=max(wind,(1.-smoothstep(-2.,3.,edge))*density*fade*.67);
        }
    } else {
        for(int side=-1;side<=1;side+=2) {
            float2 q=float2(p.x,p.y*side);
            float spread=Age*105.;
            white+=S.Beam(q,float2(-20.,-3.+spread),float2(31.,30.+spread),1.55)*snap;
            float edge=S.Edge(q,float2(-31.,-1.+spread),float2(-3.,31.+spread),float2(38.,33.+spread),float2(47.,24.+spread),7.0);
            wind=max(wind,(1.-smoothstep(-2.,3.,edge))*density*fade*.72);
        }
    }
    for(int j=0;j<14;j++) {
        float seed=frac(sin(j*37.4+9.7)*14751.73),a=j*6.2831853/14.;
        float2 d=float2(cos(a),sin(a)*.61);
        float r=8.+Age*(150.+seed*180.);
        flecks+=S.Beam(p,d*r,d*(r+5.+seed*10.),.55)*fade*.34;
    }
    return float4(float3(2.0,1.08,.28)*wind*.65+float3(3.4,2.85,1.65)*white
                  +float3(2.2,1.59,.58)*flecks,saturate(wind*.50+white+flecks));
}

// D6 deliberately retains the exact narrow rail/marker vocabulary of D4.
if(Mode==6) {
    float guide=ready*(shot<0.?1.:exp(-shot*23.));
    float reach=80.+smoothstep(.02,.30,Age)*780.;
    float lead=1.-smoothstep(reach-15.,reach+5.,p.x);
    rails=(S.Beam(p,float2(6.,13.),float2(860.,5.),.65)
          +S.Beam(p,float2(6.,-13.),float2(860.,-5.),.65))*guide*lead;
    for(int j=0;j<7;j++) {
        float x=83.+j*104.,side=j%2==0?1.:-1.;
        float form=smoothstep(.03+j*.025,.11+j*.025,Age);
        rails+=S.Beam(p,float2(x,side*15.),float2(x+6.,side*24.),.70)*form*guide*.75;
    }
    // This is the previous D5 body, scale and timing, not a reduced smoke
    // interpretation of it. D4 rails sit alongside its existing silhouette.
    float body=0.,edgeCore=0.;
    float baseGrain=Texture2DSample(Detail,DetailSampler,UV*float2(5.7,3.1)+float2(-Age*.7,Age*.2)).r;
    float prep=smoothstep(.03,.25,Age)*(shot<0.?1.:exp(-shot*28.));
    for(int side=-1;side<=1;side+=2) {
        float2 q=float2(p.x,p.y*side);
        float edge=S.Edge(q,float2(-23.,63.),float2(24.,70.),float2(63.,34.),float2(79.,0),5.);
        body+=(1.-smoothstep(-.45,1.05,edge))*prep;
        float brightEdge=S.Edge(q,float2(-29.,70.),float2(24.,77.),float2(67.,36.),float2(84.,0),.85);
        edgeCore+=(1.-smoothstep(-.45,1.05,brightEdge))*prep*.7;
    }
    if(shot>=0.) {
        for(int j=0;j<6;j++) {
            float t=shot-j*.018;
            if(t<0.||t>.40)continue;
            float fade=1.-smoothstep(.025,.40,t),x=92.+j*116.,side=j%2==0?1.:-1.;
            float spread=34.+t*90.;
            float2 q=float2(p.x,p.y*side);
            float edge=S.Edge(q,float2(x-42.,spread),float2(x-9.,spread+16.),float2(x+18.,spread*.4),float2(x+31.,-8.),4.2);
            body+=(1.-smoothstep(-.45,1.05,edge))*fade;
            float brightEdge=S.Edge(q,float2(x-49.,spread+7.),float2(x-10.,spread+24.),float2(x+24.,spread*.4),float2(x+39.,-5.),.9);
            edgeCore+=(1.-smoothstep(-.45,1.05,brightEdge))*fade*.8;
            flecks+=S.Beam(q,float2(x-16.,spread+13.),float2(x-32.,spread+22.),.7)*fade;
        }
    }
    return float4(float3(1.7,.83,.12)*body*(.4+baseGrain*.35)
                  +float3(2.3,1.85,.88)*(edgeCore+flecks)+float3(2.4,1.88,.79)*rails,
                  saturate(body+edgeCore+flecks+rails));
}

if(Mode==7) {
    float guide=ready*(shot<0.?1.:exp(-shot*27.));
    rails=(S.Beam(p,float2(-16.,23.),float2(335.,5.),.65)
          +S.Beam(p,float2(-16.,-23.),float2(335.,-5.),.65))*guide;
    float head=shot<0.?120.:HeadDistance;
    float rear=head-p.x;
    float localLife=shot<0.?ready:(1.-smoothstep(.19,.33,shot));
    for(int side=-1;side<=1;side+=2) {
        float span=shot<0.?24.-ready*12.:22.;
        float center=sin(rear*.047-Age*18.)*span*side;
        float radius=shot<0.?11.+ready*5.:21.;
        float axial=smoothstep(-20.,12.,rear)*(1.-smoothstep(95.,228.,rear));
        float mask=exp(-pow(abs(p.y-center)/radius,1.55)*2.0)*axial;
        float2 uv=float2(rear*.016-Age*1.8,(p.y-center)*.028+side*.31);
        float tex=Texture2DSample(Smoke,SmokeSampler,uv).r;
        float den=smoothstep(.03,.68,tex);
        wind=max(wind,mask*(.13+.87*den)*localLife);
        white=max(white,pow(mask,1.9)*pow(den,1.8)*localLife*.77);
    }
    // A thin short residual of the real lane, not a second projectile.
    if(shot>=0.) {
        float fade=1.-smoothstep(.04,.22,shot);
        rails+=S.Beam(p,float2(20.,-6.),float2(min(HeadDistance,900.),-2.),.42)*fade*.30;
    }
}

if(Mode==8) {
    float charge=ready*(shot<0.?1.:exp(-shot*34.));
    // A restrained split preparation makes the opening at release readable.
    for(int side=-1;side<=1;side+=2) {
        float2 q=float2(p.x,p.y*side);
        float edge=S.Edge(q,float2(-24.,32.),float2(10.,40.),float2(38.,27.),float2(49.,8.),5.4);
        wind=max(wind,(1.-smoothstep(-1.7,3.,edge))*density*charge*.60);
    }
    if(shot>=0.&&shot<.29) {
        float burst=smoothstep(0.,.050,shot),closing=smoothstep(.055,.180,shot);
        float fade=1.-smoothstep(.12,.265,shot);
        for(int side=-1;side<=1;side+=2) {
            float2 q=float2(p.x,p.y*side);
            float front=55.+burst*150.+closing*165.;
            float spread=(25.+burst*115.)*(1.-closing*.79);
            for(int blade=0;blade<2;blade++) {
                float reach=front+blade*47.,height=spread*(1.-blade*.44);
                float2 a=float2(-25.+blade*36.,height*.20);
                float2 b=float2(31.+blade*34.,height+43.);
                float2 c=float2(reach-36.,height+12.);
                float2 d=float2(reach,12.+blade*6.);
                float edge=S.Edge(q,a,b,c,d,(19.-blade*5.)*.75);
                float tearSmoke=Texture2DSample(Smoke,SmokeSampler,
                    float2(q.x*.007-Age*.91+blade*.31,q.y*.017+side*.23)).r;
                float tearWind=Texture2DSample(Wind,WindSampler,
                    float2(q.x*.012-Age*1.18,q.y*.025+blade*.43)).r;
                // Both source textures have dark regions. Multiplying them
                // erased nearly the entire face; mix their density instead.
                float gaps=smoothstep(.06,.50,tearSmoke*.65+tearWind*.35);
                // Erode the perimeter and open large gaps through the face.
                // The same mask breaks the bright edge, avoiding a continuous
                // opaque C even where the inner wind has faded away.
                float face=1.-smoothstep(-1.8,3.2,edge+(1.-tearSmoke)*2.0);
                float torn=face*(.18+.82*gaps)*fade*(1.-blade*.12);
                wind=max(wind,torn*(.50+.30*density));
                white=max(white,torn*(.04+.14*pow(density,2.)));
                float edgeBright=S.Edge(q,a+float2(-3.,4.),b+float2(-2.,5.),c+float2(3.,5.),d+float2(5.,2.),1.0);
                rails+=(1.-smoothstep(-.4,1.1,edgeBright))*fade*(.20+.80*gaps)*(.16-blade*.03);
            }
            for(int j=0;j<7;j++) {
                float seed=frac(sin(j*37.3+11.7)*7513.21);
                float2 start=float2(12.+j*17.+shot*120.,spread*(.47+seed*.60));
                flecks+=S.Beam(q,start,start+float2(-5.-seed*8.,3.+seed*6.),.65)*fade*.52;
            }
        }
        // One brief center snap aligns with the unchanged real D release.
        rails+=S.Beam(p,float2(-12.,0),float2(96.,0),.85)*exp(-shot*52.);
    }
    // D8's four overlapping faces need their own translucent budget. D6/D7
    // retain the previously reviewed composition and exposure unchanged.
    float3 tornColor=float3(1.7,.96,.32)*wind*.75+float3(2.0,1.85,1.45)*white
                     +float3(2.0,1.62,.78)*rails+float3(1.8,1.30,.49)*flecks*.64;
    // The translucent blend already multiplies opacity. Normalize this
    // weighted color so coverage is not unintentionally applied twice.
    float coverage=max(wind,max(white,rails+flecks*.5));
    tornColor=min(tornColor/max(coverage,.08),float3(3.,3.,3.));
    return float4(tornColor,min(.66,wind*.68+white*.45+rails*.66+flecks*.30));
}

float3 color=float3(2.0,1.04,.25)*wind*.66+float3(3.2,2.6,1.40)*min(white,.88)
             +float3(2.4,1.88,.79)*rails+float3(2.1,1.42,.39)*flecks;
return float4(color,saturate(wind*.54+white*.65+rails+flecks));
'''


def _write(out, name, value):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    """Connect and save only the selected preview materials, never source assets."""
    selected = [x.strip().upper() for x in os.environ.get('SPARROW_D_COMBINED_AUTHOR', ','.join(OPTIONS)).split(',') if x.strip()]
    assert selected and all(x in OPTIONS for x in selected), selected
    lib = unreal.MaterialEditingLibrary
    textures = {name: unreal.load_asset(path) for name, path in (
        ('Smoke', WRS['SMOKE_DETAIL']), ('Wind', WRS['WIND_DETAIL']), ('Detail', WRS['DETAIL']))}
    assert all(textures.values())
    paths = []
    for option in selected:
        path = ROOT+'/M_'+option
        material = unreal.load_asset(path)
        if material is None:
            folder, name = path.rsplit('/', 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        def node(kind, **properties):
            expression = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in properties.items():
                expression.set_editor_property(key, value)
            return expression
        custom = node('Custom', code=SHADER.replace('DESIGN_NUMBER', option[1:]), output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate'),
                   'Age': node('ScalarParameter', parameter_name='Age', default_value=.30),
                   'ShotAge': node('ScalarParameter', parameter_name='ShotAge', default_value=-1.),
                   'HeadDistance': node('ScalarParameter', parameter_name='HeadDistance', default_value=0.),
                   'FlightSpeed': node('ScalarParameter', parameter_name='FlightSpeed', default_value=6500.),
                   'ContactMode': node('ScalarParameter', parameter_name='ContactMode', default_value=0.)}
        sources.update({name: node('TextureObject', texture=texture) for name, texture in textures.items()})
        inputs = []
        for name in sources:
            value = unreal.CustomInput(); value.set_editor_property('input_name', name); inputs.append(value)
        custom.set_editor_property('inputs', inputs)
        for name, source in sources.items():
            assert lib.connect_material_expressions(source, '', custom, name)
        for prop, flags in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                            (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
            mask = node('ComponentMask', r=flags[0], g=flags[1], b=flags[2], a=flags[3])
            assert lib.connect_material_expressions(custom, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        paths.append(path)
    result = {'passed': True, 'preview_assets': paths, 'production_changed': False,
              'source_textures_read_only': {name: texture.get_path_name() for name, texture in textures.items()},
              'designs': DESIGNS}
    _write(out, 'd-combined-materials.json', result)
    return result


class Study(WRS['Study']):
    def __init__(self, rig, option):
        # Reuse the proven plane/particle lifecycle without loading materials
        # from the older WRS ownership folder or changing its module globals.
        BASE['Study'].__init__(self, rig, option)
        material = unreal.load_asset(ROOT+'/M_'+option)
        assert material, 'Run author before PIE: '+ROOT+'/M_'+option
        self.materials['design'] = material
        self.materials['contact'] = material
        self.surface = self.plane('design', 'DCombined_'+option)
        self.contacts = []
        self.shot, self.last_shot = -1., -1.
        self.proxy, self.proxy_mesh = None, None
        self.native = rig['pawn']().get_editor_property('mesh')
        self.original_visible = self.native.is_visible()
        self.origin = rig['skills']().get_arrow_origin()
        self.forward = unreal.Vector(1., 0., 0.)
        self.visual_events = []
        self.launch_origin, self.native_arrow = None, None
        self.head_distance = 0.
        self.flight_speed = 6500.
        self.feather_events = set()
        self.native_samples = []

    def observe_arrow(self, arrow, elapsed):
        self.native_arrow = arrow
        observed_flight = arrow.get_distance_travelled()/max(arrow.get_flight_speed(), 1.)
        # At 30 fps the first observed native arrow has already advanced one
        # frame. Align revised D6/D8 and the post-passage D9 to that release.
        self.shot = max(0., elapsed-observed_flight) if self.option in ('D6', 'D8', 'D9') else elapsed
        self.launch_origin = self.rig['skills']().get_arrow_origin()
        if self.option == 'D9':
            self.forward = arrow.get_flight_direction()
            self.flight_speed = arrow.get_flight_speed()
            self.launch_origin = arrow.get_actor_location()-self.forward*arrow.get_distance_travelled()
        self.visual_events.append({'event': 'one_native_D_observed', 'time': elapsed,
                                   'native_flight_seconds': observed_flight, 'visual_release_time': self.shot})

    def contact(self, position, elapsed, native=True):
        if self.option == 'D9':
            self.visual_events.append({'event': 'native_health_contact', 'time': round(elapsed, 4)})
            return
        super().contact(position, elapsed, native)
        self.contacts[-1]['mid'].set_scalar_parameter_value('ContactMode', 1.)

    def update(self, elapsed):
        # Freeze only this cosmetic coordinate system at release so the lane
        # does not move with the character's lowering-bow recovery animation.
        self.origin = self.launch_origin if self.launch_origin is not None else self.rig['skills']().get_arrow_origin()
        if BASE['_valid'](self.native_arrow):
            delta = self.native_arrow.get_actor_location()-self.origin
            self.head_distance = max(0., delta.x*self.forward.x+delta.y*self.forward.y+delta.z*self.forward.z)
            self.native_samples.append({'time': round(elapsed, 4), 'head_distance': round(self.head_distance, 3)})
        if self.option == 'D9' and self.shot >= 0.:
            for index in range(7):
                anchor = 110.+index*120.
                delay = .035+(index % 3)*.010
                born = self.shot+anchor/max(self.flight_speed, 1.)+delay
                if index not in self.feather_events and self.head_distance >= anchor and elapsed >= born:
                    self.feather_events.add(index)
                    self.visual_events.append({'event': 'feather_after_pass', 'index': index,
                                               'anchor_cm': anchor, 'delay_seconds': delay,
                                               'scheduled_time': round(born, 4), 'observed_time': round(elapsed, 4),
                                               'native_head_distance': round(self.head_distance, 3)})
        camera = unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](), 0).get_camera_location()
        row = self.surface
        row['actor'].set_actor_location(self.origin+self.forward*430., False, True)
        row['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(self.forward, camera-self.origin), True)
        row['mesh'].set_world_scale3d(unreal.Vector(12.5, 5.4, 1.))
        row['mid'].set_scalar_parameter_value('Age', elapsed)
        row['mid'].set_scalar_parameter_value('ShotAge', self.shot)
        row['mid'].set_scalar_parameter_value('HeadDistance', self.head_distance)
        if self.option == 'D9':
            row['mid'].set_scalar_parameter_value('FlightSpeed', self.flight_speed)
        for contact in self.contacts:
            age = elapsed-contact['started']
            contact['actor'].set_actor_location(contact['position'], False, True)
            contact['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(self.forward, camera-contact['position']), True)
            contact['mesh'].set_world_scale3d(unreal.Vector(2.5, 2.5, 1.))
            contact['mid'].set_scalar_parameter_value('Age', age)
            contact['actor'].set_actor_hidden_in_game(age>.26)
        self.tick()


def sequence(rig):
    if os.environ.get('SPARROW_QA_COMPACT_MEMORY') == '1':
        rig['cmd']('r.Streaming.PoolSize 384')
        rig['cmd']('r.Shadow.Virtual.MaxPhysicalPages 512')
        yield .5
    selected = [x.strip().upper() for x in os.environ.get('SPARROW_D_COMBINED', ','.join(OPTIONS)).split(',') if x.strip()]
    assert selected and all(x in OPTIONS for x in selected), selected
    rows = []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in selected:
        rig['switch']('countess'); yield .20
        rig['switch']('sparrow'); yield .65
        rig['cmd']('CountessComboQA.FlushInput')
        prefix = 'DCombined_'+option
        rig['case'](prefix)
        targets = rig['layout']([(540, 0), (700, 280), (780, -280)])
        yield .20
        initial = [rig['health'](target) for target in targets]
        previous = initial[:]
        study = Study(rig, option)
        started, seen, hits = now(), set(), []
        moments = [.38, .50, .60, .75, 1.0] if option == 'D9' else [.22, .35, .43, .50, .60]
        duration = 1.40
        try:
            rig['use']('D', offset=(1100, 0))
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': prefix, 'prefix': prefix+'_video', 'cast_time': started, 'frame_times': []}
            while now()-started<duration:
                elapsed = now()-started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    if arrow.get_owner()==rig['pawn']() and arrow.get_path_name() not in seen:
                        seen.add(arrow.get_path_name())
                        study.observe_arrow(arrow, elapsed)
                current = [rig['health'](target) for target in targets]
                for index, (old, new) in enumerate(zip(previous, current)):
                    if new<old-.01:
                        hits.append({'target': index, 'time': round(elapsed, 4), 'damage': old-new})
                        study.contact(targets[index].get_actor_location(), elapsed)
                previous = current
                study.update(elapsed)
                if moments and elapsed>=moments[0]:
                    rig['capture'](prefix+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage = [old-rig['health'](target) for old, target in zip(initial, targets)]
            rig['check'](len(seen)==1 and len(hits)==1, option+' preserves one operating D arrow and one native target contact')
            rig['check'](abs(damage[0]-65.)<.03 and max(damage[1:])<.03, option+' preserves 65 damage without cosmetic damage')
            rig['check'](bool(study.native_samples) and study.shot>=.30, option+' attaches visual release to the operating projectile')
            if option == 'D9':
                rig['check'](len(study.feather_events)==7, option+' leaves all seven feathers behind the passed native head')
            rig['recovered']()
            row = {'id': option, **DESIGNS[option], 'video_prefix': prefix+'_video', 'duration_seconds': duration,
                   'installed': False, 'native_cast': 'D', 'native_arrow_count': len(seen), 'hits': hits,
                   'damage': damage, 'shot_time': study.shot, 'native_head_samples': study.native_samples,
                   'visual_events': study.visual_events, 'peak_live_particles': study.peak_particles,
                   'visual_review': 'pending actual quarter-view frame and video review'}
        finally:
            rig['finish_video_clip']()
            failures = study.close()
        rig['check'](not failures and not study.planes and not study.effects, option+' clears temporary actors and particles')
        rows.append(row)
        _write(rig['OUT'], 'd-combined-studies.json', {'passed': len(rows)==len(selected), 'studies': rows,
               'production_changed': False, 'note': 'Selection previews only. Every study uses the operating D arrow, damage, animation and collision; no skill or runtime material is installed.'})

