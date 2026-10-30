"""Form-only E/S/D/F materials. Normal authored materials remain untouched."""
import ast,hashlib,json,runpy
from pathlib import Path
import unreal

FOLDER='/Game/TopDown/Characters/Sparrow/Materials/AscendedArsenal20261026'
NOISE='/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'

def author(out):
    out=Path(out);folder=Path(__file__).parent
    sharp=runpy.run_path(str(folder/'sparrow_sharp_art_studies.py'))
    gather=runpy.run_path(str(folder/'sparrow_arsenal_adoption.py'))
    lib=unreal.MaterialEditingLibrary; rows=[]
    def build(name,code,params,texture_path=NOISE,texture_input='Flow'):
        path=FOLDER+'/'+name
        material=unreal.load_asset(path)
        digest=hashlib.sha256((code+(texture_path if name.startswith('M_GatherCrystal') else '')).encode()).hexdigest()
        if not material or unreal.EditorAssetLibrary.get_metadata_tag(material,'AscendedHash')!=digest:
            if not material:
                material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,FOLDER,unreal.Material,unreal.MaterialFactoryNew())
            assert material,path
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided',True)
            def node(kind,**props):
                obj=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
                for key,val in props.items():obj.set_editor_property(key,val)
                return obj
            shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            sources={'UV':node('TextureCoordinate'),texture_input:node('TextureObject',texture=unreal.load_asset(texture_path))}
            if name.startswith('M_GatherCrystal'):
                sources['Clock']=node('Time')
                if name in ('M_GatherCrystalFold','M_GatherCrystalArrow','M_GatherCrystalSolid'):
                    sources['Facing']=node('Fresnel',exponent=1.0,base_reflect_fraction=0.0)
            for name,value in params:sources[name]=node('ScalarParameter',parameter_name=name,default_value=value)
            pins=[]
            for name in sources:
                pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
            shader.set_editor_property('inputs',pins)
            for name,source in sources.items():assert lib.connect_material_expressions(source,'',shader,name)
            for prop,rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(1,1,1,0)),(unreal.MaterialProperty.MP_OPACITY,(0,0,0,1))]:
                mask=node('ComponentMask',r=bool(rgba[0]),g=bool(rgba[1]),b=bool(rgba[2]),a=bool(rgba[3]))
                assert lib.connect_material_expressions(shader,'',mask,'')
                assert lib.connect_material_property(mask,'',prop)
            lib.recompile_material(material)
            unreal.EditorAssetLibrary.set_metadata_tag(material,'AscendedHash',digest)
            assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
        rows.append({'path':path,'hash':digest})
    for style in (6,10):
        for part in ('Muzzle','Body','Release','Streak','Impact'):
            code=(sharp['COMMON']+sharp[part.upper()]).replace('DESIGN',str(float(style-6)))
            if part=='Muzzle':
                code=code.replace('rgb=white*(ring*','rgb=gold*flecks*.8+warm*inner*.7+white*(ring*')
                code=code.replace('second*.08','second*.20').replace('inner*1.3','inner*1.7')
            elif part=='Body':
                code=code.replace('i<45','i<64')
                code=code.replace('rgb=warm*sparks*1.2;','float arcs=pow(saturate(cos(a*3.-r*12.+Age*20.+Index)),9.)*exp(-pow((r-.68)/.10,2.))*(.2+n);\nrgb=warm*sparks*1.25+gold*arcs*1.6;')
                code=code.replace('alpha=sparks*.8;','alpha=sparks*.8+arcs*.6;')
                code=code.replace('seam*.15','seam*.26').replace('warm*shape*pow(fine,4.)','warm*shape*(pow(fine,4.)+pow(saturate(sin(p.y*15.-Age*24.+Index)),12.)*.45)')
            elif part in ('Release','Impact'):
                code=code.replace('i<24','i<36').replace('i<28','i<42').replace('gold*haze','gold*haze*1.2')
            elif part=='Streak':
                code=code.replace('sparks*.55','sparks*.80').replace('inner*.18','inner*.42')
            build(f'M_SharpT{style}{part}',code,[('Age',0.),('ShotAge',100.),('Index',0.)])
    for part,body in [('Ribbon',gather['RIBBON']),('Release',gather['RELEASE']),
                      ('CrystalFold',gather['CRYSTAL_FOLD']),('CrystalFragment',gather['CRYSTAL_FRAGMENT']),
                      ('CrystalArrow',gather['CRYSTAL_ARROW']),('CrystalSolid',gather['CRYSTAL_SOLID']),('CrystalRelease',gather['CRYSTAL_RELEASE']),
                      ('CrystalImpact',gather['CRYSTAL_IMPACT'])]:
        code=gather['COMMON']+(gather['PLASMA_DENSITY'] if part in ('CrystalFold','CrystalFragment','CrystalArrow','CrystalSolid') else '')+body
        if part=='Ribbon':
            code=code.replace('float fade=open*','tissue+=exp(-pow((abs(d)-width*1.5)/.034,2.))*taper*(.2+fine*.6);\nfloat fade=open*')
        elif part=='Release':
            code=code.replace('i<22','i<34').replace('gold*sheet*1.2','gold*sheet*1.55')
        elif part=='CrystalArrow':
            code=code.replace('split*.55','split*.65').replace('body*.58','body*.62')
        elif part=='CrystalFragment':
            code=code.replace('current*1.25','current*1.40').replace('pulse*.31','pulse*.35')
        elif part=='CrystalImpact':
            code=code.replace('i<18','i<24').replace('gold*shear*1.8','gold*shear*2.3')
        build('M_Gather'+part,code,[('Age',0.),('Progress',1. if part.startswith('Crystal') else 0.),
                                  ('ShotAge',100.),('Index',0.),('Crystal',0.),('Envelope',1.)],
              texture_path=gather['CRYSTAL_FLOW'] if part.startswith('Crystal') else NOISE)
    tree=ast.parse((folder/'sparrow_holy_bow_surface.py').read_text(encoding='utf-8-sig'))
    code=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('\nstruct FBow'))
    code=code.replace('j<=3','j<=4').replace('f<5','f<6').replace('.38+f*.13','.36+f*.11')
    # 펼침의 흰 윤곽만 밝히면 평소와 구분되지 않는다. 금색 면과 내부 음각 대비를 올린다.
    code=code.replace('float3 gold=float3(2.1,1.05,.18);','float3 gold=float3(3.2,1.35,.12);')
    code=code.replace('body*(.32+veins*.33)*(1.-inlay*.72)','body*(.60+veins*.55)*(1.-inlay*.82)')
    code=code.replace('rim*.68','rim*.50').replace('ornament*(.24+grain*.20)','ornament*(.43+grain*.34)')
    code=code.replace('return float4(color*(1.+Pulse*.35),alpha*Envelope*Open);',
        'float surge=pow(saturate(sin(nearest*27.-Age*30.+grain*2.)),9.);\ncolor+=gold*(rim+ornamentRim+filigree)*surge*1.2+white*runner*.2;\nreturn float4(color*(1.+Pulse*.4),alpha*Envelope*Open);')
    build('M_HolyBow',code,[('Age',0.),('Open',1.),('Draw',1.),('Pulse',0.),('Envelope',1.)],
          '/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless','Detail')
    saw=runpy.run_path(str(folder/'sparrow_saw_vortex_materials.py'))['author'](out)
    qwr=runpy.run_path(str(folder/'sparrow_ascended_shot_materials.py'))['author'](out)
    result={'passed':saw['passed'] and qwr['passed'],'materials':rows,'saw':saw,'qwr':qwr}
    (out/'ascended-arsenal-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
