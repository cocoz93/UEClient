"""Frame sequences of Gideon W (Cosmic Rift), A (Burden), R (Black Hole) in the dark training room, plus the
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
    (qa / 'gideon-beam.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


ANIMS = [] or ['CosmicRift', 'CosmicRift_Start', 'CosmicRift_Execute', 'Cosmic_Rift', 'Cosmic_Rift_Intro', 'Burden',
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

    def capture(name):
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

    def read_beam(label):
        # 줄 빔 끝점 진단: 3번 메시에 붙은 빔 부품의 각 방출기 끝점을 허수아비 위치와 함께 남긴다.
        def run(world, pawn):
            point, name = target_point(world, pawn)
            rows = []
            for component in pawn.get_components_by_class(unreal.ParticleSystemComponent):
                template = component.get_editor_property('template')
                if not template or 'BlackHole_Beam' not in template.get_name():
                    continue
                for index in range(4):
                    try:
                        end = component.get_beam_end_point(index)
                        src = component.get_beam_source_point(index, 0)
                        tgt = component.get_beam_target_point(index, 0)
                    except Exception as error:
                        rows.append({'emitter': index, 'error': str(error)})
                        continue
                    rows.append({'emitter': index, 'end': vec(end) if end else None, 'source': vec(src) if src else None,
                                 'target': vec(tgt) if tgt else None})
                rows.append({'component': vec(component.get_world_location()),
                             'rotation': [round(component.get_world_rotation().yaw, 1), round(component.get_world_rotation().pitch, 1),
                                          round(component.get_world_rotation().roll, 1)]})
            state['log'].append({'label': label, 'dummy': vec(point), 'beam': rows})
        return run

    steps = [(0.0, 'switch', switch), (1.0, 'reset_a', reset), (0.0, 'a_cast', at_dummy('A')),
             (1.0, 'beam1', read_beam('beam_1s')), (0.0, 'shot1', capture('beam_1s')),
             (1.0, 'beam2', read_beam('beam_2s')), (3.0, 'end', lambda world, pawn: None)]
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
