"""Actual controller/PIE checks in the new room, with both protected heroes."""
import json
import math
from pathlib import Path
import sys

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path[:0] = [str(ROOT / 'Tools/CharacterPipeline'), str(ROOT / 'Tools/CharacterPipeline/Suites')]
from context import fps, profile, qa
from sparrow_runtime import Runner, valid, xyz
import character_switch
from character_switch import SwitchRunner, field_meshes

ROOM = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
character_switch.ORIGINAL_MAP = ROOM
HERO_PROFILES = {name: json.loads((ROOT / f'Tools/CharacterPipeline/Profiles/{name}.json').read_text(encoding='utf-8'))
                 for name in ('countess', 'sparrow')}


def hero_name(rig):
    return 'sparrow' if isinstance(rig.pawn, unreal.SparrowCharacter) else 'countess'


def select(rig, name):
    if hero_name(rig) != name:
        yield from rig.switch(name)
    rig.hero(name)
    yield .5


def room(rig):
    yield 5.0
    rig.hero('countess')
    rig.check(len(rig.runner.original_field) >= 120, 'new room contains finished static architecture and floor inlay')
    placed = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.KwangTrainingDummy)
              if 'TrainingRoomTarget' in [str(t) for t in a.tags]]
    rig.check(len(placed) == 3, 'three persistent stone practice targets are present')
    texture_rows = []
    room_textures = []
    # EditorAssetLibrary deliberately rejects queries during PIE; read package names from our folder.
    for file in sorted((ROOT / 'Content/TopDown/TrainingRoom/Textures').glob('*.uasset')):
        path = '/Game/' + file.relative_to(ROOT / 'Content').with_suffix('').as_posix()
        texture = unreal.load_asset(path)
        room_textures.append((path, texture))
    yield rig.until(lambda: all(max(t.blueprint_get_size_x(), t.blueprint_get_size_y()) >= 1024
                               for _, t in room_textures), 30, 'room texture compilation resolves beyond temporary 32px placeholders')
    for path, texture in room_textures:
        size = [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]
        rig.check(1024 <= max(size) <= 2048, 'room-owned texture has finished building at no more than 2K')
        texture_rows.append({'path': path, 'actual_platform_size': size})
    rig.check(bool(texture_rows), 'room has explicit environment-only texture-budget copies')
    rig.runner.report['environment_texture_sizes'] = texture_rows
    for actor in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.StaticMeshActor):
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        for i in range(comp.get_num_materials()):
            mat = comp.get_material(i)
            rig.check(mat is not None and not any(s in mat.get_path_name() for s in ('WorldGridMaterial', 'DefaultMaterial')),
                      'room surfaces have configured non-placeholder materials')
            rig.check(mat.get_path_name().startswith('/Game/TopDown/TrainingRoom/Materials/'),
                      'saved room actors resolve their project-owned resource-budget materials')
    arm = rig.pawn.get_components_by_class(unreal.SpringArmComponent)[0]
    camera = rig.pawn.get_components_by_class(unreal.CameraComponent)[0]
    rig.check(abs(arm.get_editor_property('target_arm_length') - 2000) < .001 and
              abs(camera.get_editor_property('field_of_view') - 55) < .001,
              'new environment preserves the approved 2000cm / 55 degree gameplay camera')
    rig.snapshot()
    yield rig.capture('room-countess-overview')


def navigation(name):
    def run(rig):
        yield from select(rig, name)
        for x, y in ((0, 150), (500, -150), (-450, -650), (0, -400)):
            goal = rig.ground_absolute(x, y)
            yield from rig.click('Right', goal)
            rig.assert_cursor_goal(goal)
            yield rig.until(lambda: math.dist(xyz(rig.pawn.get_actor_location())[:2], [x, y]) < 45,
                            4, name + ' reaches actual ground click through navigation')
        yield 2.5  # Wait for the retained camera lag after each fixture-only teleport.
        rig.check(not rig.movement.is_falling(), name + ' stays on the solid modular floor')
        rig.snapshot()
        yield rig.capture(name + '-navigation')
    return run


def switch(rig):
    yield from select(rig, 'countess')
    yield from rig.noop('countess')
    yield from rig.switch('sparrow')
    yield from rig.noop('sparrow')
    rig.snapshot()
    yield rig.capture('room-sparrow-overview')
    yield from rig.switch('countess')


def primary(name):
    def run(rig):
        yield from select(rig, name)
        target = rig.dummy(0, 160 if name == 'countess' else 500)
        rig.aim_target(target)
        before = rig.health(target)
        yield from rig.click('Left', target.get_actor_location())
        yield rig.until(lambda: rig.health(target) < before, 3, name + ' basic attack deals damage')
        rig.snapshot()
        yield rig.capture(name + '-primary-impact')
        yield rig.idle()
        rig.assert_recovered()
        rig.data['health_before_after'] = [before, rig.health(target)]
        yield .6
    return run


