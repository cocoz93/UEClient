"""Frame sequences of Gideon W (Cosmic Rift), A (Burden), E (Torn Space), R (Black Hole) in the dark training room, plus the
lengths/notifies of their cast animations. Answers 'what does it look like over time'. Saves no assets."""
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
    (qa / 'gideon-wra.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


ANIMS = ['Torn_Space_intro', 'Torn_Space_TargetingPose', 'Torn_Space_Outro', 'PortalBlast_Loop', 'CosmicRift', 'CosmicRift_Start', 'CosmicRift_Execute', 'Cosmic_Rift', 'Cosmic_Rift_Intro', 'Burden',
         'Burden_Start', 'Burden_Loop', 'Burden_Fast', 'Burden_Start_Fast', 'Burden_slow', 'Blackhole_Start',
         'BlackHole_Loop']


def dump_anims():
    root = '/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/'
    rows = {}
    for name in ANIMS:
        anim = unreal.load_asset(root + name)
        if anim is None:
            rows[name] = None
            continue
        notifies = []
        try:
            for event in unreal.AnimationLibrary.get_animation_notify_events(anim):
                notify = event.get_editor_property('notify')
                notifies.append([str(event.get_editor_property('notify_name')),
                                 notify.get_class().get_name() if notify else None,
                                 round(event.get_editor_property('link_value'), 3)])
        except Exception as error:
            notifies = str(error)
        rows[name] = {'length': round(anim.get_play_length(), 3), 'notifies': notifies}
    (qa / 'gideon-wra-anims.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')


def build_steps():
    def switch(world, pawn):
        key(world, 'Three')
        # WRA_CONSOLE = 바꾼 뒤 실행할 콘솔 명령(; 로 구분). 예: E·R·D 시안 고르기.
        for line in [c.strip() for c in os.environ.get('WRA_CONSOLE', '').split(';') if c.strip()]:
            command(world, line)

    def capture(name):
        # WRA_NO_SHOTS=1 = 화면을 저장하지 않는다(로그만 보는 시험 — 사진을 안 남기면 지울 일도, 지울 때 승인창도 없다, 10-20).
        if os.environ.get('WRA_NO_SHOTS') == '1':
            return lambda world, pawn: None
        return lambda world, pawn: command(world, f'CharacterVisualQA.Capture {name}')

    def at_dummy(key_name):
        def run(world, pawn):
            point, name = target_point(world, pawn)
            state['log'].append({'label': f'aim {key_name}', 'target': name, 'point': vec(point)})
            aim(world, point)
            key(world, key_name)
        return run

    def offset_aim(key_name, along, side):
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

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    def sequence(prefix, cast, times):
        # times = 시전 뒤 절대 게임 초. 단계 표는 앞 단계 기준 지연이라 차이로 바꾼다.
        rows = [(0.0, f'{prefix}_cast', cast)]
        previous = 0.0
        for t in times:
            rows.append((round(t - previous, 3), f'{prefix}_{int(t * 100):03d}', capture(f'{prefix}_{int(t * 100):03d}')))
            previous = t
        return rows

    def pull_away(world, pawn):
        # 줄 끊김 시험: 3번을 허수아비에서 1900 떨어진 쪽(시작점 방향)으로 순간이동한다. 기대 = GIDEON_BURDEN end reason=broken
        point, name = target_point(world, pawn)
        here = pawn.get_actor_location()
        away = unreal.Vector(here.x - point.x, here.y - point.y, 0)
        away = away * (1.0 / max(away.length(), 1.0))
        state['home'] = here
        target = unreal.Vector(point.x + away.x * 1900, point.y + away.y * 1900, here.z)
        pawn.set_actor_location(target, False, True)
        state['log'].append({'label': 'pull_away', 'to': vec(pawn.get_actor_location()), 'target': name})

    def come_back(world, pawn):
        pawn.set_actor_location(state['home'], False, True)

    def near_dummy(world, pawn):
        # R 고리 방패 시험(10-18): 3번을 허수아비 앞 250(지금 있던 쪽)으로 옮긴다. 기대 = GIDEON_WARD release pushed=1
        point, name = target_point(world, pawn)
        here = pawn.get_actor_location()
        away = unreal.Vector(here.x - point.x, here.y - point.y, 0)
        away = away * (1.0 / max(away.length(), 1.0))
        pawn.set_actor_location(unreal.Vector(point.x + away.x * 250, point.y + away.y * 250, here.z), False, True)
        state['log'].append({'label': 'near_dummy', 'to': vec(pawn.get_actor_location()), 'target': name})

    def come_back_start(world, pawn):
        # E로 건너간 뒤 다음 묶음이 같은 자리에서 시작하도록 시작점으로 되돌린다.
        start = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)[0].get_actor_location()
        pawn.set_actor_location(start, False, True)

    # WRA_ONLY = 찍을 묶음 쉼표 목록. e = 순간이동(Space), r = 블랙홀(V), line·cage·sky = 새 E·R·D(10-18).
    only = [s for s in os.environ.get('WRA_ONLY', 'w,a,e,q,r').split(',') if s]
    steps = [(0.0, 'switch', switch)]
    # WRA_REPEAT = 「묶음:콘솔 변수:값,값」을 ; 로 이은 것(10-18 시안 비교). 그 묶음을 값마다 콘솔로 바꿔 <묶음><값>_ 이름으로 다시 찍는다.
    repeat = {}
    for spec in [s for s in os.environ.get('WRA_REPEAT', '').split(';') if s]:
        group, cvar, values = spec.split(':')
        repeat[group] = (cvar, values.split(','))

    def runs(group, cast, times, gap):
        if group not in repeat:
            return sequence(group, cast, times)
        cvar, values = repeat[group]
        rows = []
        # 콘솔 변수 여럿은 + 로 잇고 값도 같은 차례로 + 로 잇는다(예 'a:Gideon.Skills.AAnim+Gideon.Skills.AFx:0+0,1+0', 10-21). 이름엔 - 로.
        def apply(world, cvar, value):
            for name, part in zip(cvar.split('+'), value.split('+')):
                command(world, f'{name} {part}')
        for value in values:
            label = f"{group}{value.replace('+', '-')}"
            rows += [(gap, f'{label}_set', lambda world, pawn, cvar=cvar, value=value: apply(world, cvar, value))]
            rows += sequence(label, cast, times)
        return rows

    if 'w' in only:
        steps += [(1.0, 'reset_w', reset)]
        w_times = [float(x) for x in os.environ.get('WRA_W_TIMES', '0.15,0.35,0.55,0.75,1.0,1.3,1.6,2.0').split(',')]
        steps += runs('w', at_dummy('W'), w_times, 3.0)
    if 'a' in only:
        steps += [(1.5, 'reset_a', reset)]
        a_times = [float(x) for x in os.environ.get('WRA_A_TIMES', '0.5,0.65,0.8,0.95,1.1,1.3,1.5,2.0,2.6,3.5,4.6').split(',')]
        # WRA_REPEAT 'a:Gideon.Skills.ANew:1,1,2,2' 처럼 A 새 스킬 시안도 값마다 다시 찍는다(10-20).
        steps += runs('a', at_dummy('A'), a_times, 2.0)
        steps += [(1.0, 'reset_a2', reset), (0.0, 'a2_cast', at_dummy('A')), (1.2, 'a2_pull', pull_away),
                  (0.4, 'a2_shot', capture('a2_after_pull')), (0.6, 'a2_back', come_back)]
    if 'e' in only:
        # 포털 두 개가 다 보이게 허수아비 300 앞·옆 250으로 건너간다. 건너가는 시점은 0.5초.
        steps += [(1.5, 'reset_e', reset)]
        e_times = [float(x) for x in os.environ.get('WRA_E_TIMES', '0.15,0.45,0.6,0.75,0.9,1.1,1.3').split(',')]
        steps += sequence('e', offset_aim('SpaceBar', 300, 250), e_times)
        steps += [(0.5, 'e_back', come_back_start)]
        # 포털 방향 확인용으로 반대쪽 옆으로 한 번 더 건너간다.
        steps += sequence('e2', offset_aim('SpaceBar', 300, -450), [0.15, 0.3, 0.45, 0.6])
        steps += [(0.5, 'e2_back', come_back_start)]
    if 'q' in only:
        steps += [(1.5, 'reset_q', reset)]
        q_times = [float(x) for x in os.environ.get('WRA_Q_TIMES', '0.3,0.4,0.5,0.6,0.75,0.9,1.1').split(',')]
        steps += sequence('q', at_dummy('Q'), q_times)
        # 화면 아래쪽(시전자 뒤 약 500cm)으로도 한 번 — 포털 높이가 화면에 맞춰 달라진다(10-18).
        steps += [(1.0, 'reset_q2', reset)]
        steps += sequence('q2', offset_aim('Q', 1300, 0), q_times)
    if 's' in only:
        # 포털 셋 + 평타 여섯 발을 허수아비 한 점으로(0.3초부터 0.08초 간격).
        steps += [(1.5, 'reset_s', reset)]
        steps += sequence('s', at_dummy('S'), [0.2, 0.32, 0.4, 0.48, 0.56, 0.64, 0.75, 0.9, 1.2])
    if 'r' in only:
        # 블랙홀은 마법진 0.5초 뒤 열려 시전 뒤 약 4.4초에 끝난다(10-18). 마지막 0.6초에 마법진과 함께 빨려 들어간다.
        steps += [(2.0, 'reset_r', reset)]
        r_times = [float(x) for x in os.environ.get('WRA_R_TIMES', '0.3,0.5,0.7,1.0,2.5,3.75,3.95,4.1,4.22,4.32,4.4,4.6').split(',')]
        steps += runs('r', offset_aim('V', 0, 220), r_times, 2.5)
    if 'line' in only:
        # E Star Line: 0.3초에 광선, 바닥 폭발 6개를 0.06초 간격으로.
        steps += [(1.5, 'reset_line', reset)]
        # WRA_EMARKS = E 표시 시안 번호 목록(예 0,1,2,3) — 시안마다 콘솔로 바꾸고 line<번호>_ 로 찍는다(10-18).
        marks = [m for m in os.environ.get('WRA_EMARKS', '').split(',') if m]
        if not marks:
            steps += sequence('line', at_dummy('E'), [0.35, 0.5, 0.65, 0.8, 1.0, 1.3, 2.0])
        for m in marks:
            steps += [(1.0, f'emark{m}', lambda world, pawn, m=m: command(world, f'Gideon.Skills.EMark {m}'))]
            steps += sequence(f'line{m}', at_dummy('E'), [0.3, 0.4, 0.5, 0.65, 0.9])
            steps += [(1.5, f'reset_line{m}', reset)]
    if 'cage' in only:
        # R Star Cage: 0.45초에 전조 고리, 0.95초에 벽이 솟기 시작해 1.85초에 다 서고, 6초 유지 뒤(7.85초) 무너짐(10-18).
        steps += [(1.5, 'reset_cage', reset)]
        cage_times = [float(x) for x in os.environ.get('WRA_CAGE_TIMES', '0.5,0.6,0.7,0.85,1.0,1.3,1.9,4.0,7.9,8.3,8.7').split(',')]
        steps += runs('cage', at_dummy('R'), cage_times, 1.5)
    if 'ward' in only:
        # R 고리 방패: 0.15초에 방패, 1.75초에 닫으며 앞쪽을 0.25초 동안 밀쳐냄, 허수아비는 1.5초 뒤 제자리.
        steps += [(1.5, 'reset_ward', reset), (0.2, 'ward_near', near_dummy)]
        ward_times = [float(x) for x in os.environ.get('WRA_WARD_TIMES', '0.3,0.8,1.5,1.75,1.85,1.95,2.1,2.5').split(',')]
        # WRA_REPEAT 'ward:<변수>:1,1' 처럼 같은 값을 두 번 주면 첫 시전이 터짐 이펙트를 처음 그릴 때의 멈칫을 대신 겪고 둘째가 같은 이름으로 덮는다(10-19).
        steps += runs('ward', at_dummy('R'), ward_times, 2.5)
        steps += [(2.0, 'ward_back', come_back_start)]
    if 'sky' in only:
        # D Sky Lance: 0.4초에 시작. 시안마다 포격 시점이 0.9~1.6초 사이.
        steps += [(1.5, 'reset_sky', reset)]
        sky_times = [float(x) for x in os.environ.get('WRA_SKY_TIMES', '0.5,0.8,1.0,1.25,1.4,1.65,1.9,2.5').split(',')]
        steps += runs('sky', at_dummy('D'), sky_times, 1.5)
    if 'ray' in only:
        # F Void Ray: 0.35초에 광선, 2초 붙잡음(10-18 1.2→2.0).
        steps += [(1.5, 'reset_ray', reset)]
        ray_times = [float(x) for x in os.environ.get('WRA_RAY_TIMES', '0.3,0.45,0.8,1.2,1.6,2.0,2.3,2.7').split(',')]
        steps += runs('ray', at_dummy('F'), ray_times, 1.5)
    if 'helper' in only:
        # A 도우미(10-21): A로 부르고 평타를 2초 누른다 — 평타마다 GIDEON_HELPER shot from=basic. 이어 W를 허수아비에 —
        # 스킬이 맞히면 from=skill(0.35초에 한 번). 부른 뒤 60초에 end(10-21 8 → 30 → 60초).
        def basic_hold(world, pawn):
            point, name = target_point(world, pawn)
            state['basic_point'] = point
            state['log'].append({'label': 'helper basic', 'target': name, 'point': vec(point)})
            command(world, f'CountessComboQA.Mouse Press Left {point.x} {point.y} {point.z}')

        def basic_release(world, pawn):
            point = state['basic_point']
            command(world, f'CountessComboQA.Mouse Release Left {point.x} {point.y} {point.z}')

        steps += [(1.5, 'reset_helper', reset), (0.0, 'helper_cast', at_dummy('A')), (0.8, 'helper_basic', basic_hold),
                  (2.0, 'helper_release', basic_release), (0.6, 'helper_w', at_dummy('W')),
                  (58.0, 'helper_wait', lambda world, pawn: None)]
    if 'ray2' in only:
        # F 대상 없이: 허수아비 600 앞·옆 300을 찍어 줄 위에 대상이 없게 한다(번개가 커서 자리에 떨어지는지, 10-19).
        steps += [(1.5, 'reset_ray2', reset)]
        ray_times = [float(x) for x in os.environ.get('WRA_RAY_TIMES', '0.3,0.45,0.8,1.2,1.6,2.0,2.3,2.7').split(',')]
        steps += runs('ray2', offset_aim('F', 600, 300), ray_times, 1.5)
    steps += [(1.0, 'end', lambda world, pawn: None)]
    return steps


dump_anims()
STEPS = build_steps()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > float(os.environ.get('WRA_TIMEOUT', '300')):
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
