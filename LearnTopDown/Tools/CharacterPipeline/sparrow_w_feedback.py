"""Author the owned W air material and check release, cancellation and owner cleanup in one PIE."""
import json
import math
import os
from pathlib import Path
import sys
import traceback
import types
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
job={'output':str(OUT),'profile':str(ROOT/'Tools/CharacterPipeline/Profiles/sparrow.json'),
     'fps':60,'baseline':str(OUT.parent/'target-baseline.json')}
(OUT/'job.json').write_text(json.dumps(job),encoding='utf-8')
os.environ['CHARACTER_PIPELINE_JOB']=str(OUT/'job.json')
PATH='/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotAirStrong'

def author_material():
    material=unreal.load_asset(PATH)
    lib=unreal.MaterialEditingLibrary
    if material is None:
        folder,name=PATH.rsplit('/',1)
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('refraction_method',unreal.RefractionMode.RM_INDEX_OF_REFRACTION)
    def node(kind,**props):
        result=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for key,val in props.items(): result.set_editor_property(key,val)
        return result
    def c(val): return node('Constant',r=float(val))
    def op(kind,a,b=None):
        result=node(kind)
        inputs=list(lib.get_material_expression_input_names(result))
        assert lib.connect_material_expressions(a,'',result,inputs[0]),kind
        if b is not None: assert lib.connect_material_expressions(b,'',result,inputs[1]),kind
        return result
    def output(expr,prop): assert lib.connect_material_property(expr,'',prop)
    uv=node('TextureCoordinate')
    center=node('Constant2Vector',r=.5,g=.5)
    radius=op('Length',op('Subtract',uv,center))
    ring=op('Power',op('Saturate',op('Subtract',c(1),op('Multiply',op('Abs',op('Subtract',radius,c(.36))),c(13)))),c(1.6))
    pan=node('Panner',speed_x=.13,speed_y=.65)
    assert lib.connect_material_expressions(op('Multiply',uv,c(2)),'',pan,'Coordinate')
    noise=node('TextureSample',texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'))
    assert lib.connect_material_expressions(pan,'',noise,'UVs')
    mask=node('ComponentMask',r=True,g=False,b=False,a=False)
    assert lib.connect_material_expressions(noise,'',mask,lib.get_material_expression_input_names(mask)[0])
    envelope=node('ScalarParameter',parameter_name='Envelope',default_value=0)
    body=op('Multiply',op('Multiply',ring,op('Add',c(.3),op('Multiply',mask,c(.7)))),envelope)
    output(op('Multiply',body,c(.64)),unreal.MaterialProperty.MP_OPACITY)
    gold=node('Constant3Vector',constant=unreal.LinearColor(8,6.2,3.7,1))
    output(op('Multiply',body,gold),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    refraction=op('Add',c(1),op('Multiply',op('Multiply',body,op('Subtract',mask,c(.5))),c(.3)))
    output(refraction,unreal.MaterialProperty.MP_REFRACTION)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False),'save owned W material'
    (OUT/'material.json').write_text(json.dumps({'asset':PATH,'passed':True,'blend':'translucent','refraction':True}),encoding='utf-8')

def main():
    try:
        author_material()
    except Exception:
        (OUT/'material-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        unreal.SystemLibrary.quit_editor()
    else:
        from context import fps
        from training_room_verify import TrainingRunner,select
        from countess_w_speed_compare import settle_switch
        from sparrow_runtime import valid,xyz

        def waves(rig): return list(unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave))
        def view(rig):
            cam=rig.controller.player_camera_manager
            rot=cam.get_camera_rotation()
            return {'position':xyz(cam.get_camera_location()),'rotation':[rot.pitch,rot.yaw,rot.roll],'fov':cam.get_fov_angle()}
        def deviation(a,b): return max(math.dist(a[k],b[k]) for k in ('position','rotation'))
        def ready(rig):
            yield from select(rig,'sparrow')
            yield .8
            unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        def release(rig):
            yield from ready(rig)
            target=rig.dummy(0,500)
            second=rig.dummy(0,750)
            rig.aim_target(target)
            before=view(rig)
            started=rig.now
            yield from rig.skill_key('W',target.get_actor_location())
            yield rig.until(lambda:bool(waves(rig)),1.5,'W actual arrow release spawns the air wave')
            released=rig.now
            wave=waves(rig)[0]
            for mesh in wave.get_components_by_class(unreal.StaticMeshComponent):
                mat=mesh.get_material(0)
                rig.check(mat is not None and mat.get_base_material().get_path_name().startswith(PATH),
                          'all three waves use the owned translucent material')
                rig.check(mesh.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION,'visual wave has no collision')
            samples=[]
            for at in (.025,.09,.19):
                yield max(1/fps,at-(rig.now-released))
                current=view(rig)
                samples.append(current)
                rig.data.setdefault('wave_meshes',[]).append([{'location':xyz(m.get_world_location()),
                    'scale':xyz(m.get_world_scale()),'visible':m.is_visible(),
                    'envelope':m.get_material(0).get_scalar_parameter_value('Envelope')}
                    for m in wave.get_components_by_class(unreal.StaticMeshComponent)])
                rig.snapshot()
                yield rig.capture('W-air-'+str(at))
            rig.check(any(deviation(v,before)>.2 for v in samples),'release produces measurable camera recoil')
            yield .6
            after=view(rig)
            rig.check(not waves(rig) and deviation(after,before)<.1 and abs(after['fov']-before['fov'])<.001,
                      'air waves expire and camera returns to its baseline')
            rig.check(rig.health(target)==65 and rig.health(second)==65,'charged piercing arrow keeps one 35-damage hit per target')
            yield rig.idle(3)
            rig.assert_recovered()
            rig.data.update(release_time=released-started,camera_before=before,camera_samples=samples,camera_after=after)
        def cancel(rig):
            yield from ready(rig)
            target=rig.dummy(0,500)
            rig.aim_target(target)
            before=view(rig)
            yield from rig.skill_key('W',target.get_actor_location())
            yield .35
            rig.interrupt()
            yield 1.2
            rig.check(not waves(rig) and rig.health(target)==100,'cancel before release prevents wave and damage')
            rig.check(deviation(view(rig),before)<.1,'cancelled charge leaves camera unchanged')
            rig.assert_recovered()
        def owner_cleanup(rig):
            yield from ready(rig)
            target=rig.dummy(0,500)
            yield from rig.skill_key('W',target.get_actor_location())
            yield rig.until(lambda:bool(waves(rig)),1.5,'active wave exists before owner switch')
            previous=waves(rig)[0]
            rig.key('Press','One')
            yield 1/fps
            rig.key('Release','One')
            yield .6
            rig.hero('countess')
            rig.check(not valid(previous) and not waves(rig),'numeric hero switch clears W wave and its recoil')
            rig.check(abs(view(rig)['fov']-55)<.001,'switch retains approved camera FOV')
        class FeedbackRunner(TrainingRunner):
            def __init__(self):
                super().__init__()
                self.cases=[('W_release_feedback',release),('W_cancel',cancel),('W_owner_cleanup',owner_cleanup)]
                self.report_name='W-feedback.json'
                self.report.update(suite='sparrow_W_feedback_scoped',verification_scope='one 60fps PIE; release, cancel, switch; selected dependencies only')
            def case_generator(self,factory):
                self.rig.switch=types.MethodType(settle_switch,self.rig)
                yield from TrainingRunner.case_generator(self,factory)
        runtime=FeedbackRunner()
        runtime.start()


if __name__ == '__main__':
    main()
