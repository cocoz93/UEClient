"""W/R/D native-cast overlays and three S tempest proposals in isolated PIE.

Only Previews/WRSTempest20261024 materials are saved. W/R retain every native
projectile, hit and animation. S uses a temporary mesh with the source attack
sequence: its arrows, wind and impacts are visual props with no gameplay.
GPU execution belongs to the integrating parent. Filter SPARROW_WRS_OPTIONS.
D is opt-in via SPARROW_D_OPTIONS; the user confirmed that its two proposals
should build on the current D piercing shot.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
BOW = runpy.run_path(str(Path(__file__).with_name('sparrow_bow_audit.py')))
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/WRSTempest20261024'
ANIMATION = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/R_Ability_Med_Fire'
DETAIL = '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'
WIND_DETAIL = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'
SMOKE_DETAIL = '/Game/ParagonSparrow/FX/Textures/Tile/Smoke/T_Smoke_Tiled_D'
OPTIONS = ('W4', 'W5', 'R4', 'R5', 'S4', 'S5', 'S6')
D_OPTIONS = ('D4', 'D5')
VARIANTS = {name: index for index, name in enumerate(OPTIONS + ('Impact',) + D_OPTIONS)}
DESIGNS = {
    'W4': {'label': '분절 대궁', 'shape': '다섯 장의 넓은 활 조각이 양끝으로 차례로 펼쳐지고 시위에 압축된 뒤 한 번에 파열',
           'role': '기존 W 충전과 얇은 관통 화살에 큰 활의 개방과 짧은 접촉 파열만 추가'},
    'W5': {'label': '백금 관통 레일', 'shape': '짧은 사선 칼날과 평행 레일이 활 앞에 조립되고 발사 때 전방으로 찢어짐',
           'role': '큰 활 대신 좁고 단단한 직선 실루엣, 기존 W 화살 두께 유지'},
    'R4': {'label': '천궁 일제사격', 'shape': '큰 깃 장궁과 세 겹의 시위가 실제 6연속 발사마다 반동하며 빛을 방출',
           'role': '기존 짧고 빽빽한 작은 화살 유지, 발사점의 큰 활만 보강'},
    'R5': {'label': '삼익 사격진', 'shape': '등 뒤와 양옆으로 분리된 세 활 프레임이 다른 각도로 펼쳐져 실제 사격 파형에 맞춰 점등',
           'role': '중앙 거대 활 대신 넓게 열린 3분할 실루엣으로 다발 사격 강조'},
    'S4': {'label': '나선 폭풍 연사', 'shape': '진행 축을 따라 꼬인 반투명 바람 덩어리가 밝고 짧은 화살 묶음 네 개를 밀어냄',
           'role': '전방 직선 집중 연사 제안, 느린 톱니 A와 분리'},
    'S5': {'label': '삼중 돌풍 해일', 'shape': '찢어진 다섯 바람 흐름이 넓게 퍼지며 세 차례 작은 화살 부채를 밀어냄',
           'role': '넓은 전방을 세 차례 강하게 두드리는 파상 공격 제안'},
    'S6': {'label': '쌍류 폭풍 관통', 'shape': '좌우 두 화살 줄기와 불규칙한 바람이 중앙으로 좁혀들며 하나의 회오리로 합쳐짐',
           'role': '좌우 수렴과 짧은 연속 타격을 가진 집중 공격 제안'},
    'D4': {'label': '백금 저격선', 'shape': '가는 금빛 레일과 조준 눈금이 전방으로 정렬되고 한 발이 지나간 뒤 짧은 십자 접촉만 남음',
           'role': '현재 D 관통 사격을 기반으로 한 선택용 저격 연출, 원래 거대 화살을 추가 복제하지 않음',
           'reference_confirmed': '사용자가 현재 D 관통 사격을 기반으로 진행하는 방향 확인'},
    'D5': {'label': '분절 바람창', 'shape': '사선 바람 틈이 짧게 벌어지고 실제 화살이 통과한 자리에 떨어진 곡선 조각들이 잠깐 남음',
           'role': '현재 D 관통 사격을 기반으로 한 공간 파열 연출, 화살 추가 복제 없이 여운의 형태를 변경',
           'reference_confirmed': '사용자가 현재 D 관통 사격을 기반으로 진행하는 방향 확인'},
}

SHADER = r'''
struct FShape {
    float Seg(float2 p,float2 a,float2 b) {
        float2 d=b-a; return length(p-a-d*saturate(dot(p-a,d)/max(dot(d,d),.001)));
    }
    float2 Curve(float2 a,float2 b,float2 c,float2 d,float t) {
        float u=1.-t; return u*u*u*a+3.*u*u*t*b+3.*u*t*t*c+t*t*t*d;
    }
    float Ribbon(float2 p,float2 a,float2 b,float2 c,float2 d,float width) {
        float edge=10000.;
        for(int i=0;i<16;i++) {
            float t=i/16.,n=(i+1)/16.;
            edge=min(edge,Seg(p,Curve(a,b,c,d,t),Curve(a,b,c,d,n))-width*pow(max(sin(n*3.14159265),.001),.65));
        }
        return 1.-smoothstep(-.45,1.05,edge);
    }
    float Line(float2 p,float2 a,float2 b,float width) {return exp(-Seg(p,a,b)/max(width,.2));}
    float Arrow(float2 p,float2 center,float2 direction,float length,float width) {
        float2 across=float2(-direction.y,direction.x),v=p-center;
        float2 q=float2(dot(v,direction),dot(v,across));
        float shaft=Line(q,float2(-length*.5,0),float2(length*.35,0),width);
        float head=Line(q,float2(length*.5,0),float2(length*.15,width*4.),width)
                  +Line(q,float2(length*.5,0),float2(length*.15,-width*4.),width);
        return max(shaft,head);
    }
};
FShape S;
const int Variant=VARIANT;
const float PI=3.14159265;
float2 p=(UV-.5)*float2(PLANE_WIDTH,PLANE_HEIGHT)+float2(PLANE_SHIFT,0);
float core=0.,body=0.,detail=0.,spark=0.;
float grain=Texture2DSample(Detail,DetailSampler,UV*float2(5.7,3.1)+float2(-Age*.7,Age*.2)).r;
float shot=ShotAge<0.?-1.:Age-ShotAge;
float pulse=LastShot<0.?0.:exp(-max(Age-LastShot,0.)*34.);

if(Variant<4) {
    float open=smoothstep(0.,Variant<2?.34:.10,Age);
    float fade=Variant<2?(shot<0.?1.:1.-smoothstep(.04,.23,shot)):(1.-smoothstep(.74,.95,Age));
    float2 q=float2(p.x,abs(p.y)/max(.03,open));
    if(Variant==0) {
        // Five overlapping broad plates retain gaps between their outer tips.
        for(int j=0;j<5;j++) {
            float reveal=smoothstep(j*.045,j*.045+.13,Age);
            float y=19.+j*34.;
            float x=34.*sin((j+.5)/5.*PI)-(1.-reveal)*75.;
            float2 root=float2(x,y),tip=float2(x-39.-j*3.,y+45.);
            body+=S.Ribbon(q,root,root+float2(30.,6.),tip+float2(22.,-2.),tip,9.-j*.7)*reveal;
            core+=S.Ribbon(q,root,root+float2(27.,7.),tip+float2(24.,-3.),tip,1.4)*reveal;
            detail+=S.Line(q,root+float2(-3.,6.),root+float2(-36.,24.),1.)*reveal;
        }
        float draw=shot<0.?smoothstep(.11,.56,Age):exp(-shot*32.);
        core+=S.Line(q,float2(-10.,182.),float2(-81.*draw,0),.85);
        core+=S.Arrow(p,float2(49.,0),float2(1,0),95.,.85)*smoothstep(.19,.58,Age);
    } else if(Variant==1) {
        for(int j=0;j<4;j++) {
            float reveal=smoothstep(.02+j*.065,.13+j*.065,Age);
            float x=22.+j*37.+(1.-reveal)*55.;
            float y=52.-j*9.;
            body+=S.Ribbon(q,float2(x-12.,y+9.),float2(x-3.,y+4.),float2(x+11.,y*.6),float2(x+18.,0),3.7)*reveal;
            core+=S.Line(q,float2(x-12.,y+9.),float2(x+18.,0),1.05)*reveal;
        }
        core+=S.Line(p,float2(-12.,18.),float2(170.,7.),.85)*open;
        core+=S.Line(p,float2(-12.,-18.),float2(170.,-7.),.85)*open;
        detail+=S.Arrow(p,float2(80.,0),float2(1,0),165.,.55)*open;
    } else {
        int count=Variant==2?1:3;
        for(int k=0;k<count;k++) {
            // Leave a visible gap between the three frames; overlapping half-
            // spans previously read as one scalloped strip in quarter view.
            float2 center=Variant==2?float2(10.,0):float2(k==1?-58.:-93.,(k-1)*143.);
            float turn=Variant==2?0.:(k-1)*.24;
            float2 v=p-center;
            float2 z=float2(v.x*cos(turn)+v.y*sin(turn),abs(-v.x*sin(turn)+v.y*cos(turn))/max(.04,open));
            float height=Variant==2?210.:62.;
            float limbScale=Variant==2?1.:.70;
            float edge=10000.;
            for(int j=0;j<20;j++) {
                float t=j/20.,n=(j+1)/20.;
                float2 a=S.Curve(float2(0,0),float2(58.*limbScale,height*.4),float2(29.*limbScale,height*.8),float2(-28.*limbScale,height),t);
                float2 b=S.Curve(float2(0,0),float2(58.*limbScale,height*.4),float2(29.*limbScale,height*.8),float2(-28.*limbScale,height),n);
                edge=min(edge,S.Seg(z,a,b)-(4.+5.*sin(n*PI))*limbScale);
            }
            body+=1.-smoothstep(-.7,.8,edge);
            core+=exp(-abs(edge)*1.4)*.58;
            for(int j=0;j<5;j++) {
                if(Variant==3)continue;
                float y=height*(.25+j*.14),x=31.*sin(y/height*PI);
                body+=S.Ribbon(z,float2(x,y),float2(x-20.,y+7.),float2(x-56.,y+28.),float2(x-73.+j*8.,y+39.),5.-j*.35)*.55;
            }
            for(int j=0;j<(Variant==2?3:1);j++) {
                float pull=(30.+j*13.+pulse*13.)*limbScale;
                core+=S.Line(z,float2(-28.*limbScale,height),float2(-pull,0),.65)*(.62+j*.11);
            }
        }
    }
    for(int j=0;j<36;j++) {
        float seed=frac(sin(j*127.1+1.7)*43758.5453);
        float born=seed*.21,t=Age-born,life=saturate(t/.38);
        float2 v=q-float2(-32.-seed*42.-t*66.,22.+j*5.+t*85.);
        spark+=(exp(-abs(v.x)*1.3-abs(v.y)*.32)+exp(-abs(v.x)*.3-abs(v.y)*1.8))*sin(life*PI)*step(0.,t)*.25;
    }
    float3 color=float3(1.6,.68,.08)*body*(.27+.42*grain)+float3(2.8,2.25,1.1)*(core+detail*.65+spark);
    return float4(color*(1.+pulse*.45),saturate(body+core+detail+spark)*open*fade);
}

if(Variant==7) {
    // Two small, directional contacts 55 ms apart. No full disc or screen flash.
    for(int k=0;k<2;k++) {
        float t=Age-k*.055;
        if(t>=0.&&t<.24) {
            float fade=1.-smoothstep(.02,.24,t),size=k==0?1.:.64;
            core+=S.Line(p,float2(-55.,-2.)*size,float2(45.,2.)*size,2.5)*exp(-t*42.);
            core+=S.Line(p,float2(-15.,-34.)*size,float2(18.,37.)*size,1.5)*exp(-t*48.);
            for(int j=0;j<20;j++) {
                float seed=frac(sin(j*91.7+2.4)*47321.37),a=j*6.2831853/20.+k*.22;
                float2 d=float2(cos(a),sin(a)*.62);
                float r=(8.+t*(160.+seed*180.))*size;
                spark+=S.Line(p,d*r,d*(r+7.+seed*12.),.75)*fade;
            }
        }
    }
    return float4(float3(2.9,2.2,.85)*core+float3(1.9,1.12,.17)*spark,saturate(core+spark));
}

if(Variant==8) {
    // No cosmetic arrow or broad beam: the operating D lance remains the shot.
    float ready=smoothstep(.02,.26,Age);
    float guide=shot<0.?ready:exp(-shot*25.);
    float reach=80.+smoothstep(.02,.30,Age)*780.;
    float lead=1.-smoothstep(reach-15.,reach+5.,p.x);
    core+=(S.Line(p,float2(6.,13.),float2(860.,5.),.65)
          +S.Line(p,float2(6.,-13.),float2(860.,-5.),.65))*guide*lead;
    for(int j=0;j<7;j++) {
        float x=83.+j*104.,signY=j%2==0?1.:-1.;
        float reveal=smoothstep(.03+j*.025,.11+j*.025,Age);
        detail+=S.Line(p,float2(x,signY*15.),float2(x+6.,signY*24.),.72)*reveal*guide;
        if(j<3)detail+=S.Line(p,float2(x,-signY*15.),float2(x+4.,-signY*20.),.58)*reveal*guide;
    }
    float focus=shot<0.?ready:exp(-shot*55.);
    core+=S.Line(p,float2(-12.,-18.),float2(13.,18.),1.25)*focus;
    core+=S.Line(p,float2(-18.,9.),float2(26.,-12.),1.25)*focus;
    return float4(float3(2.3,1.8,.7)*core+float3(1.7,.84,.16)*detail,saturate(core+detail));
}

if(Variant==9) {
    // Short separated wind windows: no single giant duplicate arrow silhouette.
    float prepare=smoothstep(.03,.25,Age)*(shot<0.?1.:exp(-shot*28.));
    for(int side=-1;side<=1;side+=2) {
        float2 z=float2(p.x,p.y*side);
        body+=S.Ribbon(z,float2(-23.,63.),float2(24.,70.),float2(63.,34.),float2(79.,0),5.)*prepare;
        core+=S.Ribbon(z,float2(-29.,70.),float2(24.,77.),float2(67.,36.),float2(84.,0),.85)*prepare*.7;
    }
    if(shot>=0.) {
        for(int j=0;j<6;j++) {
            float t=shot-j*.018;
            if(t<0.||t>.40)continue;
            float fade=1.-smoothstep(.025,.40,t);
            float x=92.+j*116.,signY=j%2==0?1.:-1.;
            float spread=34.+t*90.;
            float2 z=float2(p.x,p.y*signY);
            body+=S.Ribbon(z,float2(x-42.,spread),float2(x-9.,spread+16.),float2(x+18.,spread*.4),float2(x+31.,-8.),4.2)*fade;
            core+=S.Ribbon(z,float2(x-49.,spread+7.),float2(x-10.,spread+24.),float2(x+24.,spread*.4),float2(x+39.,-5.),.9)*fade*.8;
            detail+=S.Line(z,float2(x-16.,spread+13.),float2(x-32.,spread+22.),.7)*fade;
        }
    }
    return float4(float3(1.7,.83,.12)*body*(.4+grain*.35)+float3(2.3,1.85,.88)*(core+detail),saturate(body+core+detail));
}

// S uses directional textured volumes. No bow-front C, enclosing ring, or
// hard ribbon boundary survives here: irregular density defines the silhouette.
float envelope=smoothstep(.0,.10,Age)*(1.-smoothstep(1.68,2.04,Age));
float wind=0.;
int packets=Variant==4?4:3;
float cadence=Variant==4?.18:.29;
float ready=smoothstep(.01,.10,Age)*(1.-smoothstep(.27,.40,Age));
float readyNoise=Texture2DSample(Smoke,SmokeSampler,float2(p.x*.018-Age*2.,p.y*.034)).r;
float readyShape=exp(-pow(abs(p.y)/15.,1.5))*smoothstep(-45.,-22.,p.x)*(1.-smoothstep(46.,88.,p.x));
wind=readyShape*(.13+.87*smoothstep(.04,.62,readyNoise))*ready*.65;
core=pow(readyShape,2.)*pow(saturate(readyNoise),1.6)*ready*.70;
for(int wave=0;wave<4;wave++) {
    if(wave>=packets)continue;
    float age=Age-(.30+wave*cadence);
    float distance=age*1250.;
    if(age>=0.&&distance<925.) {
        float fade=1.-smoothstep(680.,890.,distance);
        int streams=Variant==4?2:Variant==5?5:2;
        for(int stream=0;stream<5;stream++) {
            if(stream>=streams)continue;
            float trail=distance-p.x;
            float side=stream==0?-1.:1.;
            float centerY=0.,radius=0.,tailLength=0.;
            if(Variant==4) {
                // Two irregular, intertwined axial plumes carry one compact
                // arrow packet. Their surface stays open and translucent.
                float taper=saturate(1.-max(trail,0.)/240.);
                centerY=side*sin(trail*.043-Age*17.)*(10.+15.*taper);
                radius=13.+22.*taper;
                tailLength=225.;
            } else if(Variant==5) {
                float lane=(stream-2.)/2.;
                trail+=abs(lane)*24.;
                centerY=lane*(48.+distance*.18)-trail*lane*.16
                       +sin(trail*.035-Age*13.+stream*1.9)*14.;
                radius=15.+7.*sin(stream+1.7)+max(trail,0.)*.018;
                tailLength=175.+(stream%2)*40.;
            } else {
                float spread=max(7.,108.-distance*.17);
                float taper=saturate(1.-max(trail,0.)/210.);
                centerY=side*(spread+sin(trail*.047-Age*15.)*(10.+12.*taper));
                radius=15.+17.*taper;
                tailLength=205.;
            }
            float transverse=p.y-centerY;
            float axial=smoothstep(-27.,8.,trail)*(1.-smoothstep(tailLength*.47,tailLength,trail));
            float profile=exp(-pow(abs(transverse)/max(radius,1.),1.55)*1.8)*axial;
            float2 smokeUV=float2(trail*.012-Age*1.9+stream*.31,transverse*.022+sin(trail*.027-Age*8.)*.20+wave*.37);
            float cloud=Texture2DSample(Smoke,SmokeSampler,smokeUV).r;
            float fine=Texture2DSample(Wind,WindSampler,smokeUV*float2(.73,1.41)+float2(Age*.33,0)).r;
            float density=smoothstep(.035,.68,cloud)*(.75+.25*fine);
            // The texture controls both interior and edge opacity. There is
            // no opaque gold plate beneath the transparent wind detail.
            wind=max(wind,profile*(.10+.90*density)*fade);
            core=max(core,pow(profile,1.65)*pow(density,1.55)*fade*.78);
            // Short irregular wakes trail the packet rather than encircling it.
            float wakeProfile=exp(-pow(abs(transverse+sin(trail*.041+stream)*10.)/(radius*.43),1.5)*2.4)
                *smoothstep(35.,70.,trail)*(1.-smoothstep(tailLength*.65,tailLength+36.,trail));
            wind=max(wind,wakeProfile*density*fade*.48);
        }
        for(int j=0;j<15;j++) {
            float seed=frac(sin(j*41.7+wave*9.1)*43117.81);
            float lane=(j-7.)/7.;
            float y=Variant==4?lane*22.:Variant==5?lane*(50.+distance*.16)
                :(j<8?-1.:1.)*max(7.,108.-distance*.17)+((j%8)-3.5)*3.3;
            float x=distance-seed*62.;
            float2 direction=normalize(float2(1,Variant==5?lane*.16:Variant==6?(j<8?.17:-.17):0.));
            detail+=S.Arrow(p,float2(x,y),direction,20.+seed*13.,.72)*fade;
        }
        // Sparse torn-off flecks reinforce speed without another long arrow.
        for(int j=0;j<12;j++) {
            float seed=frac(sin(j*78.3+wave*17.1)*19751.17);
            float rear=38.+seed*184.;
            float spread=Variant==4?37.:Variant==5?58.+distance*.14:max(18.,100.-distance*.15);
            float2 spot=float2(distance-rear,(seed-.5)*2.*spread);
            float2 d=p-spot;
            float fleck=exp(-abs(d.x)*.26-abs(d.y)*1.1)*(.25+.75*seed);
            core+=fleck*fade*.14;
        }
    }
}
// White cores remain local to the dense flow. The surrounding gold wind is
// translucent, so the floor remains visible through the edges and dark gaps.
float3 color=float3(2.1,1.13,.29)*wind*.58+float3(3.9,3.25,1.85)*min(core,.86)
             +float3(2.7,2.2,1.10)*detail*.92;
return float4(color,saturate(wind*.51+core*.59+detail)*envelope);
'''


def _write(out, name, data):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    """Save only the preview-owned graph; source textures are read only."""
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(DETAIL)
    wind_texture = unreal.load_asset(WIND_DETAIL)
    smoke_texture = unreal.load_asset(SMOKE_DETAIL)
    assert texture and wind_texture and smoke_texture and unreal.load_asset(ANIMATION)
    paths = []
    selected = [name.strip() for name in os.environ.get('SPARROW_WRS_AUTHOR_OPTIONS', ','.join(VARIANTS)).split(',') if name.strip()]
    assert selected and all(name in VARIANTS for name in selected), selected
    for option in selected:
        index = VARIANTS[option]
        width, height, shift = (700, 600, 110) if index < 4 else (250, 250, 0) if option == 'Impact' else (1250, 540, 430)
        path = ROOT + '/M_' + option
        material = unreal.load_asset(path)
        if material is None:
            folder, name = path.rsplit('/', 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        def node(kind, **props):
            value = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for key, field in props.items():
                value.set_editor_property(key, field)
            return value
        code = SHADER.replace('VARIANT', str(index)).replace('PLANE_WIDTH', str(float(width))).replace('PLANE_HEIGHT', str(float(height))).replace('PLANE_SHIFT', str(float(shift)))
        custom = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate'), 'Age': node('ScalarParameter', parameter_name='Age', default_value=.35),
                   'ShotAge': node('ScalarParameter', parameter_name='ShotAge', default_value=-1.),
                   'LastShot': node('ScalarParameter', parameter_name='LastShot', default_value=-1.),
                   'Detail': node('TextureObject', texture=texture),
                   'Wind': node('TextureObject', texture=wind_texture),
                   'Smoke': node('TextureObject', texture=smoke_texture)}
        inputs = []
        for name in sources:
            item = unreal.CustomInput(); item.set_editor_property('input_name', name); inputs.append(item)
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
    result = {'passed': True, 'preview_assets': paths, 'production_changed': False, 'designs': DESIGNS}
    _write(out, 'wrs-tempest-materials.json', result)
    return result


class Study(BASE['Study']):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.materials['design'] = unreal.load_asset(ROOT + '/M_' + option)
        self.materials['contact'] = unreal.load_asset(ROOT + '/M_Impact')
        assert self.materials['design'] and self.materials['contact'], 'author preview materials before PIE'
        self.surface = self.plane('design', 'Tempest_' + option)
        self.contacts = []
        self.shot, self.last_shot = -1., -1.
        self.proxy, self.proxy_mesh = None, None
        self.native = rig['pawn']().get_editor_property('mesh')
        self.original_visible = self.native.is_visible()
        self.origin = rig['skills']().get_arrow_origin()
        self.forward = unreal.Vector(1., 0., 0.)
        self.target = None
        self.visual_events = []
        self.seen_waves = set()

    def pose_proxy(self):
        """S animation is a transient source-pose prop, never a native skill cast."""
        self.proxy = BOW['spawn_preview'](self.rig['world'](), self.rig['cmd'])
        self.proxy.set_editor_property('tags', [BASE['TAG']])
        self.proxy_mesh = self.proxy.get_editor_property('skeletal_mesh_component')
        self.proxy_mesh.set_skeletal_mesh_asset(self.native.get_skeletal_mesh_asset())
        self.proxy_mesh.set_editor_property('disable_cloth_simulation', True)
        self.proxy_mesh.set_forced_lod(1)
        self.proxy_mesh.set_cast_shadow(False)
        for index in range(self.native.get_num_materials()):
            self.proxy_mesh.set_material(index, self.native.get_material(index))
        self.proxy.set_actor_transform(self.native.get_world_transform(), False, True)
        self.animation = unreal.load_asset(ANIMATION)
        assert self.animation.get_editor_property('skeleton') == self.native.get_skeletal_mesh_asset().get_editor_property('skeleton')
        self.proxy_mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.proxy_mesh.play_animation(self.animation, False)
        self.proxy_mesh.set_play_rate(0.)
        self.native.set_visibility(False, False)

    def contact(self, position, elapsed, native):
        row = self.plane('contact', 'NativeContact' if native else 'ConceptContact')
        row['position'], row['started'] = position, elapsed
        self.contacts.append(row)
        self.pulse('impact', ('Sparks', 'SparkTrailHeads'), position,
                   unreal.MathLibrary.make_rot_from_x(self.forward), (.57, .57, .57), .25, 2.0)
        self.visual_events.append({'event': 'native_health_contact' if native else 'visual_contact_no_damage', 'time': round(elapsed, 4)})

    def update(self, t):
        if not self.option.startswith('S'):
            self.origin = self.rig['skills']().get_arrow_origin()
        if self.proxy_mesh:
            cadence = .18 if self.option == 'S4' else .29
            count = 4 if self.option == 'S4' else 3
            # Existing R sequence segments mirror the operating multishot's
            # preparation, repeated firing, and bow-lowering tail.
            if t < .30:
                pose = .33 + min(t/.30, 1.)*.12
            elif t < .30 + count*cadence:
                pose = ((t-.30) % cadence)/cadence*.45
            else:
                pose = .45 + min((t-(.30+count*cadence))/.22, 1.)*.15
            self.proxy_mesh.set_position(min(pose, self.animation.get_play_length()), False)
            self.origin = self.proxy_mesh.get_socket_location('BowEmitterSocket')
            for index in range(count):
                release = .30 + index*cadence
                if t >= release and ('release', index) not in self.seen_waves:
                    self.seen_waves.add(('release', index))
                    self.pulse('muzzle', ('Sparks',), self.origin, unreal.Rotator(), (.65, .65, .65), .19, 2.0)
                    self.visual_events.append({'event': 'visual_packet_no_damage', 'packet': index, 'time': round(t, 4)})
                # The conceptual projected packet is aimed through the dummy's
                # screen lane; the contact effect does not alter that dummy.
                arrival = release + .43
                if t >= arrival and ('hit', index) not in self.seen_waves:
                    self.seen_waves.add(('hit', index))
                    self.contact(self.target, t, False)
        camera = unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](), 0).get_camera_location()
        rotation = unreal.MathLibrary.make_rot_from_xz(self.forward, camera-self.origin)
        row = self.surface
        width, height, shift = (700., 600., 110.) if self.option[0] in ('W', 'R') else (1250., 540., 430.)
        row['actor'].set_actor_location(self.origin+self.forward*shift, False, True)
        row['actor'].set_actor_rotation(rotation, True)
        row['mesh'].set_world_scale3d(unreal.Vector(width/100., height/100., 1.))
        row['mid'].set_scalar_parameter_value('Age', t)
        row['mid'].set_scalar_parameter_value('ShotAge', self.shot)
        row['mid'].set_scalar_parameter_value('LastShot', self.last_shot)
        for contact in self.contacts:
            age = t-contact['started']
            contact['actor'].set_actor_location(contact['position'], False, True)
            contact['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(self.forward, camera-contact['position']), True)
            contact['mesh'].set_world_scale3d(unreal.Vector(2.5, 2.5, 1.))
            contact['mid'].set_scalar_parameter_value('Age', age)
            contact['actor'].set_actor_hidden_in_game(age > .30)
        self.tick()

    def close(self):
        self.native.set_visibility(self.original_visible, False)
        if BASE['_valid'](self.proxy):
            self.proxy.destroy_actor()
        self.proxy, self.proxy_mesh = None, None
        failures = super().close()
        if self.native.is_visible() != self.original_visible:
            failures.append('native mesh visibility')
        return failures


def sequence(rig):
    if os.environ.get('SPARROW_QA_COMPACT_MEMORY') == '1':
        rig['cmd']('r.Streaming.PoolSize 384')
        rig['cmd']('r.Shadow.Virtual.MaxPhysicalPages 512')
        yield .5
    selected = [x.strip().upper() for x in os.environ.get('SPARROW_WRS_OPTIONS', ','.join(OPTIONS)).split(',') if x.strip()]
    selected_d = [x.strip().upper() for x in os.environ.get('SPARROW_D_OPTIONS', '').split(',') if x.strip()]
    assert all(x in OPTIONS for x in selected) and all(x in D_OPTIONS for x in selected_d), (selected, selected_d)
    selected += selected_d
    assert selected, 'Select SPARROW_WRS_OPTIONS and/or opt-in SPARROW_D_OPTIONS'
    rows = []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in selected:
        rig['switch']('countess'); yield .20
        rig['switch']('sparrow'); yield .65
        rig['cmd']('CountessComboQA.FlushInput')
        prefix = 'Tempest_' + option
        rig['case'](prefix)
        targets = rig['layout']([(540, 0), (700, 280), (780, -280)])
        yield .20
        initial = [rig['health'](target) for target in targets]
        last = initial[:]
        study = Study(rig, option)
        study.target = targets[0].get_actor_location()
        started = now()
        seen, hits = set(), []
        duration = 2.15 if option.startswith('S') else 1.65
        moments = [.22, .48, .68, 1.03] if option.startswith('W') else [.16, .36, .58, .78] if option.startswith('R') else [.22, .37, .48, .65] if option.startswith('D') else [.22, .47, .80, 1.16]
        try:
            if option.startswith('S'):
                study.pose_proxy()
            else:
                rig['use'](option[0], offset=(1100, 0))
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': prefix, 'prefix': prefix+'_video', 'cast_time': started, 'frame_times': []}
            while now()-started < duration:
                elapsed = now()-started
                new_arrows = []
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    if arrow.get_owner() == rig['pawn']() and arrow.get_path_name() not in seen:
                        seen.add(arrow.get_path_name()); new_arrows.append(arrow)
                if new_arrows:
                    if study.shot < 0.:
                        study.shot = elapsed
                    study.last_shot = elapsed
                current = [rig['health'](target) for target in targets]
                for index, (before, after) in enumerate(zip(last, current)):
                    if after < before-.01:
                        hits.append({'target': index, 'time': elapsed, 'damage': before-after})
                        study.contact(targets[index].get_actor_location(), elapsed, True)
                last = current
                study.update(elapsed)
                if moments and elapsed >= moments[0]:
                    rig['capture'](prefix+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage = [before-rig['health'](target) for before, target in zip(initial, targets)]
            if option.startswith('S'):
                rig['check'](not seen and all(abs(value)<.001 for value in damage), option+' has visual packets but no native projectile or damage')
                rig['check'](len([e for e in study.visual_events if e['event']=='visual_packet_no_damage']) == (4 if option=='S4' else 3), option+' presents every proposed burst')
            else:
                rig['check'](bool(seen) and study.shot >= 0. and bool(hits), option+' observes real native shots and target contacts')
                if option.startswith('W'):
                    rig['check'](len(seen)==1, option+' retains one native thin W arrow')
                if option.startswith('D'):
                    rig['check'](len(seen)==1 and abs(damage[0]-65.)<.03 and max(damage[1:])<.03,
                                 option+' retains one existing D lance and its 65-damage contact')
                rig['recovered']()
            row = {'id': option, **DESIGNS[option], 'video_prefix': prefix+'_video', 'duration_seconds': duration,
                   'installed': False, 'native_cast': option[0] if not option.startswith('S') else None,
                   'concept_gameplay_implemented': False, 'native_arrows_observed': len(seen),
                   'target_health_delta': damage, 'native_hits': hits, 'events': study.visual_events,
                   'visual_review': 'pending actual game frames', 'peak_live_particles': study.peak_particles}
        finally:
            rig['finish_video_clip']()
            failures = study.close()
        rig['check'](not failures and not study.planes and not study.effects, option+' clears its props and restores native visibility')
        rows.append(row)
        _write(rig['OUT'], 'wrs-tempest-studies.json', {'passed': len(rows)==len(selected), 'studies': rows,
               'production_changed': False, 'note': 'W/R are isolated native-cast overlays. S uses an animated visual proxy; no S input, damage or skill is installed. D is opt-in and uses the current piercing D, confirmed by the user.'})

