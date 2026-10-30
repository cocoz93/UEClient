"""Six playable S presentation studies based on the approved 2D design sheets.

B and F replace only the disliked opening ideas. Collision, damage and the
15 parallel native arrows remain owned by SparrowSharpVolley/SparrowArrow.
"""
import hashlib
import json
from pathlib import Path
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/SharpArt20261026'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
DESIGNS = {6:'A 겹광륜', 7:'B 짧은 광류', 8:'C 빛의 장막', 9:'D 압축 폭풍', 10:'E 황금 결정', 11:'F 광편 점화'}

COMMON = r'''
const float design=DESIGN;
const float PI=3.14159265;
float2 p=(UV-.5)*2.;
float r=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.65,.003);
float n=Texture2DSample(Flow,FlowSampler,UV*2.1+float2(Age*.19,-Age*.45)+Index*.13).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*6.7+float2(-Age*.37,Age*.29)).g;
float3 gold=float3(1.35,.38,.035);
float3 warm=float3(2.8,1.3,.23);
float3 white=float3(4.3,3.2,1.2);
float fired=1.-step(10.,ShotAge);
float st=max(0.,ShotAge);
float open=smoothstep(.005,.09,Age);
float squeeze=smoothstep(.20,.36,Age);
float prepare=open*(1.-fired);
float tail=(1.-smoothstep(.09,.26,st))*fired;
float3 rgb=0.; float alpha=0.;
'''

MUZZLE = r'''
float rad=lerp(.72,.20,squeeze)*open;
float distance=abs(r-rad);
float ring=exp(-pow(distance/(.006+aa),2.));
float broad=exp(-pow(distance/.07,2.));
float core=exp(-r*r/.012);
float phase=a-Age*15.-Index*1.6;
float crescent=pow(saturate(cos(phase)),3.)*exp(-pow((r-rad*.90)/.09,2.));
float inner=pow(saturate(cos(phase+r*12.)),8.)*exp(-pow((r-rad*.70)/.12,2.));
float fade=open*lerp(1.,1.-smoothstep(.008,.075,st),fired);
if(design<.5) {
    float second=exp(-pow((r-rad*1.075)/(.004+aa),2.));
    float flecks=pow(saturate(fine*1.35-.32),4.)*broad;
    float movingCrest=pow(saturate(cos(phase)),10.);
    float texturedCrescent=crescent*(.35+n*.8+fine*.25);
    rgb=white*(ring*(.08+movingCrest*.50)+core*squeeze*.6)+warm*(texturedCrescent*1.4+second*.08)+gold*(inner*1.3+broad*.5+flecks*1.5);
    alpha=ring*.28+texturedCrescent*.85+broad*.20+second*.15+inner*.6+core*squeeze*.65;
} else {
    // The other silhouettes live on their own spatial surfaces, not on five large rings.
    float glow=exp(-r*r/.018)*(.3+squeeze*.7);
    float flick=exp(-pow(p.x/.009,2.)-pow(p.y/.12,2.))+exp(-pow(p.y/.009,2.)-pow(p.x/.12,2.));
    rgb=warm*glow+white*flick*squeeze*.35;
    alpha=glow*.6+flick*squeeze*.3;
}
return float4(rgb*fade,saturate(alpha)*fade);
'''

