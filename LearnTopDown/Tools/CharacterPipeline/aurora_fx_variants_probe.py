"""PIE in the dark training room: Aurora 3rd-round review shots at the game camera.
Basic attack (faster swing + what appears in front), Q recovery (pelvis right after landing), E swirl layers,
W path variants (Aurora.FX.WTrail 0..3) and R variants (Aurora.FX.RStyle 0..3). Saves no assets."""
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


def pelvis_height(pawn):
    mesh = pawn.get_editor_property('mesh')
    return round(mesh.get_socket_location('pelvis').z - (pawn.get_actor_location().z - 96), 1)


def target_point(world, pawn):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    here = pawn.get_actor_location()
    nearest = min(dummies, key=lambda d: (d.get_actor_location() - here).length())
    location = nearest.get_actor_location()
    return unreal.Vector(location.x, location.y, location.z - 90)


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'aurora-fx-variants.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def build_steps():
    def capture(name):
        return lambda world, pawn: command(world, f'CharacterVisualQA.Capture {name}')

    def note(label):
        def run(world, pawn):
            state['log'].append({'label': label, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
                                 'pawn_location': vec(pawn.get_actor_location()), 'pelvis': pelvis_height(pawn)})
        return run

    def walk_near(distance):
        def run(world, pawn):
            point = target_point(world, pawn)
            here = pawn.get_actor_location()
            back = unreal.Vector(here.x - point.x, here.y - point.y, 0)
            back = back * (1.0 / max(back.length(), 1.0))
            goal = point + back * distance
            command(world, f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            command(world, f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        return run

    def at_dummy(key_name):
        def run(world, pawn):
            aim(world, target_point(world, pawn))
            key(world, key_name)
        return run

    def offset_aim(key_name, along, side):
        def run(world, pawn):
            point = target_point(world, pawn)
            here = pawn.get_actor_location()
            forward = unreal.Vector(point.x - here.x, point.y - here.y, 0)
            forward = forward * (1.0 / max(forward.length(), 1.0))
            right = unreal.Vector(-forward.y, forward.x, 0)
            aim(world, point - forward * along + right * side)
            key(world, key_name)
        return run

    def basic_press(world, pawn):
        point = target_point(world, pawn)
        state['basic_point'] = point
        command(world, f'CountessComboQA.Mouse Press Left {point.x} {point.y} {point.z}')

    def basic_release(world, pawn):
        point = state['basic_point']
        command(world, f'CountessComboQA.Mouse Release Left {point.x} {point.y} {point.z}')

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    def cvar(text):
        return lambda world, pawn: command(world, text)

    steps = [
        (0.0, 'switch', lambda world, pawn: key(world, 'Four')),
        (0.8, 'walk', walk_near(170)), (3.5, 'arrived', note('arrived')),
        # 평타: 1.35배 → 타격 약 0.19초. 그 앞뒤를 찍어 캐릭터 앞에 생기는 것을 본다
        (0.0, 'basic_press', basic_press), (0.12, 'shot_basic_a', capture('basic_012')),
        (0.07, 'shot_basic_b', capture('basic_019')), (0.08, 'shot_basic_c', capture('basic_027')),
        (0.1, 'shot_basic_d', capture('basic_037')),
        (2.0, 'basic_release', basic_release),
        # Q: 0.65초 착지, 회복 0.6 → 0.75초에 시전 끝(골반 서 있음 약 112)
        (1.0, 'reset_q', reset), (0.0, 'Q', offset_aim('SpaceBar', 300, 300)), (0.62, 'shot_q_land', capture('q_land')),
        (0.0, 'q_062', note('q_062')), (0.2, 'q_082', note('q_082')), (0.0, 'shot_q_after', capture('q_after')),
        (0.5, 'walk_e', walk_near(170)), (2.5, 'reset_e', reset),
        # E: 0.25초 내려찍기 → 회오리 겹
        (0.0, 'E', at_dummy('E')), (0.35, 'shot_e_1', capture('e_035')), (0.25, 'shot_e_2', capture('e_060')),
        (0.3, 'shot_e_3', capture('e_090')),
    ]
    if os.environ.get('PROBE_SET') == 'basic_e':
        # 짧은 묶음: 눈송이(Aurora.FX.MeleeSnow)를 켠 앞 묶음과 끈 이 묶음을 같은 시각에 찍어 평타 앞에 생기는 것이 그것인지 가린다
        steps = [(0.0, 'snow_on_first', cvar('Aurora.FX.MeleeSnow 1'))] + steps + [
            (0.5, 'snow_off', cvar('Aurora.FX.MeleeSnow 0')), (0.0, 'walk_b', walk_near(170)), (2.5, 'reset_b', reset),
            (0.0, 'basic_press2', basic_press), (0.12, 'shot_nosnow_a', capture('nosnow_012')),
            (0.07, 'shot_nosnow_b', capture('nosnow_019')), (0.08, 'shot_nosnow_c', capture('nosnow_027')),
            (0.1, 'shot_nosnow_d', capture('nosnow_037')), (1.0, 'basic_release2', basic_release),
            (0.5, 'end', note('end')),
        ]
        return steps
    if os.environ.get('PROBE_SET') == 'r_skip':
        # R 착지 이펙트를 비트로 하나씩 빼 보며(Aurora.FX.RSkip) 화면 위쪽 구름이 사라지는 조합을 찾는다. 끝에 E·W 확인 사진
        steps = steps[:3]
        for mask in [int(m) for m in os.environ.get('SKIP_MASKS', '0,64,128,1,2,12,48').split(',')]:
            steps += [(1.0, f'skip{mask}_set', cvar(f'Aurora.FX.RSkip {mask}')), (0.0, f'skip{mask}_walk', walk_near(170)),
                      (2.5, f'skip{mask}_reset', reset), (0.0, f'skip{mask}_V', at_dummy('V')),
                      (1.45, f'skip{mask}_a', capture(f'skip{mask}_145')), (0.6, f'skip{mask}_b', capture(f'skip{mask}_205'))]
        steps += [(0.0, 'skip_restore', cvar('Aurora.FX.RSkip 0')), (1.0, 'walk_e', walk_near(170)), (2.5, 'E', at_dummy('E'))]
        steps += [(t, f'e_{i}', capture(f'e_check_{i}')) for i, t in enumerate((0.4, 0.3, 0.2, 0.3, 0.5))]
        steps += [(1.0, 'walk_w', walk_near(170)), (2.5, 'W', offset_aim('W', -400, 0))]
        steps += [(t, f'w_{i}', capture(f'w_check_{i}')) for i, t in enumerate((0.2, 0.12, 0.12, 0.3))]
        steps += [(1.0, 'end', note('end'))]
        return steps
    if os.environ.get('PROBE_SET') == 'r_only':
        # R(V)만 단독으로(앞에 E 없이) 써서 화면 위쪽에 생기는 구름이 R 때문인지, 그다음 E만 단독으로 써서 E 잔해인지 가른다
        steps = steps[:3] + [(0.0, 'R_alone', at_dummy('V'))]
        steps += [(t, f'shot_r_alone_{i}', capture(f'r_alone_{i}')) for i, t in enumerate((0.3, 0.5, 0.55, 0.65, 1.0))]
        steps += [(1.5, 'walk_e2', walk_near(170)), (2.5, 'E_alone', at_dummy('E'))]
        steps += [(t, f'shot_e_alone_{i}', capture(f'e_alone_{i}')) for i, t in enumerate((0.3, 0.5, 0.7, 1.0, 1.5))]
        steps += [(1.0, 'end', note('end'))]
        return steps
    if os.environ.get('PROBE_SET') == 'w_r_ground':
        # 4차 시안: W 달리기 동작(WRun)·앞쪽 얼음(WFront) 짝, R 바닥(RGround). 돌진은 0.1초에 시작해 약 0.43초 간다
        steps = steps[:3]
        for run, front in ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (2, 3)):
            tag = f'w_run{run}_front{front}'
            steps += [
                (1.0, f'{tag}_set', cvar(f'Aurora.FX.WRun {run}')), (0.0, f'{tag}_set2', cvar(f'Aurora.FX.WFront {front}')),
                (0.0, f'{tag}_walk', walk_near(170)), (2.5, f'{tag}_reset', reset), (0.0, tag, offset_aim('W', -400, 0)),
                (0.2, f'{tag}_a', capture(f'{tag}_020')), (0.12, f'{tag}_b', capture(f'{tag}_032')),
                (0.12, f'{tag}_c', capture(f'{tag}_044')), (0.3, f'{tag}_d', capture(f'{tag}_074')),
            ]
        for ground in range(5):
            steps += [
                (1.5, f'g{ground}_set', cvar(f'Aurora.FX.RGround {ground}')), (0.0, f'g{ground}_walk', walk_near(170)),
                (2.5, f'g{ground}_reset', reset), (0.0, f'G{ground}', at_dummy('V')),
                (1.35, f'shot_g{ground}_a', capture(f'g{ground}_135')), (0.4, f'shot_g{ground}_b', capture(f'g{ground}_175')),
                (0.85, f'shot_g{ground}_c', capture(f'g{ground}_260')),
            ]
        steps += [(0.0, 'restore', cvar('Aurora.FX.RGround 0')), (0.0, 'restore_run', cvar('Aurora.FX.WRun 0')),
                  (0.0, 'restore_front', cvar('Aurora.FX.WFront 0')), (1.0, 'end', note('end'))]
        return steps
    for trail in range(4):
        steps += [
            (1.0, f'w{trail}_set', cvar(f'Aurora.FX.WTrail {trail}')), (0.0, f'w{trail}_walk', walk_near(170)),
            (2.5, f'w{trail}_reset', reset), (0.0, f'W{trail}', offset_aim('W', -400, 0)),
            (0.3, f'shot_w{trail}_a', capture(f'w{trail}_030')), (0.35, f'shot_w{trail}_b', capture(f'w{trail}_065')),
            (0.5, f'shot_w{trail}_c', capture(f'w{trail}_115')),
        ]
    for style in range(4):
        steps += [
            (1.5, f'r{style}_set', cvar(f'Aurora.FX.RStyle {style}')), (0.0, f'r{style}_walk', walk_near(170)),
            (2.5, f'r{style}_reset', reset), (0.0, f'R{style}', at_dummy('V')),
            (0.8, f'shot_r{style}_a', capture(f'r{style}_080')), (0.55, f'shot_r{style}_b', capture(f'r{style}_135')),
            (0.4, f'shot_r{style}_c', capture(f'r{style}_175')), (0.85, f'shot_r{style}_d', capture(f'r{style}_260')),
        ]
    steps += [(0.0, 'restore', cvar('Aurora.FX.RStyle 3')), (0.0, 'restore_w', cvar('Aurora.FX.WTrail 1')), (1.0, 'end', note('end'))]
    return steps


STEPS = build_steps()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 400:
            raise TimeoutError('Aurora fx variants probe timed out')
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
            command(world, 'Aurora.Skills.IgnoreCooldowns 1')
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
        unreal.log(f'AURORA_PROBE step={name}')
        action(world, pawn)
        state['step'] += 1
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
