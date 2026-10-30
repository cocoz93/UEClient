"""Thicken only the mapped outer smoke and torn trailing pieces of W."""
import json, os, traceback
from pathlib import Path
import unreal

OUT=Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE='/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseRing'
DEST='/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing'
report={'passed':False,'changes':[]}


def multiply(value,factor):
    if hasattr(value,'x'):
        f=factor if isinstance(factor,tuple) else (factor,)*3
        return unreal.Vector(value.x*f[0],value.y*f[1],value.z*f[2])
    return value*factor


def change(module_name,field,factor=None,offset=None):
    original=unreal.find_object(None,source.get_path_name()+':'+module_name)
    target=unreal.find_object(None,asset.get_path_name()+':'+module_name)
    assert original and target,(module_name,field)
    a=original.get_editor_property(field).get_editor_property('distribution')
    b=target.get_editor_property(field).get_editor_property('distribution')
    assert b.get_path_name().startswith(asset.get_path_name()+':')
    cls=a.get_class().get_name()
    row={'module':module_name,'field':field,'factor':factor,'offset':offset,'before':{},'after':{}}
    def transform(v):
        v=multiply(v,factor) if factor is not None else v
        return unreal.Vector(v.x+offset[0],v.y+offset[1],v.z+offset[2]) if offset else v
    fields=('Min','Max') if cls.endswith('Uniform') else ('Constant',)
    assert cls.endswith(('Uniform','Constant')),cls
    b.modify()
    for key in fields:
        value=a.get_editor_property(key)
        row['before'][key]=str(value)
        b.set_editor_property(key,transform(value))
        row['after'][key]=str(b.get_editor_property(key))
    report['changes'].append(row)


try:
    source=unreal.load_asset(SOURCE)
    asset=unreal.load_asset(DEST)
    assert source and asset
    asset.modify()
    # Native emitter graph: DarkPuffs_FL and SmokePuffs_FL share only these size/location modules.
    change('ParticleModuleSize_9','StartSize',(.72,.80,1.0))
    for name in ('ParticleModuleSpawn_11','ParticleModuleSpawn_0'):
        change(name,'Rate',1.8)
        original=unreal.find_object(None,source.get_path_name()+':'+name)
        target=unreal.find_object(None,asset.get_path_name()+':'+name)
        bursts=[b.copy() for b in original.get_editor_property('BurstList')]
        for burst in bursts:
            for field in ('Count','CountLow'):
                n=burst.get_editor_property(field)
                if n>0:burst.set_editor_property(field,round(n*1.8))
        target.set_editor_property('BurstList',bursts)
        report['changes'].append({'module':name,'field':'BurstList','factor':1.8})
    # Native graph: these size and alpha modules belong exclusively to the two torn mesh tails.
    change('ParticleModuleSize_22','StartSize',(1.25,1.35,1.20))
    change('ParticleModuleSize_27','StartSize',(1.20,1.35,1.20))
    change('ParticleModuleColor_24','StartAlpha',1.20)
    change('ParticleModuleColor_28','StartAlpha',1.20)
    unreal.SystemLibrary.execute_console_command(None,'CharacterPipeline.OutputDirectory '+str(OUT))
    unreal.SystemLibrary.execute_console_command(None,'CountessFXQA.WOuterSmoke')
    adaptation=json.loads((OUT/'w-outer-smoke-adaptation.json').read_text(encoding='utf-8'))
    assert adaptation['adapted_emitters']==2
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True)
    before=sorted(str(v) for v in registry.get_dependencies(SOURCE,options))
    after=sorted(str(v) for v in registry.get_dependencies(DEST,options))
    assert before==after,(before,after)
    report.update(passed=True,source=SOURCE,destination=DEST,dependencies_preserved=after,outer_smoke=adaptation,
                  interior_sparks_droplets_and_hit_effect_untouched=True)
except Exception:report['error']=traceback.format_exc()
(OUT/'assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
