"""PIE in the dark training room: key 3 -> Gideon, basic combo and Q W E R A at the nearest dummy, Black Hole cancel by switching.
Reads results from the editor log (GIDEON_* and 'Kwang hit' lines). Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
state = {'phase': 'load', 'wall': time.monotonic(), 'step': 0, 'until': 0.0, 'log': []}


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def key(world, name):
    command(world, f'CountessInputQA.Key {name} Press')
    command(world, f'CountessInputQA.Key {name} Release')


def aim(world, point):
    command(world, f'CountessComboQA.Mouse Move Left {point.x} {point.y} {point.z}')


def snapshot(world, pawn, label):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    state['log'].append({'label': label, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
        'pawn': pawn.get_class().get_name(), 'pawn_location': vec(pawn.get_actor_location()),
        'dummies': [{'name': d.get_name(), 'location': vec(d.get_actor_location())} for d in dummies]})


def target_point(world, pawn):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    here = pawn.get_actor_location()
    nearest = min(dummies, key=lambda d: (d.get_actor_location() - here).length())
    location = nearest.get_actor_location()
    # 커서는 허수아비 발밑 바닥을 가리킨다(캡슐 반높이 90).
    return unreal.Vector(location.x, location.y, location.z - 90), nearest.get_name()


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'gideon-skills.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


# (이전 단계 뒤 기다릴 게임 초, 이름, 동작)
def build_steps():
    def switch(world, pawn):
        key(world, 'Three')

    def capture(name):
        # PROBE_NO_SHOTS=1 = 화면을 저장하지 않는다(판정은 로그·json으로 — 사진을 남기지 않으면 지울 일도, 지울 때 승인창도 없다, 10-20).
        if os.environ.get('PROBE_NO_SHOTS') == '1':
            return lambda world, pawn: None
        return lambda world, pawn: command(world, f'CharacterVisualQA.Capture {name}')

    def at_dummy(key_name):
        def run(world, pawn):
            point, name = target_point(world, pawn)
            state['log'].append({'label': f'aim {key_name}', 'target': name, 'point': vec(point)})
            aim(world, point)
            key(world, key_name)
        return run

    def basic_press(world, pawn):
        # 플레이어처럼 좌클릭을 누른 채 두어 SaveAttack 시점마다 다음 타로 잇는다.
        point, name = target_point(world, pawn)
        state['basic_point'] = point
        state['log'].append({'label': 'aim basic', 'target': name, 'point': vec(point)})
        command(world, f'CountessComboQA.Mouse Press Left {point.x} {point.y} {point.z}')

    def basic_release(world, pawn):
        point = state['basic_point']
        command(world, f'CountessComboQA.Mouse Release Left {point.x} {point.y} {point.z}')

    def near_floor(ahead, side):
        # 몸 기준 (앞 ahead, 오른쪽 side) 바닥(10-19 「바닥에 쏘면 이상한 곳으로 튄다」). 로그 GIDEON_BASIC yaw와 몸→조준 각을 비교한다.
        def point_of(pawn):
            here = pawn.get_actor_location()
            forward = pawn.get_actor_forward_vector()
            right = unreal.Vector(-forward.y, forward.x, 0)
            return here + forward * ahead + right * side + unreal.Vector(0, 0, -96)
        def press(world, pawn):
            point = point_of(pawn)
            state['near_point'] = point
            state['log'].append({'label': f'aim near {ahead},{side}', 'pawn': vec(pawn.get_actor_location()), 'point': vec(point)})
            command(world, f'CountessComboQA.Mouse Press Left {point.x} {point.y} {point.z}')
        def release(world, pawn):
            point = state['near_point']
            command(world, f'CountessComboQA.Mouse Release Left {point.x} {point.y} {point.z}')
        return press, release

    def away_floor(key_name, distance):
        # 가장 가까운 허수아비 반대쪽 빈 바닥(10-19 S 「안 맞았는데도 맞은 이펙트」). 기대 = 투사체 멈춤 로그 effect=None.
        def run(world, pawn):
            point, name = target_point(world, pawn)
            here = pawn.get_actor_location()
            away = unreal.Vector(here.x - point.x, here.y - point.y, 0)
            away = away * (1.0 / max(away.length(), 1.0))
            chosen = here + away * distance + unreal.Vector(0, 0, -96)
            state['log'].append({'label': f'aim {key_name} away', 'point': vec(chosen)})
            aim(world, chosen)
            key(world, key_name)
        return run

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    def offset_aim(key_name, along, side):
        # 허수아비 기준 (시전자 쪽 along, 옆 side) 만큼 떨어진 바닥을 고른다.
        def run(world, pawn):
            point, name = target_point(world, pawn)
            here = pawn.get_actor_location()
            forward = unreal.Vector(point.x - here.x, point.y - here.y, 0)
            forward = forward * (1.0 / max(forward.length(), 1.0))
            right = unreal.Vector(-forward.y, forward.x, 0)
            chosen = point - forward * along + right * side
            projected = unreal.NavigationSystemV1.project_point_to_navigation(world, chosen, None, None,
                unreal.Vector(100, 100, 250))
            state['log'].append({'label': f'aim {key_name}', 'target': name, 'point': vec(chosen),
                                 'nav': str(projected)})
            aim(world, chosen)
            key(world, key_name)
        return run

    def note(label):
        return lambda world, pawn: snapshot(world, pawn, label)

    steps = [
        (0.0, 'start', note('start')),
        (0.0, 'switch', switch),
        (0.8, 'gideon', note('gideon')),
        (0.0, 'shot_idle', capture('gideon_idle')),
        (0.2, 'basic_press', basic_press), (1.2, 'shot_basic', capture('gideon_basic')),
        (1.6, 'basic_release', basic_release),
        (0.8, 'basic_near', near_floor(60, 110)[0]), (0.15, 'basic_near_release', near_floor(60, 110)[1]),
        # 10-20부터 S는 대상 지정: 빈 바닥을 찍으면 안 나가야 한다(기대 = GIDEON_SKILL rejected=No target). 허수아비를 찍으면 6발.
        (0.8, 'S_away', away_floor('S', 600)), (1.0, 'after_s', note('after_s')),
        (0.2, 'S_dummy', at_dummy('S')), (1.4, 'after_s_dummy', note('after_s_dummy')),
        (1.0, 'reset_q', reset), (0.0, 'Q', at_dummy('Q')), (0.6, 'shot_q', capture('gideon_q')),
        (1.6, 'reset_w', reset), (0.0, 'W', at_dummy('W')), (0.9, 'shot_w', capture('gideon_w')),
        (2.0, 'reset_a', reset), (0.0, 'A', at_dummy('A')), (0.5, 'shot_a', capture('gideon_a')), (1.5, 'shot_a_dot', capture('gideon_a_dot')),
        (2.0, 'before_e', note('before_e')),
        # 10-18부터 순간이동은 Space, 블랙홀은 V(단계 이름은 예전 그대로 둔다).
        (0.0, 'E', offset_aim('SpaceBar', 250, 0)), (0.3, 'shot_e_portal', capture('gideon_e_portal')),
        (1.2, 'after_e', note('after_e')), (0.0, 'shot_e_after', capture('gideon_e_after')),
        (0.5, 'reset_r', reset), (0.0, 'R', offset_aim('V', 0, 220)), (1.5, 'shot_r', capture('gideon_r')), (0.1, 'during_r', note('during_r')),
        # 10-20 V 시전 시간 +0.7초(블랙홀이 1.2 → 1.9초에 열림) — 끝난 뒤 다시 쓰기·열린 뒤 끊기가 되게 기다림도 0.7초씩 늘림.
        (3.7, 'after_r', note('after_r')), (0.0, 'shot_r_end', capture('gideon_r_end')),
        (0.5, 'R_again', at_dummy('V')), (2.2, 'cancel', lambda world, pawn: key(world, 'One')),
        (0.6, 'after_cancel', note('after_cancel')),
        (0.2, 'back', switch), (0.8, 'back_gideon', note('back_gideon')),
        # Dekker 효과로 만든 새 E(Star Line)·R(Star Cage)·D(Sky Lance). 허수아비 복귀(1.5초) 뒤에 쏜다.
        (1.6, 'reset_line', reset), (0.0, 'line', at_dummy('E')), (0.8, 'shot_line', capture('gideon_line')),
        (1.0, 'reset_cage', reset), (0.0, 'cage', at_dummy('R')), (2.6, 'shot_cage', capture('gideon_cage')),
        (1.4, 'reset_sky', reset), (0.0, 'sky', at_dummy('D')), (1.4, 'shot_sky', capture('gideon_sky')),
        (1.6, 'after_new', note('after_new')),
        # 쿨타임: 무시를 끄고 Q를 시전 직후(0.8초)와 쿨 4초가 지난 뒤 다시 누른다. 기대 = 거절 1 · 시전 1
        (0.0, 'cooldown_on', lambda world, pawn: command(world, 'Gideon.Skills.IgnoreCooldowns 0')),
        (0.2, 'cd_q1', at_dummy('Q')), (0.8, 'cd_q2', at_dummy('Q')), (3.4, 'cd_q3', at_dummy('Q')),
        # Q 운석은 0.35초에 떠나 0.71초 떨어진다(10-18 바닥 마법진으로 높이 1500). 닿을 때까지 기다린다.
        (1.5, 'end', note('end')),
    ]
    return steps


STEPS = build_steps()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300:
            raise TimeoutError('Gideon skill probe timed out')
        if state['phase'] == 'load':
            unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            state['phase'] = 'navwait'
            return
        if state['phase'] == 'navwait':
            # 불러온 직후 내비메시를 만드는 중이면 PIE 사본에 내비가 없다. 시작점이 내비에 투영될 때까지 기다린다.
            editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0].get_actor_location()
            if time.monotonic() - state['wall'] < 2 or unreal.NavigationSystemV1.is_navigation_being_built(editor_world):
                return
            projected = unreal.NavigationSystemV1.project_point_to_navigation(editor_world, start - unreal.Vector(0, 0, 90),
                None, None, unreal.Vector(100, 100, 250))
            if projected is None and time.monotonic() - state['wall'] < 90:
                return
            state['log'].append({'label': 'editor_nav', 'start': vec(start), 'projected': str(projected),
                                 'waited': round(time.monotonic() - state['wall'], 1)})
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'run'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn or unreal.NavigationSystemV1.is_navigation_being_built(world):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['step'] == 0 and now < 4:
            return
        if state['step'] == 0 and 'configured' not in state:
            command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
            command(world, 'Gideon.Skills.IgnoreCooldowns 1')
            # A 기본이 광선 시안(7)으로 바뀌어(10-20) 이 검사가 보는 원래 Burden을 0으로 고정한다.
            command(world, 'Gideon.Skills.ANew 0')
            state['configured'] = True
        if now < state['until']:
            return
        if state['step'] >= len(STEPS):
            finish()
            return
        delay, name, action = STEPS[state['step']]
        if 'armed' not in state:
            state['armed'] = True
            state['until'] = now + delay
            return
        del state['armed']
        unreal.log(f'GIDEON_PROBE step={name}')
        action(world, pawn)
        state['step'] += 1
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
