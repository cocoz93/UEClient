"""Strengthen private copies of the original textured W particles."""
import json,os,traceback
from pathlib import Path
import unreal

OUT=Path(os.environ['SPARROW_QA_OUTPUT'])
ROOT=Path(unreal.Paths.project_dir()).resolve()
SOURCE='/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/'
DEST='/Game/TopDown/Characters/Countess/FX/'
report={'passed':False,'assets':[],'materials_meshes_textures_replaced':False}


def vector_scale(value,factor):
    return unreal.Vector(value.x*factor,value.y*factor,value.z*factor)


def scaled(value,factor):
    return vector_scale(value,factor) if hasattr(value,'x') else value*factor


def scale_distribution(module,property_name,factor,seen,changes):
    try:
        raw=module.get_editor_property(property_name)
    except Exception:
        return
    distribution=raw.get_editor_property('distribution')
    if not distribution:return
    key=distribution.get_path_name()
    if key in seen:return
    seen.add(key)
    if not key.startswith(COPY_ROOT+':'):raise RuntimeError('Refuse to edit a distribution outside the private W copy')
    original=unreal.find_object(None,key.replace(COPY_ROOT,ORIGINAL_ROOT,1))
    if not original:raise RuntimeError('Original W distribution is missing')
    cls=distribution.get_class().get_name()
    if 'Parameter' in cls: return
    distribution.modify()
    before={};after={}
    if cls.endswith('Constant'):
        before['Constant']=str(original.get_editor_property('Constant'))
        distribution.set_editor_property('Constant',scaled(original.get_editor_property('Constant'),factor))
        after['Constant']=str(distribution.get_editor_property('Constant'))
    elif cls.endswith('Uniform'):
        for field in ('Min','Max'):
            value=original.get_editor_property(field)
            before[field]=str(value)
            distribution.set_editor_property(field,scaled(value,factor))
            after[field]=str(distribution.get_editor_property(field))
    elif cls.endswith('ConstantCurve'):
        curve=original.get_editor_property('ConstantCurve').copy()
        before['curve']=str(curve)
        points=[point.copy() for point in curve.get_editor_property('Points')]
        for point in points:
            for field in ('OutVal','ArriveTangent','LeaveTangent'):
                point.set_editor_property(field,scaled(point.get_editor_property(field),factor))
        curve.set_editor_property('Points',points)
        distribution.set_editor_property('ConstantCurve',curve)
        after['curve']=str(distribution.get_editor_property('ConstantCurve'))
    else:
        raise RuntimeError('Unreviewed W distribution '+cls+' '+property_name)
    changes.append({'module':module.get_name(),'property':property_name,'distribution_class':cls,
                    'factor':factor,'before':before,'after':after})


try:
    for original,name,density in (
        ('P_Countess_BladeSiphon_RingFX','P_CountessW_DenseRing',2.4),
        ('P_Countess_BladeSiphon_Trails','P_CountessW_DenseTrails',1.8),
        ('p_Countess_BladeSiphon_HitFX','P_CountessW_DenseHit',1.6)):
        target=DEST+name
        source_asset=unreal.load_asset(SOURCE+original)
        ORIGINAL_ROOT=source_asset.get_path_name()
        asset=unreal.load_asset(target) if unreal.EditorAssetLibrary.does_asset_exist(target) else unreal.EditorAssetLibrary.duplicate_asset(SOURCE+original,target)
        if not asset:raise RuntimeError('W particle copy failed')
        COPY_ROOT=asset.get_path_name()
        asset.modify();prefix=asset.get_path_name()+':'
        objects=[obj for obj in unreal.ObjectIterator(unreal.Object)
                 if unreal.SystemLibrary.get_path_name(obj).startswith(prefix)]
        changes=[];seen=set()
        for obj in objects:
            cls=obj.get_class().get_name()
            if cls=='ParticleModuleSpawn':
                scale_distribution(obj,'Rate',density,seen,changes)
                source_module=unreal.find_object(None,obj.get_path_name().replace(COPY_ROOT,ORIGINAL_ROOT,1))
                if not source_module:raise RuntimeError('Original W spawn module is missing')
                bursts=[burst.copy() for burst in source_module.get_editor_property('BurstList')]
                for burst in bursts:
                    for field in ('Count','CountLow'):
                        value=burst.get_editor_property(field)
                        if value>0:burst.set_editor_property(field,min(512,max(value,round(value*density))))
                obj.set_editor_property('BurstList',bursts)
                changes.append({'module':obj.get_name(),'property':'BurstList','factor':density})
            elif cls=='ParticleModuleSize':
                scale_distribution(obj,'StartSize',1.18,seen,changes)
            elif cls=='ParticleModuleLifetime':
                scale_distribution(obj,'Lifetime',1.20,seen,changes)
            elif cls=='ParticleModuleColorOverLife':
                scale_distribution(obj,'ColorOverLife',1.25,seen,changes)
                scale_distribution(obj,'AlphaOverLife',1.28,seen,changes)
            elif cls=='ParticleModuleColorScaleOverLife':
                scale_distribution(obj,'ColorScaleOverLife',1.25,seen,changes)
                scale_distribution(obj,'AlphaScaleOverLife',1.28,seen,changes)
        if not changes:raise RuntimeError('W copy has no authored module changes')
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('W save failed')
        registry=unreal.AssetRegistryHelpers.get_asset_registry()
        options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True)
        original_dependencies=sorted(str(v) for v in registry.get_dependencies(SOURCE+original,options))
        copy_dependencies=sorted(str(v) for v in registry.get_dependencies(target,options))
        # Exact direct dependencies preserve the authored material, mesh and texture references.
        if original_dependencies != copy_dependencies:
            raise RuntimeError('Private W asset references differ from the original: '+str((original_dependencies,copy_dependencies)))
        report['assets'].append({'dependencies_preserved':copy_dependencies,'source':SOURCE+original,'destination':target,'changes':changes})
    report['passed']=len(report['assets'])==3
except Exception:report['error']=traceback.format_exc()
finally:
    (OUT/'assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
