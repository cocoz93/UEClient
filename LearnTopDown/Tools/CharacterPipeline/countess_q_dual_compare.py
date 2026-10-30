"""Compare Q presentation in actual PIE with identical room, camera and gameplay."""
import math
from pathlib import Path
import sys
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
from context import fps
from training_room_verify import TrainingRunner, room, select, skill
from sparrow_runtime import xyz, valid

CVAR = 'Countess.Skills.QPresentation'


def set_variant(rig, enhanced):
    choice = 1 if enhanced == 'legacy' else (2 if enhanced else 0)
    unreal.SystemLibrary.execute_console_command(rig.world, CVAR + ' ' + str(choice))
    rig.check(unreal.SystemLibrary.get_console_variable_int_value(CVAR) == choice,
              'compiled Q-only presentation switch selects the requested variant')


def particle_settings(rig):
    rows = []
    for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
        if not valid(particle) or not particle.component_has_tag('CountessSkillFX'):
            continue
        outer = particle.get_outer()
        while outer is not None and outer != rig.world:
            outer = outer.get_outer()
        if outer != rig.world:
            continue
        template = particle.get_editor_property('template')
        if template:
            rows.append({'template':template.get_path_name(), 'scale':xyz(particle.get_world_scale()),
                         'time_dilation':particle.get_editor_property('custom_time_dilation')})
    return rows


def accent_settings(rig):
    rows = []
    for actor in unreal.GameplayStatics.get_all_actors_with_tag(rig.world, 'CountessQImpactAccent'):
        blades = actor.get_components_by_class(unreal.StaticMeshComponent)
        rows.append({'position':xyz(actor.get_actor_location()),'collision':actor.get_actor_enable_collision(),
                     'rotation':[actor.get_actor_rotation().pitch,actor.get_actor_rotation().yaw,actor.get_actor_rotation().roll], 'mesh_rotation':[rig.mesh.get_world_rotation().pitch,rig.mesh.get_world_rotation().yaw,rig.mesh.get_world_rotation().roll],
                     'blades':[{'mesh':blade.get_editor_property('static_mesh').get_path_name(), 'rotation':[blade.get_world_rotation().pitch,blade.get_world_rotation().yaw,blade.get_world_rotation().roll], 'material':blade.get_material(0).get_editor_property('parent').get_path_name(),
                                'collision':str(blade.get_collision_enabled()),
                                'scale':xyz(blade.get_editor_property('relative_scale3d'))} for blade in blades]})
    return rows


