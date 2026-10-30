"""PIE in the dark training room: key 4 -> Aurora, walk to a dummy, melee combo, Q W E R, cancel by switching, cooldown.
Reads results from the editor log (AURORA_* and 'Kwang hit' lines) plus pelvis heights recorded here. Saves no assets."""
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
    # 발밑(캡슐 바닥) 기준 골반 높이. 서 있으면 약 112, 전신 동작이 붙으면 그 동작의 자세를 따라간다.
    mesh = pawn.get_editor_property('mesh')
    feet = pawn.get_actor_location().z - 96
    return round(mesh.get_socket_location('pelvis').z - feet, 1)


def snapshot(world, pawn, label):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    state['log'].append({'label': label, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
        'pawn': pawn.get_class().get_name(), 'pawn_location': vec(pawn.get_actor_location()),
        'pelvis': pelvis_height(pawn),
        'walk': round(pawn.get_editor_property('character_movement').get_editor_property('max_walk_speed'), 1),
        'dummies': [{'name': d.get_name(), 'location': vec(d.get_actor_location())} for d in dummies]})


def nearest_dummy(world, pawn):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    here = pawn.get_actor_location()
    return min(dummies, key=lambda d: (d.get_actor_location() - here).length())


def target_point(world, pawn):
    nearest = nearest_dummy(world, pawn)
    location = nearest.get_actor_location()
    # 커서는 허수아비 발밑 바닥을 가리킨다(캡슐 반높이 90).
    return unreal.Vector(location.x, location.y, location.z - 90), nearest.get_name()


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'aurora-skills.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


