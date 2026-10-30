"""Transient cloth A/B measurement in the original field; never saves assets."""
import json, os, sys
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
qa=Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
job=qa/'job.json'
job.write_text(json.dumps(dict(profile=str(root/'Tools/CharacterPipeline/Profiles/sparrow.json'), baseline=str(root/'Saved/QA/CharacterPipeline/baseline-20261015-pose-final/baseline.json'), output=str(qa),fps=int(os.environ['SPARROW_QA_FPS']))),encoding='utf-8')
os.environ['CHARACTER_PIPELINE_JOB']=str(job)
sys.path[:0]=[str(root/'Tools/CharacterPipeline'),str(root/'Tools/CharacterPipeline/Suites')]
from context import fps
from sparrow_runtime import Runner
from character_switch import SwitchRunner
from sparrow_pose import close_capture

def trial(hero,mode):
 def run(rig):
    # Recreate only through the actual number-key selection to reset each transient variant.
    current='sparrow' if 'Sparrow' in rig.pawn.get_class().get_name() else 'countess'
    rig.controller.stop_movement()
    rig.movement.stop_movement_immediately()
    for chosen in ('countess' if current=='sparrow' else 'sparrow',hero):
        key='Two' if chosen=='sparrow' else 'One'
        rig.key('Press',key)
        yield 1.0/fps
        rig.key('Release',key)
        yield 1.0/fps
        rig.snapshot()
    rig.pawn.set_actor_location(rig.runner.test_origin,False,True)
    rig.mesh.force_cloth_next_update_teleport_and_reset()
    yield .7
    rig.origin=rig.pawn.get_actor_location()
    assets=rig.mesh.get_editor_property('skeletal_mesh_asset').get_editor_property('mesh_clothing_assets')
    rig.data['cloth_assets']=[a.get_path_name() for a in assets]
    simulation=rig.mesh.get_clothing_simulation_interactor()
    rig.data['simulation_class']=simulation.get_class().get_name() if simulation else None
    if mode!='baseline':
        rig.mesh.set_editor_property('teleport_rotation_threshold',45.0)
    if mode in ('inertia','drive'):
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.ClothTune '+('2' if mode=='drive' else '1'))
    yield .7
    yield from close_capture(rig,hero+'-'+mode+'-idle')
    origin=rig.pawn.get_actor_location()
    goal=rig.ground(0,800)
    yield from rig.click('Right',goal)
    rig.assert_cursor_goal(goal)
    yield .5
    yield from close_capture(rig,hero+'-'+mode+'-turn-run')
    yield .35
    yield from close_capture(rig,hero+'-'+mode+'-settled-run')
    yield 1.5
    yield .2
    rig.origin=rig.pawn.get_actor_location()
    target=rig.dummy(0,450 if hero=='sparrow' else 140)
    rig.aim_target(target)
    yield from rig.click('Left',target.get_actor_location())
    yield .05
    yield from close_capture(rig,hero+'-'+mode+'-attack')
    yield rig.idle()
    yield .5
    for offset in ((-400,0),(0,-400),(400,0),(0,400)):
        goal=rig.ground_absolute(origin.x+offset[0],origin.y+offset[1])
        yield from rig.click('Right',goal)
        yield .45
    rig.controller.stop_movement()
    rig.movement.stop_movement_immediately()
    yield 1.5
    yield from close_capture(rig,hero+'-'+mode+'-recovery')
    rows=[c for s in rig.trace for c in s['cloth']]
    rig.data['cloth_summary']=dict(samples=len(rows),max_above_head_cm=max((r['max_above_head_cm'] for r in rows),default=0),p95_peak_above_head_cm=max((r['p95_above_head_cm'] for r in rows),default=0),max_radius_cm=max((r['max_radius_cm'] for r in rows),default=0))
 return run
class ClothRunner(SwitchRunner):
 def tick(self,delta):
    super().tick(delta)
    if self.rig and not hasattr(self,'test_origin'):
        self.test_origin=self.rig.pawn.get_actor_location()
 def __init__(self):
    Runner.__init__(self,'cloth_diagnostic',[(h+'_'+m,trial(h,m)) for h,m in (('sparrow','inertia'),('sparrow','drive'),('countess','baseline'))])
    self.report.update(asset_saves=False,transient_cloth_tuning=True)
runtime=ClothRunner()
runtime.start()