def skill(name, key):
    def run(rig):
        yield from select(rig, name)
        distance = (200 if key == 'E' else 170) if name == 'countess' else 500
        target = rig.dummy(0, distance)
        rig.aim_target(target)
        before = rig.health(target)
        started = rig.now
        yield from rig.skill_key(key, target.get_actor_location())
        rig.check(rig.component.is_casting(), name + ' ' + key + ' uses its actual slot binding')
        phases = [('prepare', .1), ('impact', .62)]
        if name == 'countess' and key == 'Q':
            phases = [('prepare', .1), ('impact', .3)]
        elif name == 'countess' and key == 'E':
            phases = [('prepare', .1), ('impact', .7)]
        elif name == 'countess' and key == 'R':
            phases = [('arrival', .13), ('windup', .3), ('impact', .6)]
        elif name == 'sparrow' and key == 'Q':
            phases = [('prepare', .2), ('rain', 1.4)]
        elif name == 'sparrow' and key == 'W':
            phases = [('charge', .55), ('release', 1.18)]
        elif name == 'sparrow' and key == 'R':
            yield .45
            rig.check(rig.component.is_inner_fire_active(), 'archer R activates its three-arrow buff')
            yield rig.idle(3)  # Firing is intentionally blocked during the buff activation animation.
            rig.aim_target(target)
            yield from rig.click('Left', target.get_actor_location())
            phases = [('empowered-shot', 1.25)]
        elif name == 'sparrow' and key == 'E':
            phases = [('rapid-start', .18), ('rapid-last', .65)]
        for label, at in phases:
            yield max(1 / fps, at - (rig.now - started))
            rig.snapshot()
            yield rig.capture(name + '-' + key + '-' + label)
        yield rig.until(lambda: any(s['healths'] and s['healths'][0] < before for s in rig.trace),
                        5, name + ' ' + key + ' produces actual target damage')
        yield rig.idle(6)
        # Observe natural expiry rather than destroying live effects to make a test pass.
        yield rig.until(lambda: not any(e['active'] and e['particles'] > 0 for e in rig.latest['effects']),
                        12, name + ' ' + key + ' particles naturally expire')
        if name == 'sparrow' and key == 'R':
            rig.check(not rig.component.is_inner_fire_active(), 'archer R buff naturally expires')
        rig.assert_recovered()
        rig.data['target_health_initial'] = before
        rig.data['target_health_minimum'] = min(s['healths'][0] for s in rig.trace if s['healths'])
        rig.snapshot()
        yield rig.capture(name + '-' + key + '-recovery')
    return run


def cleanup(rig):
    yield from select(rig, 'sparrow')
    target = rig.dummy(0, 500)
    rig.aim_target(target)
    yield from rig.skill_key('Q', target.get_actor_location())
    yield 1.0
    rig.check(any(e['active'] and e['particles'] > 0 for e in rig.snapshot()['effects']),
              'archer Q is genuinely active before switching')
    yield from rig.switch('countess')
    rig.cleanup()
    after = rig.health(target)
    yield 1.1
    rig.cleanup()
    rig.check(rig.health(target) == after, 'destroyed archer rain owner does not keep damaging its target')
    rig.snapshot()
    yield rig.capture('room-final-countess')


class TrainingRunner(SwitchRunner):
    def __init__(self):
        cases = [('room_and_materials', room), ('number_key_switch_and_camera', switch)]
        for name in ('countess', 'sparrow'):
            cases += [(name + '_navigation', navigation(name)), (name + '_primary', primary(name))]
            cases += [(name + '_' + key, skill(name, key)) for key in ('Q', 'W', 'E', 'R')]
        cases.append(('switch_during_active_rain', cleanup))
        Runner.__init__(self, 'training_room', cases)
        self.report.update(map=ROOM, character_code_modified=False, scene_changes_saved=False,
                           camera='approved gameplay camera; no close-camera replacements',
                           offscreen_texture_pool_mb=512,
                           offscreen_virtual_shadow_cache_pages=1024,
                           full_original_profile_reverified=False)

    def case_generator(self, factory):
        rig = self.rig
        for actor in rig.fixtures:
            if valid(actor):
                actor.destroy_actor()
        rig.fixtures, rig.targets = [], []
        rig.trace, rig.events, rig.data = [], [], {}
        rig.controller.stop_movement()
        rig.movement.stop_movement_immediately()
        half = rig.pawn.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
        rig.pawn.set_actor_location(unreal.Vector(0, -400, half + 2), False, True)
        rig.pawn.set_actor_rotation(unreal.Rotator(yaw=90), True)
        rig.origin = rig.pawn.get_actor_location()
        rig.ground_cache = {}
        yield 2.5  # The fixture teleport must settle before measuring a stopped camera switch.
        rig.update_player()
        rig.origin = rig.pawn.get_actor_location()
        self.case_started = rig.now
        yield from factory(rig)

    def advance(self):
        if self.rig and self.rig.trace:
            hero = hero_name(self.rig)
            contract = HERO_PROFILES[hero]['presentation_contract']['quality_gate']
            latest = self.rig.latest
            self.rig.check(not latest['cloth_disabled'] and not latest['cloth_suspended'],
                           hero + ' retains active cloth simulation')
            for cloth in latest['cloth']:
                for key, limit in contract['cloth_limits'].items():
                    self.rig.check(cloth[key] <= limit, hero + ' cloth stays within the approved ' + key)
            for effect in latest['effects']:
                if effect['active'] and effect['particles'] > 0:
                    for emitter in effect.get('render_emitters', []):
                        if emitter.get('renders_surface', True) and emitter['particles'] > 0:
                            self.rig.check(not any('WorldGridMaterial' in m or 'DefaultMaterial' in m
                                                   for m in emitter['materials']),
                                           'active skill surfaces do not use placeholder materials')
        super().advance()


if __name__ == '__main__':
    runtime = TrainingRunner()
    runtime.start()
