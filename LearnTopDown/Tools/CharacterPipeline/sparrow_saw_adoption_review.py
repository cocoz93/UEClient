"""Short actual A capture; the unchanged projectile owns its hit and speed."""
import json
import os
import unreal

def sequence(rig):
    rig['switch']('countess');yield .2
    rig['switch']('sparrow');yield .7
    rig['cmd']('CountessComboQA.FlushInput')
    rig['case']('A_vortex')
    targets=rig['layout']([(390,0),(700,350),(700,-350)])
    yield .2
    now=lambda:unreal.GameplayStatics.get_time_seconds(rig['world']())
    started=now();rig['use']('A',offset=(950,0))
    if os.environ.get('NEW_SKILLS_VIDEO')=='1':
        rig['STATE']['video_clip']={'case':'A','prefix':'A_vortex_video','cast_time':started,'frame_times':[]}
    row={'arrows':{},'surfaces':0,'materials_ready':False}
    times=[.20,.45,.70,1.,1.35,1.7,2.2]
    while now()-started<2.5:
        for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow):
            if arrow.get_owner()!=rig['pawn']():continue
            row['arrows'][arrow.get_name()]={'speed':arrow.get_flight_speed(),'hits':arrow.get_hit_count()}
            parts=[c for c in arrow.get_components_by_class(unreal.StaticMeshComponent) if 'SparrowSawVortex' in [str(t) for t in c.component_tags]]
            row['surfaces']=max(row['surfaces'],len(parts))
            row['materials_ready']|=len(parts)==4 and all(c.get_material(0) for c in parts)
        if times and now()-started>=times[0]:rig['capture']('A_vortex_t'+str(round(times.pop(0)*100)).zfill(3))
        yield 1./rig['FPS']
    rig['finish_video_clip']()
    row['damage']=[100-rig['health'](d) for d in targets]
    rig['check'](len(row['arrows'])==1 and all(v['speed']==160 for v in row['arrows'].values()),'A preserves one slow 160cm/s gear projectile')
    rig['check'](row['surfaces']==4 and row['materials_ready'],'A loads four hollow vortex surfaces')
    rig['check'](abs(row['damage'][0]-90)<.03 and max(row['damage'][1:])<.03,'A retains single 90 damage and no cosmetic damage')
    rig['recovered']()
    rig['switch']('countess');yield .2
    rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow),'A and its owned vortex clear on character switch')
    row['passed']=True
    (rig['OUT']/'saw-adoption-review.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
