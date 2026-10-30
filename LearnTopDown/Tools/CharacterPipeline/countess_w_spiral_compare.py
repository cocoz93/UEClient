"""Compare the preserved textured rim and connected spiral W through actual PIE input."""
from pathlib import Path
import sys
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
from context import fps
from training_room_verify import TrainingRunner, room, select, skill
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


def variant(rig, enhanced):
    unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.WPlayRate 1')
    unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 1')
    unreal.SystemLibrary.execute_console_command(rig.world, 'Countess.Skills.WPresentation ' + str(3 if enhanced else 2))
    rig.check(unreal.SystemLibrary.get_console_variable_int_value('Countess.Skills.WPresentation') == (3 if enhanced else 2),
              'W-only switch selects the requested rim or spiral presentation')


def effects(rig):
    return [e for e in rig.latest['effects'] if 'BladeSiphon' in e['template'] or 'CountessW_' in e['template']]


def finished(rig):
    yield rig.idle(6)
    yield rig.until(lambda: not any(e['active'] and e['particles'] > 0 for e in effects(rig)),
                    8, 'W and its original textured particles naturally expire')
    rig.assert_recovered()


def warm(rig):
    yield from select(rig, 'countess')
    for enhanced in (False, True):
        variant(rig, enhanced)
        yield from rig.skill_key('W', rig.ground(0, 170))
        rig.check(rig.component.is_casting(), 'both rim and spiral W are genuinely rendered during warmup')
        yield 1.5
        yield from finished(rig)


def trial(enhanced):
    def run(rig):
        yield from select(rig, 'countess')
        variant(rig, enhanced)
        definition = rig.component.get_editor_property('skills')[1]
        for field, expected in (('damage', 40), ('range', 240), ('cooldown', 6),
                                ('action_time', .55), ('recovery_time', .95)):
            rig.check(abs(definition.get_editor_property(field) - expected) < .001,
                      'W retains configured ' + field)
        targets = [statue_target(rig, x, y) for x, y in ((0, 170), (-145, 50), (130, -70))]
        outside = statue_target(rig, 0, 400)
        rig.aim_target(targets[0])
        start = rig.now
        yield from rig.skill_key('W', targets[0].get_actor_location())
        rig.check(rig.component.is_casting(), 'W starts through its actual controller key binding')
        mode = 'spiral' if enhanced else 'rim'
        all_effects = []
        for index in range(16):
            at = .10 + index * .10
            yield max(1 / fps, at - (rig.now - start))
            rig.snapshot()
            current = effects(rig)
            all_effects += current
            rig.data.setdefault('frames', []).append({'index': index, 'elapsed': rig.now - start,
                'effects': current, 'pawn': xyz(rig.pawn.get_actor_location()),
                'camera': rig.latest['view_location'], 'healths': [rig.health(t) for t in targets]})
            yield rig.capture(f'W-{mode}-{index:02}')
        rig.check(all(rig.health(t) == 60 for t in targets), 'W hits each of three nearby enemies once for unchanged 40 damage')
        rig.check(rig.health(outside) == 100, 'spiral W does not enlarge its actual damage range')
        hit_times = [s['time'] - start for s in rig.trace if s['healths'] and s['healths'][0] < 100]
        rig.check(bool(hit_times) and .53 <= min(hit_times) <= .55 + 3 / fps, 'W retains its real hit timing')
        names = {e['template'] for e in all_effects}
        if enhanced:
            rig.check(all(any(name in n for n in names) for name in
                          ('P_CountessW_SpiralRing', 'P_CountessW_DenseTrails', 'P_CountessW_DenseHit')),
                      'all three original-texture private W assets are actually spawned')
        else:
            rig.check(any('P_CountessW_RimRing' in n for n in names) and not any('P_CountessW_SpiralRing' in n for n in names), 'preserved rim does not spawn spiral copies')
        rig.data.update(first_damage_seconds=min(hit_times), target_healths=[rig.health(t) for t in targets],
                        outside_health=rig.health(outside), variant=mode)
        yield from finished(rig)
        rig.snapshot()
        yield rig.capture('W-' + mode + '-clear')
    return run


def unchanged(key, expected):
    def run(rig):
        variant(rig, True)
        yield from skill('countess', key)(rig)
        rig.check(abs(rig.data['target_health_minimum'] - expected) < .001,
                  key + ' retains its unchanged damage after the W-only change')
    return run


def owner_cleanup(rig):
    yield from select(rig, 'countess')
    variant(rig, True)
    target = statue_target(rig, 0, 170)
    yield from rig.skill_key('W', target.get_actor_location())
    yield .62
    rig.snapshot()
    rig.check(any(e['particles'] > 0 for e in effects(rig)), 'spiral W is genuinely visible before hero selection')
    previous = rig.pawn
    rig.key('Press', 'Two')
    yield 1 / fps
    rig.key('Release', 'Two')
    rig.hero('sparrow')
    yield .6
    rig.snapshot()
    rig.check(not valid(previous) and not any(e['particles'] > 0 for e in effects(rig)),
              'numeric hero switching destroys the old owner and all its spiral W effects')
    yield rig.capture('W-owner-cleanup-sparrow')


def early_cancel(rig):
    yield from select(rig, 'countess')
    variant(rig, True)
    target = statue_target(rig, 0, 170)
    yield from rig.skill_key('W', target.get_actor_location())
    yield .40
    rig.anim.montage_stop(.05)
    yield .65
    rig.check(rig.health(target) == 100, 'cancelling W before impact creates no delayed damage')
    yield from finished(rig)
    rig.snapshot()
    yield rig.capture('W-cancelled-clear')


def cooldown(rig):
    yield from rig.switch('sparrow')
    yield from rig.switch('countess')
    variant(rig,True)
    unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 0')
    target=statue_target(rig,0,170)
    yield from rig.skill_key('W',target.get_actor_location())
    rig.check(rig.component.is_casting(),'spiral W starts with normal cooldowns enabled')
    yield 1.1
    rig.check(rig.health(target)==60 and not rig.component.is_casting(),'normal W hits once and releases its input lock')
    yield from rig.skill_key('W',target.get_actor_location())
    rig.check(not rig.component.is_casting() and rig.component.get_input_feedback()=='Cooldown',
              'W retains its real configured cooldown instead of becoming freely repeatable')
    rig.check(rig.health(target)==60,'blocked W recast does not create another damage event')
    yield from finished(rig)
    rig.snapshot()
    yield rig.capture('W-normal-cooldown')


class WRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases = [('room', room), ('W_renderer_warmup', warm),
                      ('W_rim', trial(False)), ('W_spiral', trial(True)),
                      ('Q_unchanged', unchanged('Q', 65)), ('E_unchanged', unchanged('E', 55)),
                      ('R_unchanged', unchanged('R', 20)), ('W_owner_cleanup', owner_cleanup),
                      ('W_early_cancel', early_cancel),('W_normal_cooldown',cooldown)]
        self.report_name = f'countess-w-spiral-comparison-{fps}.json'
        self.report.update(suite='countess_w_connected_textured_spiral', character_code_modified=True,
                           scope='W inner-to-outer original-texture spiral distribution and lifetime only',
                           physical_input_tested=False, camera_zoom_changed=False,
                           capture_kind='actual PIE viewport samples, not continuous video')


runtime = WRunner()
runtime.start()
