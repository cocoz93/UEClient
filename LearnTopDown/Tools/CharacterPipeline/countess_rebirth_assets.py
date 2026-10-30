"""Owned volume meshes and ink materials for the ten-skill Countess revision."""
import hashlib
import json
import math
from pathlib import Path
import runpy
import unreal

ROOT='/Game/TopDown/Characters/Countess/Rebirth20261028'
FLOW='/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
CUT=r'''
float u=UV.x,v=UV.y;
float noise=Texture2DSample(Flow,FlowSampler,float2(u*2.3-Age*1.7,v*2.0+Seed)).g;
float grain=Texture2DSample(Flow,FlowSampler,float2(u*7.+Seed,v*5.-Age*.7)).r;
float edge=pow(saturate(1.-abs(v-.5)*2.),.65);
float spine=exp(-pow((v-.49)/.065,2.));
float ends=pow(saturate(sin(u*3.141592)),.35);
float alpha=edge*ends*(.35+.65*smoothstep(.02,.55,noise*.75+grain*.6))*Alpha;
float3 deep=float3(.08,.001,.006), red=float3(2.0,.008,.035), hot=float3(4.,.16,.11);
float3 rgb=lerp(deep,red,saturate(.35+noise*.65))+hot*spine*.20;
return float4(rgb,alpha);
'''
SHARD=r'''
float3 n=normalize(Normal);
float noise=Texture2DSample(Flow,FlowSampler,float2(UV.x*2.-Age*.08,UV.y*3.+Seed)).g;
float light=.25+.75*pow(abs(dot(n,normalize(float3(.3,-.6,.8)))),2.);
float ridge=pow(abs(cos(UV.y*6.283185)),24.);
float veins=pow(saturate(sin(UV.x*53.+noise*13.+UV.y*5.)),24.);
float3 rgb=float3(.11,.032,.054)*light+float3(1.25,.006,.023)*(ridge*.28+veins*.12);
rgb+=float3(.16,.09,.12)*pow(light,4.);
return float4(rgb,Alpha);
'''

def author(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    folder=Path(__file__).resolve().parent
    # Reuse the established graph and OBJ import routes; the target root is private.
    helper=runpy.run_path(str(folder/'sparrow_harmony_author.py'))
    create=helper['material'];create.__globals__['ROOT']=ROOT;create.__globals__['FLOW']=FLOW
    mats={'M_BloodCut':create('M_BloodCut',CUT),'M_ObsidianVein':create('M_ObsidianVein',SHARD)}
    importer=runpy.run_path(str(folder/'countess_ruin_surface.py'))['_import_mesh']
    rows=[]
    for name,kind in (('SM_TwistedCut','cut'),('SM_HookedFang','fang')):
        vertices=[];uv=[];faces=[];steps=40;sides=8
        for i in range(steps+1):
            t=i/steps
            if kind=='cut':
                angle=(t-.5)*2.7;center=(math.sin(angle)*100.,(math.cos(angle)-.22)*77.,math.sin(t*math.pi)*8.)
                tangent=(math.cos(angle),-math.sin(angle),0.)
                width=max(.015,math.sin(t*math.pi)**.55*(.18+.82*t)*24.)
                depth=max(.02,math.sin(t*math.pi)*2.4)
            else:
                center=(math.sin(t*math.pi)*24.+12.*t*t,math.sin(t*math.pi)*8.,t*100.)
                tangent=(1.,0.,0.);width=max(.015,math.sin(t*math.pi)**.6*(1.-t*.55)*15.)
                depth=width*.55
            for j in range(sides):
                a=j*math.tau/sides
                if kind=='cut':p=(center[0]-tangent[1]*math.cos(a)*width,center[1]+tangent[0]*math.cos(a)*width,center[2]+math.sin(a)*depth)
                else:p=(center[0]+math.cos(a)*width,center[1]+math.sin(a)*depth,center[2])
                vertices.append(p);uv.append((t,(1.-math.cos(a))*.5 if kind=='cut' else j/sides))
        for i in range(steps):
            for j in range(sides):
                a=i*sides+j+1;b=i*sides+(j+1)%sides+1;c=b+sides;d=a+sides
                faces.extend(((a,b,c),(a,c,d)))
        path=ROOT+'/'+name;digest=hashlib.sha256(repr((vertices,uv,faces)).encode()).hexdigest();mesh=unreal.load_asset(path)
        if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'CountessRebirthShape')==digest:rows.append({'path':path,'reused':True});continue
        extent=[max(p[i] for p in vertices)-min(p[i] for p in vertices) for i in range(3)]
        rows.append(importer(output,mats['M_BloodCut' if kind=='cut' else 'M_ObsidianVein'],path,vertices,uv,faces,
            'CountessRebirthShape',digest,(extent[0],extent[1]-.1,extent[1]+.1,extent[2]-.1,extent[2]+.1),len(faces)-16,24))
    result={'passed':True,'meshes':rows,'materials':[m.get_path_name() for m in mats.values()],'source_packs_saved':False}
    (output/'rebirth-assets.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
