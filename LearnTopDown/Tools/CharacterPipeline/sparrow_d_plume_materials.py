"""D6 feather skin, fitted to six live physical-bow spline sections.

author(output) is called by the parent's serialized UE editor session. The
renaissance D0/D5 projectile and path-feather assets are never modified here.
"""
import hashlib
import json
import math
from pathlib import Path
import runpy

import unreal

ROOT = '/Game/TopDown/Characters/Sparrow/FX/PlumeBow20261028'

SURFACE = r'''
// Each bound section is one readable quill, not a miniaturized half-bow.
// UV bands encode six quills while the source image still supplies their
// carved bright edges and amber channels. The physical limb is unchanged.
float piece=floor(UV.y*.5);
float section=fmod(piece,3.);
float t=saturate(UV.x),v=saturate((UV.y-piece*2.-.1)/.8);
float2 root=float2(.720,.600);
float2 tip=float2(.975,.165);
float2 sampleUV=lerp(root,tip,t)+float2(.016,.024)*(v-.5)*2.*sin(t*3.14159265);
if (piece<3.) sampleUV.x=1.-sampleUV.x;
float4 art=Texture2DSample(BowArt,BowArtSampler,sampleUV);
float side=(section+t)/3.;
float flow=Texture2DSample(Flow,FlowSampler,float2(side*3.8-Age*1.25,v*5.0)).r;
float fine=Texture2DSample(Flow,FlowSampler,float2(side*7.4-Age*1.85,v*10.0)).g;
// The source bow has transparent gaps through the sampled region. Those gaps
// must not cut the already-authored quill's root/tip a second time. Treat the
// raster as inset colour detail and let the actual quill mesh own its coverage.
// Transparent source RGB also contains red fringe pixels: replace, never glow.
float sourceCoverage=smoothstep(.25,.90,art.a);
float3 insetBody=float3(.32,.145,.027)*(.66+flow*.34);
float3 surface=lerp(insetBody,art.rgb,sourceCoverage);
float l=dot(surface,float3(.30,.59,.11));
float ridge=smoothstep(.40,.90,l);
float inset=smoothstep(.025,.11,l)*(1.-smoothstep(.25,.55,l));
float reveal=1.-smoothstep(Open-.025,Open+.055,side);
float crest=exp(-pow((side-Open)/.032,2.))*(1.-smoothstep(.88,1.,Open));
float3 gold=float3(1.90,.86,.12),ivory=float3(2.05,1.70,.95);
float rachis=exp(-pow((v-.5)/.055,2.))*sin(t*3.14159265);
float3 rgb=surface*.59+gold*(pow(flow,2.4)*(.25+fine*.75)*inset*.28)
    +ivory*(ridge*.045+crest*.16+Pulse*ridge*.12);
rgb+=ivory*rachis*.065;
float endFade=smoothstep(0.,.055,t)*(1.-smoothstep(.97,1.,t));
float edgeCoverage=1.-smoothstep(.96,1.,abs(v-.5)*2.);
return float4(rgb,(.79+ridge*.07)*edgeCoverage*reveal*Envelope*endFade);
'''


def geometry(side, section):
    """One overlapping quill per real-limb section, three on each side.

    X 0..100 is the bone-bound segment; the tapered end overlaps the next
    segment by 32%. Y at the tip is only 12/16/18 cm outside the existing bow.
    UV bands identify the quill and use one selected long source feather.
    """
    vertices,uvs,faces=[],[],[]
    rows=10
    left_cuts=(.28,.46,.64,.80)
    right_cuts=(.34,.52,.70)
    # Give each short V-cut an explicit middle and shoulders, so importing the
    # mesh cannot smooth its silhouette into another uninterrupted gold strip.
    samples=sorted(set([i/24. for i in range(25)]+
                       [c+d for c in left_cuts+right_cuts for d in (-.036,0.,.036)]))
    for t in samples:
        center=(12.,16.,18.)[section]*t**1.2
        width=.12+11.6*math.sin(math.pi*t)**.65*(1.-t*.20)
        left_cut=max(max(0.,1.-abs(t-c)/.036)*3.1 for c in left_cuts)
        right_cut=max(max(0.,1.-abs(t-c)/.036)*2.7 for c in right_cuts)
        for j in range(rows+1):
            v=j/rows
            edge_width=width-(left_cut if v<.5 else right_cut)
            vertices.append((t*132.,center+(v-.5)*2.*edge_width,
                             .65+math.sin(math.pi*t)*math.sin(math.pi*v)*1.6))
            # Preserve the six shader bands through UE's OBJ/FBX V flip.
            uvs.append((t,1.-((side*3+section)*2.+.1+v*.8)))
    stride=rows+1
    for i in range(len(samples)-1):
        for j in range(rows):
            a=i*stride+j+1
            faces.extend(((a,a+1,a+1+stride),(a,a+1+stride,a+stride)))
    return vertices,uvs,faces


