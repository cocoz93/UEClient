"""Native PIE viewport captures; visual acceptance is a separate human review."""
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from sparrow_runtime import run, assert_bow_effect_attachment


def visible_effect(rig, fragment):
    return any(fragment in effect['template'] and effect['active'] and effect['particles'] > 0
               for effect in rig.latest.get('effects', []))


def idle(rig):
    yield 0.45
    rig.check(rig.latest['speed'] < 1.0 and rig.latest.get('run_weight', 1.0) < 0.05,
              'idle capture uses the actual standing locomotion pose')
    yield rig.capture('idle')


def moving(rig):
    yield from rig.click('Right', rig.ground(0, 650))
    yield 0.3
    rig.check(rig.latest['speed'] > 100.0 and rig.latest.get('run_weight', 0.0) > 0.5,
              'moving capture uses an actual navigation run pose')
    yield rig.capture('move')


def attack(rig):
    target = rig.dummy(800)
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'presentation bow attack starts')
    yield rig.until(lambda: bool(rig.arrows()), 0.5, 'presentation bow release creates its projectile')
    yield 0.05
    rig.check(rig.latest['attacking'] and rig.latest['projectiles'], 'attack capture includes the bow montage and flying arrow')
    rig.check(any(effect['particles'] > 0 for effect in rig.latest['effects']), 'attack emits live original particles')
    yield rig.capture('bow-release')


def hail(rig):
    target = rig.dummy(550)
    yield from rig.skill_key('Q', target.get_actor_location())
    yield 0.08
    rig.check(rig.component.is_casting(), 'Q casting pose is active before area release')
    yield rig.capture('q-cast')
    yield rig.until(lambda: rig.component.get_active_hail_count() > 0, 0.8, 'Q rain area is released')
    yield 0.15
    launch = [effect for effect in rig.latest['effects'] if 'RainofArrowsProj' in effect['template']]
    rig.check(launch and launch[0]['position'][2] > rig.latest['arrow_origin'][2] + 100.0,
              'Q visual launch travels upward in world space from the bow')
    rig.data['upward_launch_position'] = launch[0]['position']
    # 원본 강우의 방출 지연과 낙하 시간을 지난 뒤 실제 지면 강우를 캡처한다.
    yield 0.95
    rig.check(visible_effect(rig, 'RainofArrows') or visible_effect(rig, 'RainArrows'),
              'Q area capture contains active original arrow-rain particles')
    rain = [effect for effect in rig.latest['effects']
            if 'RainofArrows' in effect['template'] and 'Proj' not in effect['template']]
    rig.check(rain and any(emitter['name'].startswith('Impact') and emitter['particles'] > 0
                         for emitter in rain[0].get('emitters', [])),
              'Q falling arrows create actual collision-event impact particles')
    rig.data['rain_emitter_state'] = rain[0].get('emitters', [])
    yield rig.capture('q-arrow-rain')


def piercing(rig):
    target = rig.dummy(1000)
    yield from rig.skill_key('W', target.get_actor_location())
    yield 0.4
    rig.check(rig.component.is_casting() and not rig.arrows(), 'W capture shows the held charge before projectile release')
    rig.check(visible_effect(rig, 'Sparrow_RMB'), 'W charge uses its original default Sparrow particles')
    assert_bow_effect_attachment(rig, 'P_Sparrow_RMB')
    yield rig.capture('w-charge')
    yield rig.until(lambda: bool(rig.arrows()), 1.2, 'charged W releases its projectile for capture')
    yield 0.033
    rig.check(rig.latest['projectiles'], 'W release capture contains a moving projectile')
    yield rig.capture('w-release')


def inner_fire(rig):
    target = rig.dummy(1100)
    yield from rig.skill_key('R', target.get_actor_location())
    yield rig.until(rig.component.is_inner_fire_active, 0.5, 'R buff activates before capture')
    yield rig.idle()
    rig.check(visible_effect(rig, 'SparrowBuff'), 'R persistent buff uses active original particles')
    assert_bow_effect_attachment(rig, 'P_SparrowBuff')
    yield rig.capture('r-buff')
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'R presentation starts a buffed bow attack')
    yield rig.until(lambda: len(rig.arrows()) == 3, 0.5, 'R emits all three lanes before capture')
    yield 0.05
    rig.check(rig.latest.get('montage_sequence') == 'R_Ability_Med_Fire',
              'buffed basic input plays the dedicated original R firing sequence')
    rig.check(len(rig.latest['projectiles']) == 3, 'R attack capture includes three distinct flying arrows')
    rig.check(visible_effect(rig, 'Sparrow_UltArrow'), 'R arrows use active original ultimate trail particles')
    yield rig.capture('r-three-arrows')
    yield rig.component.get_buff_remaining() + 0.6
    rig.check(not rig.component.is_inner_fire_active() and not rig.arrows(), 'presentation leaves no expired buff or projectile')
    rig.check(not any(effect['active'] or effect['particles'] > 0 for effect in rig.latest['effects']),
              'temporary presentation particles finish and clean up')


runtime = run('sparrow_presentation', [('idle', idle), ('move', moving), ('bow_attack', attack),
                                     ('q_arrow_rain', hail), ('w_piercing_charge', piercing),
                                     ('r_inner_fire', inner_fire)])