def q_trial(enhanced):
    def run(rig):
        yield from select(rig, 'countess')
        set_variant(rig, enhanced)
        unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.IgnoreCooldowns 1')
        definition = rig.component.get_editor_property('skills')[0]
        rig.check(abs(definition.get_editor_property('damage') - 35) < .001 and
                  abs(definition.get_editor_property('range') - 850) < .001 and
                  abs(definition.get_editor_property('cooldown') - 8) < .001 and
                  abs(definition.get_editor_property('action_time') - .2) < .001,
                  'Q retains its configured damage, range, cooldown and 0.2s action time')
        target = rig.dummy(0, 420)
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
        rig.aim_target(target)
        origin = xyz(rig.pawn.get_actor_location())
        start = rig.now
        yield from rig.skill_key('Q', target.get_actor_location())
        mode = 'enhanced' if enhanced else 'original'
        rig.check(rig.component.is_casting(), 'Q starts through the actual controller key binding')
        observed = []
        accents = []
        for label, at in (('prepare', .10), ('arrival', .23), ('slash', .30),
                          ('afterimage', .42), ('settle', .58), ('recovery', .80)):
            yield max(1 / fps, at - (rig.now - start))
            rig.snapshot()
            settings = particle_settings(rig)
            observed += settings
            current_accents = accent_settings(rig)
            accents += current_accents
            rig.data.setdefault('phases', []).append({'phase':label,'elapsed':rig.now-start,'effects':settings,
                'accents':current_accents, 'sockets':{str(n):xyz(rig.mesh.get_socket_location(n)) for n in ('FX_WeaponBase_L','FX_WeaponTip_L','FX_WeaponBase_R','FX_WeaponTip_R')}, 'montage_position':rig.latest.get('montage_position'), 'pawn':xyz(rig.pawn.get_actor_location()),'camera':rig.latest['view_location']})
            yield rig.capture('Q-' + mode + '-' + label)
        rig.check(rig.health(target) == 65, 'Q deals exactly one unchanged 35-damage hit')
        hits = [s['time']-start for s in rig.trace if s['healths'] and s['healths'][0] < 100]
        rig.check(bool(hits) and .18 <= min(hits) <= .2 + 3/fps,
                  'Q retains its real gameplay hit timing despite the longer visual afterimage')
        slashes = [e for e in observed if 'p_Countess_XSlash.' in e['template']]
        rig.check(bool(slashes), 'the actual original authored cross-slash particle component is observed')
        rig.check(all(abs(e['scale'][0] - 1) < .001 and abs(e['time_dilation'] - 1) < .001 for e in slashes),
                  'the original cross-slash motion is retained without expanding the authored flying blades')
        rig.check(bool(accents) == enhanced, 'only enhanced Q creates its large measured dual-sword sweeps')
        for accent in accents:
            rig.check(not accent['collision'] and len(accent['blades']) in (1,3) and
                      all('M_CountessQDualSweep' in b['material'] and 'NO_COLLISION' in b['collision']
                          for b in accent['blades']),
                      'the Q accent has measured dual sweep plus optional departure ribbon and impact with finished materials and no gameplay collision')
        rig.check(not accent_settings(rig), 'the brief accent expires before Q recovery')
        dual=[b for a in accents for b in a['blades'] if 'SM_CountessQDualSweep' in b['mesh']]
        rig.check(bool(dual)==enhanced, 'the visible blade geometry comes from the measured left and right weapon socket paths')
        rig.check(all(max(abs(v-w) for v,w in zip(a['rotation'],a['mesh_rotation'])) < .1 for a in accents), 'sweep orientation matches the actual skeletal mesh, without fixed-plane tilt or camera billboard')
        rig.data.update(variant=mode, first_damage_seconds=min(hits), damage=35,
                        initial_position=origin, target_health=rig.health(target))
        yield rig.idle()
        yield from rig.skill_key('Q', target.get_actor_location())
        yield rig.until(lambda: math.dist(xyz(rig.pawn.get_actor_location()), origin) < 2,
                        2, 'Q recast still returns to its original location')
        rig.check(rig.health(target) == 65, 'Q return does not add another damage event')
        yield rig.idle()
        yield rig.until(lambda: not any(e['active'] and e['particles'] > 0 for e in rig.latest['effects']),
                        10, 'Q and its afterimage naturally finish without leaving particle components alive')
        rig.assert_recovered()
        rig.snapshot()
        yield rig.capture('Q-' + mode + '-return')
    return run


def unchanged_e(enhanced):
    def run(rig):
        set_variant(rig, enhanced)
        yield from skill('countess', 'E')(rig)
        rig.data['q_presentation_switch'] = int(enhanced)
        rig.check(abs(rig.data['target_health_minimum'] - 55) < .001,
                  'E retains its original single 45-damage hit with either Q presentation setting')
    return run


def warm_q(rig):
    yield from select(rig, 'countess')
    unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.IgnoreCooldowns 1')
    for enhanced in (False, True):
        set_variant(rig, enhanced)
        target = rig.dummy(0, 420)
        rig.aim_target(target)
        yield from rig.skill_key('Q', target.get_actor_location())
        yield .8
        yield rig.idle()
        yield from rig.skill_key('Q', target.get_actor_location())
        yield rig.idle()
        yield rig.until(lambda: not any(e['active'] and e['particles'] > 0 for e in rig.latest['effects']),
                        10, 'both Q variants have rendered and expired before the paired captures')
        target.destroy_actor()
        rig.targets.remove(target)
        rig.fixtures.remove(target)
        yield 2.5
    rig.assert_recovered()


class ComparisonRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases = [('room', room), ('Q_renderer_warmup', warm_q),
                      ('Q_original', q_trial(False)), ('Q_enhanced', q_trial(True)),
                      ('E_with_original_Q_setting', unchanged_e(False)),
                      ('E_with_enhanced_Q_setting', unchanged_e(True))]
        self.report_name = f'countess-q-comparison-{fps}.json'
        self.report.update(suite='countess_q_comparison', character_code_modified=True,
                           change_scope='measured dual Q sweep presentation only; E/gameplay settings preserved',
                           physical_input_tested=False)


if __name__ == '__main__':
    runtime = ComparisonRunner()
    runtime.start()