def author(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    helper=runpy.run_path(str(Path(__file__).with_name('sparrow_e_design_materials.py')))
    plume,image=helper['_plume_art']()
    flow=unreal.load_asset(helper['FLOW']);assert flow,helper['FLOW']
    art=unreal.load_asset(helper['ART']);assert art,helper['ART']
    material,material_row=helper['_material']('M_D6FeatherBow',SURFACE,flow,art,plume,folder=ROOT,spline=True)
    importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    meshes=[]
    for side in range(2):
        for section in range(3):
            name='SM_D6Feather_%d_%d'%(side,section)
            path=ROOT+'/'+name
            vertices,uvs,faces=geometry(side,section)
            digest=hashlib.sha256(repr((vertices,uvs,faces)).encode()).hexdigest()
            mesh=unreal.load_asset(path)
            if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'D6PlumeMesh')==digest:
                row={'path':path,'reused':True,'triangles':mesh.get_num_triangles(0)}
            else:
                sizes=[max(p[a] for p in vertices)-min(p[a] for p in vertices) for a in range(3)]
                bounds=(sizes[0],sizes[1]-.1,sizes[1]+.1,sizes[2]-.1,sizes[2]+.1)
                row=importer(output,material,path,vertices,uvs,faces,'D6PlumeMesh',digest,bounds,len(faces)-8,len(vertices)//11-1)
                source=Path(row['source_obj']).resolve()
                assert source.parent==output.resolve() and source.name==name+'.obj'
                source.unlink();row['source_obj_removed']=True
                mesh=unreal.load_asset(path)
            # These are owned reimports. FBX can retain an obsolete section
            # slot despite the mesh now containing exactly one material.
            subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            slot_rows=[];slot_changed=False
            for lod in range(subsystem.get_lod_count(mesh)):
                for section_index in range(mesh.get_num_sections(lod)):
                    before=subsystem.get_lod_material_slot(mesh,lod,section_index)
                    if before!=0:
                        subsystem.set_lod_material_slot(mesh,0,lod,section_index)
                        slot_changed=True
                    after=subsystem.get_lod_material_slot(mesh,lod,section_index)
                    assert after==0,(path,lod,section_index,after)
                    slot_rows.append({'lod':lod,'section':section_index,'before':before,'after':after})
            if slot_changed:
                assert unreal.EditorAssetLibrary.save_loaded_asset(mesh,False),path
            row['material_sections']=slot_rows
            imported=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)[3]
            expected=(min(p[0] for p in uvs),max(p[0] for p in uvs),
                      min(1.-p[1] for p in uvs),max(1.-p[1] for p in uvs))
            actual=(min(p.x for p in imported),max(p.x for p in imported),min(p.y for p in imported),max(p.y for p in imported))
            assert all(abs(a-b)<.01 for a,b in zip(expected,actual)),(name,expected,actual)
            row['uv_bounds']=actual
            row['section']=[side,section]
            row['outward_tip_cm']=(12.,16.,18.)[section]
            row['body_half_width_cm']=10.6
            row['short_edge_cuts']=[4,3]
            meshes.append(row)
    result={'passed':True,'selector':'Sparrow.BowMuzzle.Style 6','materials':[material_row],
            'meshes':meshes,'images':[image],
            'binding':'2 limbs x 3 overlapping quills, roots on the existing bow bones; tips 12/16/18cm outward',
            'baseline':'renaissance D5_r2 (craft D0): .22s live release tail, .72s fade',
            'source_assets_changed':False,'visual_acceptance':'pending actual game render'}
    (output/'d6-plume-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