BODY = r'''
if(design<.5) {
    float sparks=0.;
    for(int i=0;i<45;++i) {
        float h=frac(sin(float(i)*64.72+Index*13.)*1723.3);
        float ang=float(i)*2.39996+Age*1.5;
        float rr=(.30+h*.55)*open*(1.-squeeze*.4+fired*st*1.7);
        float2 q=p-float2(cos(ang),sin(ang))*rr;
        sparks+=exp(-dot(q,q)/(.00003+h*.00012))*(.45+.55*sin(Age*22.+h*19.));
    }
    rgb=warm*sparks*1.2;
    alpha=sparks*.8;
} else if(design<1.5) {
    // B revised opening: three compact curved light folds, no sprawling back-loop or knot.
    float x=UV.x;
    float envelope=pow(saturate(sin(x*PI)),.8);
    float bands=0.; float seams=0.; float haze=0.;
    for(int i=0;i<2;++i) {
        float side=float(i)*2.-1.;
        float curve=side*(.12+.56*envelope)*(1.-squeeze*.65)+.10*sin(x*6.-Age*10.+Index);
        curve+=fired*side*st*1.4;
        float d=p.y-curve;
        float width=(.06+.12*envelope)*(1.-.6*squeeze);
        float tissue=exp(-pow(d/width,2.))*pow(saturate(.15+n*.9+fine*.35),1.4);
        float edge=exp(-pow((abs(d)-width*.75)/(.008+aa),2.));
        float crest=exp(-pow(d/(.012+aa),2.))*pow(saturate(sin(x*9.-Age*14.+Index)),3.);
        bands+=tissue; seams+=edge*.10*(.15+pow(n,2.))+crest*.50; haze+=exp(-pow(d/(width*1.7),2.))*.12;
    }
    float bounds=smoothstep(.04,.15,x)*(1.-smoothstep(.83,.98,x));
    rgb=(gold*(bands*1.4+haze)+warm*bands*.6+white*seams*.9)*bounds;
    alpha=(bands*.60+seams*.75+haze)*bounds;
} else if(design<2.5) {
    // C: a broad curved membrane with layered bright seams and a translucent interior.
    float yy=p.y;
    float halfWidth=.12+.15*(1.-yy*yy);
    float center=.28-.51*yy*yy;
    float dd=abs(p.x-center);
    float shape=(1.-smoothstep(halfWidth-aa,halfWidth+aa,dd))*(1.-smoothstep(.80,.98,abs(yy)));
    float edges=exp(-pow((dd-halfWidth)/(.009+aa),2.));
    float fold=exp(-pow((p.x-center+.03*sin(yy*5.+Age*8.))/.018,2.));
    float flow=pow(saturate(sin(yy*9.-Age*17.+n*3.+Index)),8.);
    float tissue=shape*(.17+n*.48+fine*.15);
    float erode=lerp(1.,smoothstep(st*3.4,st*3.4+.22,n),fired);
    float crest=pow(saturate(cos(yy*4.-Age*11.+Index)),5.);
    rgb=(gold*tissue*1.6+warm*shape*flow*.9+white*(edges*(.07+crest*.28)+fold*shape*.3))*erode;
    alpha=(tissue*.68+edges*.45+fold*shape*.3)*erode;
} else if(design<3.5) {
    // D: broad spiralling membranes with a dark hollow, rather than sinusoidal wire coils.
    float2 q=float2(p.x*.90,p.y*1.12);
    float rr=length(q); float ang=atan2(q.y,q.x);
    float mask=smoothstep(.19,.34,rr)*(1.-smoothstep(.74,.96,rr));
    float spiral=ang*3.-rr*12.+Age*20.+Index*2.1;
    float tongues=pow(saturate(cos(spiral+n*1.8)),3.);
    float crest=pow(saturate(cos(spiral+.35+n*1.8)),17.);
    float tissue=pow(saturate(.1+n*.95+fine*.25),1.4)*tongues*mask;
    float glints=crest*mask*pow(saturate(fine*.9+n*.6),3.);
    rgb=gold*tissue*2.0+warm*tongues*mask*.55+white*glints*.65;
    alpha=tissue*.75+tongues*mask*.12+glints*.4;
} else if(design<4.5) {
    // E: pointed, faceted shards with readable amber interior and a white edge.
    float halfWidth=.64*(1.-abs(p.y));
    float d=abs(p.x)-halfWidth;
    float shape=(1.-smoothstep(-aa,aa,d))*(1.-smoothstep(.88,1.,abs(p.y)));
    float edge=exp(-pow(d/(.010+aa),2.));
    float seam=exp(-pow((p.x-p.y*.16)/(.008+aa),2.))*shape;
    float face=lerp(.16,.45,step(0.,p.x))+.10*n;
    float glint=pow(saturate(sin(p.y*6.+Age*16.+Index*1.3)),8.);
    rgb=gold*face*shape+white*(edge*(.06+glint*.38)+seam*.15)+warm*shape*pow(fine,4.);
    alpha=shape*.42+edge*.60+seam*.35;
} else {
    // F revised opening: unconnected suspended light flakes gather, then bloom into stars at release.
    float arrival=smoothstep(Index*.010,Index*.010+.07,Age);
    float beat=exp(-pow((Age-(.13+Index*.012))/.028,2.));
    float diamond=abs(p.x)*1.7+abs(p.y);
    float flake=(1.-smoothstep(.27,.30+aa,diamond));
    float glint=exp(-pow(p.x/(.010+aa),2.)-pow(p.y/.48,2.))
               +exp(-pow(p.y/(.010+aa),2.)-pow(p.x/.48,2.));
    float halo=exp(-r*r/.11);
    float strength=.18+beat*.42+squeeze*.24+fired*.95*exp(-st*12.);
    float curl=pow(saturate(cos(a*2.+r*10.-Age*18.-Index)),6.)*exp(-pow((r-.48)/.15,2.));
    float dust=pow(saturate(fine*1.8-.65),5.)*exp(-r*r/.45);
    rgb=gold*(flake*.7+halo*.5+dust*.8)+white*glint*strength+warm*(flake*beat+curl*.65);
    alpha=(flake*.65+glint*strength*.7+halo*.15+curl*.4+dust*.5)*arrival;
    rgb*=arrival;
}
float bounds=smoothstep(0.,.025,UV.x)*(1.-smoothstep(.975,1.,UV.x))*smoothstep(0.,.025,UV.y)*(1.-smoothstep(.975,1.,UV.y));
float life=open*lerp(1.,1.-smoothstep(.06,.27,st),fired);
return float4(rgb*life*bounds,saturate(alpha)*life*bounds);
'''

