"""Four opt-in S effect studies; never overwrite the installed S materials.

All studies retain the same parallel arrows and native damage. The per-ring
Index parameter only changes presentation. Sparrow.Sharp.Preview defaults to 0.
"""
import json
from pathlib import Path
import runpy


FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/SharpConcepts'
VERSION = 2
MUZZLE = r'''
float2 p=(UV-.5)*2.;
float d=length(p);
float delay=fmod(Index*3.,5.)*.005;
float age=max(0.,Age-delay);
float unfold=smoothstep(0.,.095,age);
float squeeze=smoothstep(.145,.345,Age);
float fired=1.-step(10.,ShotAge);
float fade=lerp(1.,1.-smoothstep(.008,.065,ShotAge),fired);
float radius=lerp(lerp(.12,.74,unfold),.20,squeeze);
float aa=max(length(fwidth(p))*.55,.0025);
// Radius depends only on time: no angular distortion, broken arcs or spirals.
float edge=abs(d-radius);
float rim=1.-smoothstep(.009,.009+aa,edge);
float halo=exp(-edge*edge/.0016);
float charge=smoothstep(.18,.36,Age)*(1.-fired);
float core=exp(-d*d/.0055)*charge;
float3 color=float3(5.2,4.9,4.0)*(rim+core*1.4)+float3(3.9,2.6,.85)*halo*.6;
float opacity=saturate(rim*.85+halo*.28+core);
float envelope=smoothstep(0.,.03,age)*fade;
return float4(color*envelope,opacity*envelope);
'''
RELEASE = r'''
const float style=STYLE;
float2 p=(UV-.5)*2.;
float d=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.55,.003);
float t=max(ShotAge,0.);
float active=(1.-step(.25,t))*step(0.,ShotAge);
float fired=1.-step(10.,ShotAge);
float3 color=0.;
float opacity=0.;
for(int i=0;i<2;++i) {
    float age=t-i*.050;
    float on=step(0.,age);
    float radius=lerp(.30,.88,pow(saturate(age/.085),.55));
    float envelope=on*(1.-smoothstep(.035,.20,age));
    float mask=1.;
    float width=.012;
    float edge=abs(d-radius);
    float rim=(1.-smoothstep(width,width+aa,edge))*mask;
    float halo=exp(-edge*edge/.0035)*mask;
    color+=envelope*(float3(7.0,6.4,4.6)*rim+float3(4.7,3.0,.9)*halo*.65);
    opacity+=envelope*(rim*.8+halo*.35);
}
float pulse=exp(-pow((t-.014)/.025,2.))+exp(-pow((t-.068)/.026,2.))*.7;
float core=exp(-d*d/.014)*pulse;
float glow=exp(-d*d/.075)*pulse;
float spokes=pow(saturate(cos(a*11.+.8)),32.)*smoothstep(.15,.26,d)
    *(1.-smoothstep(.32+t*1.8,.48+t*1.8,d))*(1.-smoothstep(.035,.14,t));
color+=float3(10.,9.4,7.2)*core+float3(4.4,3.0,1.1)*(glow*.7+spokes);
opacity+=core+glow*.4+spokes*.6;
float gather=smoothstep(.01,.08,Age)*(1.-smoothstep(.14,.35,Age))*(1.-fired);
float center=exp(-d*d/.013)*gather;
float mist=exp(-d*d/.06)*gather;
return float4(color*active+float3(7.,6.3,4.8)*center+float3(3.,2.3,.8)*mist*.4,
    saturate(opacity)*active+saturate(center+mist*.3));
'''


def author(out):
    helper=runpy.run_path(str(Path(__file__).with_name('sparrow_sharp_surface.py')))['_author_surface']
    rows=[]
    for style in range(1,5):
        for name,shader in [('Muzzle',MUZZLE),('Release',RELEASE)]:
            rows.append(helper(out,f'{FOLDER}/M_SharpC{style}{name}',shader.replace('STYLE',str(float(style))),indexed=True))
    result={'passed':True,'version':VERSION,'materials':rows,
            'saved_scope':[row['asset'] for row in rows],
            'production_materials_saved':False,'default_preview_style':0,
            'designs':{'C1':'mixed clean circles','C2':'two large overlapping circles','C3':'one large circle and four smaller circles','C4':'offset circle cluster'}}
    (Path(out)/'sharp-concepts-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
