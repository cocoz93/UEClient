"""Read-only real F2 floor/base/camera probe in the original map."""
import json,os,time,traceback
from pathlib import Path
import unreal
qa=Path(os.environ['SPARROW_QA_OUTPUT'])
state={'phase':'load','wall':time.monotonic(),'rows':[],'frame':0}
def scalar(value):
    if isinstance(value,unreal.Vector):return [value.x,value.y,value.z]
    if isinstance(value,(float,int,bool,str)) or value is None:return value
    if isinstance(value,unreal.Object):return value.get_path_name()
    return str(value)
def read_properties(obj, names):
    result={}
    for name in names:
        try:result[name]=scalar(obj.get_editor_property(name))
        except Exception as error:result[name]={'unavailable':str(error)}
    return result
def sample(world,pawn,controller):
    movement=pawn.get_editor_property('character_movement')
    capsule=pawn.get_component_by_class(unreal.CapsuleComponent)
    base=getattr(pawn,'get_movement_base',lambda: None)()
    floor=movement.get_editor_property('current_floor')
    hit=floor.get_editor_property('hit_result')
    return {'frame':state['frame'],'time':unreal.GameplayStatics.get_time_seconds(world),'pawn':pawn.get_name(),
        'location':scalar(pawn.get_actor_location()),'velocity':scalar(pawn.get_velocity()),
        'movement':read_properties(movement,('movement_mode','default_land_movement_mode','force_next_floor_check','just_teleported')),
        'floor':read_properties(floor,('blocking_hit','walkable_floor','floor_dist','line_dist')),
        'floor_hit':read_properties(hit,('blocking_hit','start_penetrating','distance','location','impact_point','normal','impact_normal','hit_object_handle')),
        'base':scalar(base),'base_owner':scalar(base.get_owner()) if base else None,
        'capsule_profile':str(capsule.get_collision_profile_name()),'capsule_channel':str(capsule.get_collision_object_type()),
        'camera_location':scalar(controller.player_camera_manager.get_camera_location())}
def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa/'switch-probe.json').write_text(json.dumps({'passed':error is None,'error':str(error) if error else None,'rows':state['rows']},indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
def tick(delta):
    try:
        if time.monotonic()-state['wall']>160:raise TimeoutError('switch probe timed out')
        if state['phase']=='load':
            unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase']='ready';return
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn=unreal.GameplayStatics.get_player_character(world,0) if world else None
        controller=unreal.GameplayStatics.get_player_controller(world,0) if world else None
        if not pawn or not controller:return
        if state['phase']=='ready':
            if unreal.GameplayStatics.get_time_seconds(world)<6:return
            state['rows'].append(sample(world,pawn,controller))
            unreal.SystemLibrary.execute_console_command(world,'CountessInputQA.Key F2 Press')
            state['phase']='probe';return
        state['frame']+=1
        state['rows'].append(sample(world,pawn,controller))
        if state['frame']==1:unreal.SystemLibrary.execute_console_command(world,'CountessInputQA.Key F2 Release')
        if state['frame']>=30:finish()
    except Exception as error:
        unreal.log_error(traceback.format_exc());finish(error)
handle=unreal.register_slate_post_tick_callback(tick)