RELEASE = r'''
float t=st;
float alive=fired*(1.-smoothstep(.11,.24,t));
float pulse=exp(-pow((t-.018)/.025,2.))+.65*exp(-pow((t-.068)/.023,2.));
float core=exp(-r*r/.013)*pulse;
float pieces=0.; float haze=0.;
for(int i=0;i<24;++i) {
    float h=frac(sin(float(i)*37.92)*1737.4);
    float ang=float(i)*2.39996;
    float2 axis=float2(cos(ang),sin(ang));
    float2 delta=p-axis*(.12+t*(2.1+h*2.8));
    float ax=dot(delta,axis);
    float side=abs(delta.x*axis.y-delta.y*axis.x);
    float shard=exp(-pow(ax/(.04+h*.075),2.)-pow(side/(.006+h*.008+aa),2.));
    pieces+=shard;
    haze+=shard*.3+exp(-dot(delta,delta)/.004)*.12;
}
float rim=0.;
if(design<.5) {
    rim=exp(-pow((r-(.16+t*3.2))/(.008+aa),2.))*exp(-t*15.);
    rim+=exp(-pow((r-(.10+max(0.,t-.045)*3.8))/(.013+aa),2.))*step(.045,t)*exp(-max(0.,t-.045)*18.);
} else if(design<1.5) {
    rim=pow(saturate(cos(a*3.+r*10.-t*26.)),8.)*exp(-pow((r-(.2+t*1.7))/.12,2.));
} else if(design<2.5) {
    rim=pow(saturate(cos(a*5.+Index)),30.)*exp(-pow((r-(.16+t*2.0))/.2,2.));
} else if(design<3.5) {
    rim=pow(saturate(cos(a*4.-r*13.+t*24.)),5.)*exp(-pow((r-(.15+t*2.1))/.17,2.))*(.3+n);
} else if(design<4.5) {
    rim=pow(saturate(cos(a*8.)),18.)*exp(-pow((r-(.10+t*2.9))/.19,2.));
} else {
    rim=(exp(-pow(p.x/.014,2.))+exp(-pow(p.y/.014,2.)))*exp(-r*r/.21)*pulse;
}
rgb=white*(core*1.8+pieces*.95)+warm*rim*.8+gold*haze;
alpha=core*.95+pieces*.75+rim*.55+haze*.30;
return float4(rgb*alive,saturate(alpha)*alive);
'''

STREAK = r'''
float x=UV.x;
float y=abs(p.y);
float taper=smoothstep(.01,.78,x)*(1.-smoothstep(.98,1.,x));
float shaft=exp(-pow(y/(.015+aa*.6),2.))*taper;
float head=(1.-smoothstep(.005,.015+aa,abs(y-(.98-x)*1.9)))*smoothstep(.82,.86,x)*(1.-smoothstep(.975,.99,x));
float blade=(1.-smoothstep((.98-x)*1.6,(.98-x)*1.6+aa,y))*smoothstep(.85,.9,x)*(1.-smoothstep(.975,.99,x));
float halo=exp(-y*y/.035)*taper;
float sparks=pow(saturate(sin(x*105.+design*2.)),30.)*exp(-pow((y-.20)/.08,2.))*taper;
float inner=exp(-pow((y-.055)/(.005+aa),2.))*taper;
rgb=white*(shaft*.90+head*.90)+warm*blade*.5+gold*(halo*.40+sparks*.55+inner*.18);
alpha=shaft*.85+head*.8+blade*.48+halo*.20+sparks*.55+inner*.20;
return float4(rgb,saturate(alpha));
'''

