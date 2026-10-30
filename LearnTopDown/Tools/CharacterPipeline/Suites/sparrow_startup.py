"""Initial Sparrow PIE pawn and its first real controller input, without a reset."""
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from sparrow_runtime import Runner, distance2d, xyz
from context import fps


class StartupRunner(Runner):
    def case_generator(self, factory):
        # 맵이 최초 생성한 Pawn과 애니메이션을 그대로 검사한다. 재생·중단·위치 초기화를 하지 않는다.
        rig = self.rig
        rig.trace = []
        rig.events = []
        rig.data = {'original_pie_pawn': rig.pawn.get_name(), 'pawn_respawned': False,
                    'preparation_montage_stop_used': False, 'forced_intro_playback': False}
        self.case_started = rig.now
        yield from factory(rig)


def initial_pawn_first_input(rig):
    yield 0.2
    before = dict(rig.latest)
    rig.check(not before['attacking'] and not before['casting'],
              'initial map pawn is in a non-combat state before its first input')
    rig.data['before_first_input'] = before
    rig.data['initial_montage_name'] = before['montage']
    rig.data['initial_intro_observation'] = 'absent' if not before['montage'] else 'observed'
    rig.data['named_level_start_intro_observed'] = before['montage'] == 'LevelStart_Montage'

    rig.key('Press', 'SpaceBar')
    yield 1.0 / fps
    rig.key('Release', 'SpaceBar')
    rig.check(rig.latest['montage'] == '', 'the first controller AnyKey input leaves no active startup montage')
    rig.check(not rig.pawn.is_combat_busy(), 'first AnyKey input does not leave a combat lock')
    rig.data['after_any_key_input'] = dict(rig.latest)
    after_key_time = rig.now - rig.runner.case_started

    start = rig.pawn.get_actor_location()
    goal = rig.ground(0, 650)
    yield from rig.click('Right', goal)
    selected_goal = rig.assert_cursor_goal(goal)
    yield 0.35
    rig.check(rig.latest['speed'] > 100.0 and rig.latest.get('run_weight', 0.0) > 0.5,
              'first live right-click input produces physical movement and the actual run pose')
    rig.check(distance2d(start, rig.pawn.get_actor_location()) > 100.0,
              'the original PIE pawn changes position after its first navigation input')
    rig.check(rig.latest['montage'] == '', 'first movement does not slide under an active startup montage')
    rig.data['first_movement'] = {'from': xyz(start), 'position': xyz(rig.pawn.get_actor_location()),
        'speed': rig.latest['speed'], 'run_weight': rig.latest.get('run_weight'),
        'montage': rig.latest['montage'], 'displacement_cm': distance2d(start, rig.pawn.get_actor_location())}

    yield rig.until(lambda: rig.latest['speed'] < 1.0 and rig.latest.get('run_weight', 1.0) < 0.05,
                    4.0, 'first navigation request arrives and restores the actual idle pose')
    rig.check(distance2d(rig.pawn.get_actor_location(), selected_goal) < 22.0,
              'original startup pawn reaches the actual selected navigation goal')
    rig.check(all(sample['montage'] == '' for sample in rig.trace if sample['elapsed'] >= after_key_time),
              'no startup montage resumes during first movement or arrival')
    rig.check(rig.latest['audio_components'] == 0, 'startup and first input spawn no audio components')
    rig.data['arrival'] = dict(rig.latest)


runtime = StartupRunner('sparrow_startup', [('original_map_pawn_first_input', initial_pawn_first_input)])
runtime.start()
