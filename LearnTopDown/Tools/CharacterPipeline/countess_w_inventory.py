import json,os,traceback
from pathlib import Path
import unreal
out=Path(os.environ['SPARROW_QA_OUTPUT']);r={'passed':False,'assets':[]}
base='/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/'
try:
    for name in ('P_Countess_BladeSiphon_RingFX','P_Countess_BladeSiphon_Trails','p_Countess_BladeSiphon_HitFX'):
        asset=unreal.load_asset(base+name);row={'asset':asset.get_path_name(),'objects':[]};prefix=asset.get_path_name()+':'
        for obj in unreal.ObjectIterator(unreal.Object):
            if not unreal.SystemLibrary.get_path_name(obj).startswith(prefix):continue
            cls=obj.get_class().get_name()
            if not any(v in cls for v in ('ParticleModule','ParticleLODLevel','ParticleEmitter')):continue
            entry={'class':cls,'path':unreal.SystemLibrary.get_path_name(obj),'properties':{}}
            for prop in ('emitter_name','material','emitter_duration','emitter_delay','rate','rate_scale','burst_list','start_size','start_lifetime','color_over_life','alpha_over_life','color_scale_over_life','alpha_scale_over_life','modules','required_module','spawn_module','EmitterName','Material','EmitterDuration','EmitterDelay','BurstList','StartSize','StartLifetime','ColorOverLife','AlphaOverLife','ColorScaleOverLife','AlphaScaleOverLife','Modules','RequiredModule','SpawnModule'):
                try:
                    value=obj.get_editor_property(prop);item={'value':str(value)[:700]}
                    if hasattr(value,'get_editor_property'):
                        dist=value.get_editor_property('distribution')
                        if dist:
                            item['distribution']=dist.get_path_name();item['class']=dist.get_class().get_name()
                            for field in ('constant','min','max','constant_curve','ConstantCurve','Min','Max'):
                                try:item[field]=str(dist.get_editor_property(field))[:1400]
                                except Exception:pass
                    entry['properties'][prop]=item
                except Exception:pass
            row['objects'].append(entry)
        r['assets'].append(row)
    r['passed']=True
except Exception:r['error']=traceback.format_exc()
(out/'inventory.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