IMPACT = r'''
float t=max(Age,0.);
float flash=exp(-t*32.)+.55*exp(-pow((t-.055)/.017,2.));
float core=exp(-r*r/.012)*flash;
float pieces=0.; float sheen=0.;
for(int i=0;i<28;++i) {
    float h=frac(sin(float(i)*41.37+design)*1277.2);
    float ang=float(i)*2.39996;
    float2 dir=float2(cos(ang),sin(ang));
    float2 q=p-dir*(.04+t*(1.6+h*3.1));
    float axial=dot(q,dir);
    float lateral=abs(q.x*dir.y-q.y*dir.x);
    float len=.025+h*.1;
    float shard=exp(-pow(axial/len,2.)-pow(lateral/(.006+h*.009+aa),2.));
    if(design>3.5 && design<4.5) {
        float polygon=abs(axial)/len+lateral/.025;
        shard=(1.-smoothstep(.9,1.0+aa,polygon));
    }
    pieces+=shard;
    sheen+=exp(-dot(q,q)/(.001+h*.002))*.25;
}
float ring=exp(-pow((r-(.10+t*3.6))/(.008+aa),2.))*exp(-t*15.);
float flow=pow(saturate(cos(a*5.-r*12.+t*22.)),7.)*exp(-pow((r-(.12+t*2.1))/.20,2.))*(.3+n);
float ray=(exp(-pow(p.x/.009,2.))+exp(-pow(p.y/.009,2.)))*exp(-r*r/.22)*flash;
float ornament=design<.5?ring:design<1.5?flow:design<2.5?pieces*.35:design<3.5?flow*1.2:design<4.5?pieces*.25:ray;
float fade=1.-smoothstep(.10,.20,t);
rgb=white*(core*2.1+pieces*.9)+gold*sheen*1.4+warm*ornament*.8;
alpha=core*.95+pieces*.8+sheen*.3+ornament*.6;
return float4(rgb*fade,saturate(alpha)*fade);
'''


def author(out):
    out=Path(out)
    project=Path(__file__).resolve().parents[2]
    protected=list((project/'Content/TopDown/Characters/Sparrow/Materials').glob('M_SparrowSharp*.uasset'))
    hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before=hashes()
    texture=unreal.load_asset(NOISE)
    assert texture, NOISE
    lib=unreal.MaterialEditingLibrary
    rows=[]
    for style in DESIGNS:
        for part,body in [('Muzzle',MUZZLE),('Body',BODY),('Release',RELEASE),('Streak',STREAK),('Impact',IMPACT)]:
            path=f'{FOLDER}/M_SharpT{style}{part}'
            code=(COMMON+body).replace('DESIGN',str(float(style-6)))
            signature=hashlib.sha256(code.encode()).hexdigest()
            material=unreal.load_asset(path)
            reused=material and unreal.EditorAssetLibrary.get_metadata_tag(material,'SharpArtHash')==signature
            if not reused:
                if material is None:
                    folder,name=path.rsplit('/',1)
                    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
                assert material,path
                lib.delete_all_material_expressions(material)
                material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
                material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
                material.set_editor_property('two_sided',True)
                def node(kind,**props):
                    obj=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
                    for key,value in props.items():obj.set_editor_property(key,value)
                    return obj
                shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
                sources={'UV':node('TextureCoordinate'),'Flow':node('TextureObject',texture=texture)}
                for param,default in [('Age',0.),('ShotAge',100.),('Index',0.)]:
                    sources[param]=node('ScalarParameter',parameter_name=param,default_value=default)
                inputs=[]
                for name in sources:
                    pin=unreal.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
                shader.set_editor_property('inputs',inputs)
                for name,source in sources.items():assert lib.connect_material_expressions(source,'',shader,name)
                for prop,channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
                    mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
                    assert lib.connect_material_expressions(shader,'',mask,'')
                    assert lib.connect_material_property(mask,'',prop)
                lib.recompile_material(material)
                unreal.EditorAssetLibrary.set_metadata_tag(material,'SharpArtHash',signature)
                assert unreal.EditorAssetLibrary.save_loaded_asset(material,False),path
            rows.append({'style':style,'part':part,'path':path,'hash':signature,'reused':bool(reused)})
    assert before==hashes(),'Production S materials changed'
    result={'passed':True,'materials':rows,'designs':DESIGNS,'default_style':0,'production_materials_unchanged':True}
    (out/'sharp-art-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