# (이전 단계 뒤 기다릴 게임 초, 이름, 동작)
def build_steps():
    def switch(world, pawn):
        key(world, 'Four')

    def capture(name):
        return lambda world, pawn: command(world, f'CharacterVisualQA.Capture {name}')

    def note(label):
        return lambda world, pawn: snapshot(world, pawn, label)

    def walk_near(distance):
        # 가장 가까운 허수아비 앞(시전자 쪽) distance 만큼 떨어진 바닥으로 우클릭 이동한다.
        def run(world, pawn):
            point, name = target_point(world, pawn)
            here = pawn.get_actor_location()
            back = unreal.Vector(here.x - point.x, here.y - point.y, 0)
            back = back * (1.0 / max(back.length(), 1.0))
            goal = point + back * distance
            state['log'].append({'label': 'walk', 'target': name, 'goal': vec(goal)})
            command(world, f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            command(world, f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        return run

    def at_dummy(key_name):
        def run(world, pawn):
            point, name = target_point(world, pawn)
            state['log'].append({'label': f'aim {key_name}', 'target': name, 'point': vec(point)})
            aim(world, point)
            key(world, key_name)
        return run

    def at_far_dummy(key_name):
        def run(world, pawn):
            dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
            here = pawn.get_actor_location()
            far = sorted(dummies, key=lambda d: (d.get_actor_location() - here).length())[-1]
            location = far.get_actor_location()
            point = unreal.Vector(location.x, location.y, location.z - 90)
            state['log'].append({'label': f'aim {key_name}', 'target': far.get_name(), 'point': vec(point)})
            aim(world, point)
            key(world, key_name)
        return run

    def offset_aim(key_name, along, side):
        # 허수아비 기준 (시전자 쪽 along, 옆 side) 만큼 떨어진 바닥을 고른다.
        def run(world, pawn):
            point, name = target_point(world, pawn)
            here = pawn.get_actor_location()
            forward = unreal.Vector(point.x - here.x, point.y - here.y, 0)
            forward = forward * (1.0 / max(forward.length(), 1.0))
            right = unreal.Vector(-forward.y, forward.x, 0)
            chosen = point - forward * along + right * side
            state['log'].append({'label': f'aim {key_name}', 'target': name, 'point': vec(chosen)})
            aim(world, chosen)
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

    def hurt(amount):
        # 플레이어에게 직접 피해를 넣는다(수련장에 때리는 적이 없다). 실제로 들어간 값은 AURORA_TAKE 로그로 본다.
        return lambda world, pawn: unreal.GameplayStatics.apply_damage(pawn, float(amount), None, None, unreal.DamageType)

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    steps = [
        (0.0, 'start', note('start')),
        (0.0, 'switch', switch),
        (0.8, 'aurora', note('aurora')),
        (0.0, 'shot_idle', capture('aurora_idle')),
        (0.0, 'walk', walk_near(170)), (3.5, 'arrived', note('arrived')),
        (0.0, 'basic_press', basic_press), (0.6, 'shot_basic', capture('aurora_basic')),
        (2.0, 'basic_release', basic_release),
        # E 빙결: 0.5초 = 내려찍은 자세(골반 약 45)
        (1.2, 'reset_e', reset), (0.0, 'E', at_dummy('E')), (0.5, 'pose_e', note('pose_e')), (0.0, 'shot_e', capture('aurora_e')),
        # 10-18 회오리 절반 속도: 1.2초엔 아직 돌고, 1.65초엔 오므라드는 중(1.75초에 깨짐과 함께 사라짐)
        (0.7, 'shot_e_swirl', capture('aurora_e_swirl')), (0.45, 'shot_e_end', capture('aurora_e_end')),
        (0.35, 'after_e', note('after_e')),
        # R 궁극기: 1.3초 = 착지 직후, 2.6초 = 얼음 폭발 뒤
        (0.5, 'reset_r', reset), (0.0, 'R', at_dummy('V')), (0.8, 'shot_r_glow', capture('aurora_r_glow')), (0.5, 'pose_r', note('pose_r')), (0.0, 'shot_r', capture('aurora_r')),
        (1.3, 'shot_r_burst', capture('aurora_r_burst')), (1.0, 'after_r', note('after_r')),
        # 돌진(10-21부터 Space): 허수아비를 지나가도록 그 너머를 겨눈다
        (0.5, 'reset_w', reset), (0.0, 'W', offset_aim('SpaceBar', -400, 0)), (0.25, 'shot_w', capture('aurora_w')),
        (0.2, 'during_w', note('during_w')), (1.2, 'after_w', note('after_w')), (0.0, 'shot_w_after', capture('aurora_w_after')),
        # 도약(10-21부터 W, 대상 지정): 허수아비 앞으로 돌아가 허수아비 머리 위에 나타났다 바로 앞에 내려서고, 분신이 떠난 자리에 남아
        # 1.5초 뒤 부서진다
        (0.5, 'walk_q', walk_near(170)), (2.5, 'reset_q', reset), (0.0, 'before_q', note('before_q')),
        (0.0, 'Q', at_dummy('W')),
        (0.35, 'shot_q', capture('aurora_q')), (0.0, 'during_q', note('during_q')),
        # 10-18 끝 섞기: 0.75초에 시전이 끝나고 0.25초 동안 보행 자세로 섞인다 → 0.8초(착지 자세)·0.95초(섞이는 중)
        (0.45, 'shot_q_land', capture('aurora_q_land')), (0.0, 'land_q', note('land_q')),
        (0.15, 'shot_q_blend', capture('aurora_q_blend')), (0.0, 'blend_q', note('blend_q')),
        (0.6, 'after_q', note('after_q')), (0.4, 'shot_q_decoy', capture('aurora_q_decoy')), (1.2, 'after_decoy', note('after_decoy')),
        # A 얼음 갑옷(10-18 다시 짬, 단계 이름은 예전 그대로): 1.12초에 켜져 12초(10-19 6 → 12) 동안 받는 피해 × 0.6.
        # 수련장에 때리는 적이 없어 시험이 직접 피해 100을 넣는다 → AURORA_TAKE 전 100 · 중 60 · 끝난 뒤(F 뒤, 약 17초) 100
        (0.3, 'walk_a', walk_near(170)), (2.5, 'hurt_before_a', hurt(100)), (0.0, 'A', at_dummy('A')),
        # 10-18 Recall 끝까지(1.3배): 칼이 꽂히는 1.12초에 켜지고 0.15초에 다 부푼다 → 1.4초에 찍고 때린다
        (1.4, 'shot_a', capture('aurora_a')), (0.0, 'hurt_during_a', hurt(100)),
        (0.6, 'shot_a_burst', capture('aurora_a_burst')), (0.0, 'after_a', note('after_a')),
        # S 서리 가속(10-18 다시 짬): 발밑 장판 9초(10-19 6 → 9), 안에 있으면 이동 600 → 780(AURORA_HASTE on/off walk=)
        (0.3, 'walk_s', walk_near(170)), (2.5, 'reset_s', reset), (0.0, 'before_s', note('before_s')),
        (0.0, 'S', at_dummy('S')), (0.8, 'shot_s', capture('aurora_s')), (0.0, 'during_s', note('during_s')),
        (1.2, 'shot_s_glow', capture('aurora_s_glow')), (1.5, 'shot_s_glow2', capture('aurora_s_glow2')),
        (2.9, 'after_s', note('after_s')),
        # D 얼음 가시 줄: 허수아비 쪽으로 일직선
        (0.3, 'reset_d', reset), (0.0, 'D', at_dummy('D')), (0.5, 'shot_d', capture('aurora_d')), (1.0, 'after_d', note('after_d')),
        # F 얼음 창: 가장 먼 허수아비(약 1000)로 던져 나는 모습(0.6초)과 박히는 모습(0.9초)을 찍는다
        (0.3, 'reset_f', reset), (0.0, 'F', at_far_dummy('F')), (0.6, 'shot_f', capture('aurora_f')),
        (0.3, 'shot_f_hit', capture('aurora_f_hit')), (1.0, 'after_f', note('after_f')),
        # F 빈 곳으로: 허수아비 반대쪽 멀리 던져 창 몸통이 나는 모습(던진 뒤 0.25초)을 찍는다
        (0.0, 'F_empty', offset_aim('F', 900, 0)), (0.65, 'shot_f_fly', capture('aurora_f_fly')), (1.0, 'after_f_empty', note('after_f_empty')),
        (0.0, 'hurt_after_a', hurt(100)),
        # 10-18 새 스킬: Q 서리 검기(안 언 허수아비 → 30), R 냉기 장판(0.5초마다 6 × 7번 + 4.35초에 20·STUN),
        # 장판으로 언 허수아비를 Q로 깨뜨림(→ 60, shattered=1)
        (0.3, 'walk_qr', walk_near(170)), (2.5, 'reset_qr', reset),
        (0.0, 'Q_slash', at_dummy('Q')), (0.5, 'shot_q_slash', capture('aurora_q_slash')),
        # R 채널링(10-18): 0.35초에 시작해 2초 버팀 → 0.25초마다 창 8개(5씩) + 끝에 20·STUN. 끝은 R 뒤 약 2.4초
        # 10-19 저녁 4초로(파편 16번) → 끝은 R 뒤 약 4.4초
        (0.6, 'R_field', at_dummy('R')), (1.5, 'shot_r_field', capture('aurora_r_field')),
        (2.95, 'shot_r_field_end', capture('aurora_r_field_end')),
        # 체력만 채우고(얼림 기록은 스킬 쪽에 남는다) 깨뜨린다 → 피해 60이 다 찍혀야 한다
        (0.1, 'reset_shatter', reset), (0.1, 'Q_shatter', at_dummy('Q')), (0.5, 'shot_q_shatter', capture('aurora_q_shatter')),
        # R 채널링 끊기: 0.8초에 D를 누르면 장판이 멈추고(AURORA_FIELD cancelled reason=skill, 얼림 없음) D가 바로 나간다
        (0.6, 'R_cancel', at_dummy('R')), (0.8, 'D_interrupt', at_dummy('D')), (1.0, 'after_r_cancel', note('after_r_cancel')),
        # 10-18 밤 시안 촬영: Q 바닥(기본 3 눈 덮임 말고 QGround 1 서리 자국 · 2 얼음 균열 · 0 얼음 결정),
        # R 버티는 자세(RChannel 1 겨눔 · 2 휘둘러 가리킴 두 번)
        (0.2, 'qg1', lambda world, pawn: command(world, 'Aurora.FX.QGround 1')), (0.1, 'Q_g1', at_dummy('Q')),
        (0.55, 'shot_q_g1', capture('aurora_q_g1')),
        (0.6, 'qg2', lambda world, pawn: command(world, 'Aurora.FX.QGround 2')), (0.1, 'Q_g2', at_dummy('Q')),
        (0.55, 'shot_q_g2', capture('aurora_q_g2')),
        (0.6, 'qg0', lambda world, pawn: command(world, 'Aurora.FX.QGround 0')), (0.1, 'Q_g0', at_dummy('Q')),
        (0.55, 'shot_q_g0', capture('aurora_q_g0')),
        (0.6, 'qg3', lambda world, pawn: command(world, 'Aurora.FX.QGround 3')),
        (0.0, 'rc1', lambda world, pawn: command(world, 'Aurora.FX.RChannel 1')), (0.1, 'R_c1', at_dummy('R')),
        (1.2, 'shot_r_c1', capture('aurora_r_c1')), (1.4, 'rc2', lambda world, pawn: command(world, 'Aurora.FX.RChannel 2')),
        (0.1, 'R_c2', at_dummy('R')), (0.85, 'shot_r_c2a', capture('aurora_r_c2a')), (0.35, 'shot_r_c2b', capture('aurora_r_c2b')),
        (1.4, 'rc0', lambda world, pawn: command(world, 'Aurora.FX.RChannel 9')),
        # 시전 중 캐릭터 전환 = 취소. 돌아온 몸은 서 있는 자세여야 한다
        (0.5, 'R_again', at_dummy('V')), (0.6, 'cancel', lambda world, pawn: key(world, 'One')),
        (0.6, 'after_cancel', note('after_cancel')),
        (0.2, 'back', switch), (0.8, 'back_aurora', note('back_aurora')),
        # 쿨타임: 무시를 끄고 E를 시전 직후(1.5초)와 쿨 8초가 지난 뒤 다시 누른다. 기대 = 거절 1 · 시전 2
        (0.0, 'cooldown_on', lambda world, pawn: command(world, 'Aurora.Skills.IgnoreCooldowns 0')),
        (0.2, 'cd_e1', at_dummy('E')), (1.5, 'cd_e2', at_dummy('E')), (6.8, 'cd_e3', at_dummy('E')),
        (1.6, 'end', note('end')),
    ]
    return steps


STEPS = build_steps()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300:
            raise TimeoutError('Aurora skill probe timed out')
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
