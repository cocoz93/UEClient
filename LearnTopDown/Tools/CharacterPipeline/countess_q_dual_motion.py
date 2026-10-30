"""Sample actual Q gameplay at 50ms intervals, plus direction/owner cleanup checks."""
from pathlib import Path
import sys
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT/'Tools/CharacterPipeline'))
from context import fps
from countess_q_dual_compare import set_variant, accent_settings, warm_q
from training_room_verify import TrainingRunner, room, select
from sparrow_runtime import xyz, valid


def statue_target(rig, x=0, y=420):
    target = rig.dummy(x, y)
    statue = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.KwangTrainingDummy)
                  if 'TrainingRoomTarget' in [str(t) for t in a.tags])
    source = statue.get_component_by_class(unreal.StaticMeshComponent)
    mesh = target.get_component_by_class(unreal.StaticMeshComponent)
    mesh.set_static_mesh(source.get_editor_property('static_mesh'))
    mesh.set_relative_location(unreal.Vector(0, 0, -90), False, False)
    mesh.set_relative_scale3d(unreal.Vector(.8, .8, .85))
    mesh.set_relative_rotation(unreal.Rotator(yaw=-90), False, False)
    for slot in range(source.get_num_materials()):
        mesh.set_material(slot, source.get_material(slot))
    label = target.get_component_by_class(unreal.TextRenderComponent)
    label.set_world_size(16)
    label.set_relative_location(unreal.Vector(0, 0, 100), False, False)
    return target


def motion(enhanced):
    def run(rig):
        yield from select(rig, 'countess')
        set_variant(rig, enhanced)
        target = statue_target(rig)
        rig.aim_target(target)
        start = rig.now
        yield from rig.skill_key('Q', target.get_actor_location())
        mode = 'legacy' if enhanced == 'legacy' else ('enhanced' if enhanced else 'original')
        for index in range(16):
            at = .10 + index*.05
            yield max(1/fps, at-(rig.now-start))
            rig.snapshot()
            rig.data.setdefault('frames', []).append({'index': index, 'elapsed': rig.now-start,
                'pawn': xyz(rig.pawn.get_actor_location()), 'camera': rig.latest['view_location'],
                'accents': accent_settings(rig), 'sockets':{str(n):xyz(rig.mesh.get_socket_location(n)) for n in ('FX_WeaponBase_L','FX_WeaponTip_L','FX_WeaponBase_R','FX_WeaponTip_R')}, 'montage_position':rig.latest.get('montage_position')})
            yield rig.capture(f'Q-motion-{mode}-{index:02}')
        rig.check(rig.health(target) == 65, 'sampled Q still deals only one 35-damage hit')
        rig.check(not accent_settings(rig), 'sampled Q finishes without leaving a visible blade')
        rig.assert_recovered()
    return run


def direction(x, y):
    def run(rig):
        yield from select(rig, 'countess')
        set_variant(rig, True)
        target = statue_target(rig, x, y)
        rig.aim_target(target)
        yield from rig.skill_key('Q', target.get_actor_location())
        yield .30
        rig.check(rig.health(target) == 65 and bool(accent_settings(rig)),
                  'other-direction Q hits once and displays its large blade')
        settings=accent_settings(rig)
        rig.check(all(max(abs(v-w) for v,w in zip(a['rotation'],a['mesh_rotation'])) < .1 for a in settings),
                  'other-direction sweep has the actual skeletal mesh orientation')
        rig.data['accents']=settings
        rig.snapshot()
        yield rig.capture(f'Q-direction-{x}-{y}')
        yield .6
        rig.check(not accent_settings(rig), 'other-direction Q blade expires')
        rig.assert_recovered()
    return run


def owner_cleanup(rig):
    yield from select(rig, 'countess')
    set_variant(rig, True)
    target = statue_target(rig)
    rig.aim_target(target)
    yield from rig.skill_key('Q', target.get_actor_location())
    yield .28
    rig.check(bool(accent_settings(rig)), 'Q visual exists immediately before changing character')
    previous = rig.pawn
    rig.key('Press', 'Two')
    yield 1/fps
    rig.key('Release', 'Two')
    rig.hero('sparrow')
    rig.check(not valid(previous) and not accent_settings(rig),
              'actual numeric character selection destroys the old pawn and all its Q blades')
    yield .6
    rig.snapshot()
    yield rig.capture('Q-owner-cleanup-sparrow')


def interrupted_before_hit(rig):
    yield from select(rig, 'countess')
    set_variant(rig, True)
    target=statue_target(rig)
    rig.aim_target(target)
    yield from rig.skill_key('Q',target.get_actor_location())
    yield .12
    rig.check(bool(accent_settings(rig)), 'the actual opening sweep exists before impact')
    target.destroy_actor()
    yield .10
    rig.check(not accent_settings(rig), 'losing the real target before impact removes the opening sweep')
    yield .8
    rig.assert_recovered()
    rig.snapshot()
    yield rig.capture('Q-interrupted-cleanup')


class MotionRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases = [('room', room), ('Q_renderer_warmup', warm_q),
                      ('Q_motion_legacy', motion('legacy')), ('Q_motion_original', motion(False)), ('Q_motion_enhanced', motion(True)),
                      ('Q_direction_left', direction(-420, 0)),
                      ('Q_direction_back', direction(0, -420)), ('Q_owner_cleanup', owner_cleanup), ('Q_interrupted_before_hit',interrupted_before_hit)]
        self.report_name = f'countess-q-comparison-{fps}.json'
        asset=unreal.load_asset('/Game/TopDown/Characters/Countess/FX/SM_CountessQDualSweep')
        desc=asset.get_static_mesh_description(0)
        self.report['sweep_mesh_uvs']=[]
        for i in range(min(12,desc.get_vertex_instance_count())):
            uv=desc.get_vertex_instance_uv(unreal.VertexInstanceID(i),0)
            self.report['sweep_mesh_uvs'].append([uv.x,uv.y])
        self.report.update(suite='countess_q_dual_motion',
                           capture_kind='native paused samples of actual PIE, 50ms simulation intervals',
                           camera_zoom_changed=False, physical_input_tested=False)


runtime = MotionRunner()
runtime.start()
