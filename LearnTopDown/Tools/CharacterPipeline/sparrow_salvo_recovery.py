"""Reuse movement reviews for W/R salvos, plus bounded interruption checks.

Run as a sparrow_feedback STUDIES module at the parent-selected 30/60fps.
No video or assets are generated; each reused JSON is preserved under its own
name before the next review runs. All temporary environment values are restored.
"""
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil

import unreal


def sequence(rig):
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1.0 / rig['FPS']
    directory = Path(unreal.Paths.project_dir()) / 'Tools' / 'CharacterPipeline'
    source = (Path(unreal.Paths.project_dir()) / 'Source' / 'LearnTopDown' /
              'SparrowSkillComponent.cpp').read_text(encoding='utf-8-sig')

    def constant(name):
        match = re.search(r'constexpr int32\s+' + name + r'\s*=\s*(\d+)\s*;', source)
        if not match:
            raise AssertionError('Cannot verify native salvo count ' + name)
        return int(match[1])

    w_count = constant('PiercingShotCount')
    r_waves = constant('MultishotWaveCount')
    r_per_wave = constant('MultishotArrowsPerWave')
    report = {'passed': False, 'fps': rig['FPS'], 'reviews': [], 'interruptions': [],
              'native_counts': {'W': w_count, 'R_waves': r_waves, 'R_per_wave': r_per_wave}}

    def save():
        (out / 'sparrow-salvo-recovery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    @contextmanager
    def environment(values):
        previous = {name: os.environ.get(name) for name in values}
        try:
            os.environ.update(values)
            yield
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def reuse(filename, values, original, preserved):
        spec = importlib.util.spec_from_file_location(filename.removesuffix('.py'), directory / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with environment(values):
            try:
                yield from module.sequence(rig)
            finally:
                if (out / original).exists():
                    shutil.copyfile(out / original, out / preserved)
        data = json.loads((out / preserved).read_text(encoding='utf-8'))
        report['reviews'].append({'filename': preserved, 'passed': data['passed'], 'cases': len(data['cases'])})
        save()
        check(data['passed'], preserved + ' completes its existing functional assertions')

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def state():
        pawn = rig['pawn']()
        movement = pawn.get_editor_property('character_movement')
        anim = pawn.get_editor_property('mesh').get_anim_instance()
        return {'casting': rig['skills']().is_casting(), 'busy': pawn.is_combat_busy(),
                'root': str(anim.get_editor_property('root_motion_mode')),
                'orient': movement.get_editor_property('orient_rotation_to_movement'),
                'position': rig['vec'](pawn.get_actor_location())}

    def observe(row, elapsed):
        new = []
        for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
            if not unreal.SystemLibrary.is_valid(arrow) or arrow.get_owner() != rig['pawn']():
                continue
            name = arrow.get_name()
            if name not in row['arrows']:
                row['arrows'][name] = elapsed
                new.append(name)
        if new:
            row['batches'].append({'elapsed': elapsed, 'count': len(new)})

    def restored(initial):
        after = state()
        return not after['casting'] and not after['busy'] and all(
            after[field] == initial[field] for field in ('root', 'orient'))

    def fresh():
        cmd('CountessComboQA.FlushInput')
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .65
        rig['layout']([(420, 0), (700, 0), (600, 370)])
        yield .15

    try:
        for form in (False, True):
            yield from reuse('sparrow_recovery_timing.py', {
                'SPARROW_RECOVERY_KEYS': 'W,R', 'SPARROW_RECOVERY_FORM': '1' if form else '0',
                'SPARROW_RECOVERY_BASELINE': '0'}, 'sparrow-recovery-timing.json',
                'sparrow-recovery-timing-' + ('form' if form else 'normal') + '.json')
        common = {'SPARROW_DIRECTION_KEYS': 'Q,W,E,R,A,S,D,F', 'SPARROW_DIRECTION_SECONDS': '1.5',
                  'SPARROW_DIRECTION_AIM_DISTANCE': '950', 'SPARROW_DIRECTION_MIN_TRAVEL': '40',
                  'SPARROW_DIRECTION_FIND_CLEAR_START': '0'}
        yield from reuse('sparrow_directional_movement_review.py', {
            **common, 'SPARROW_DIRECTION_CHARACTER': 'countess', 'SPARROW_DIRECTION_ANGLES': '0',
            'SPARROW_DIRECTION_GROUPS': 'idle_tap,idle_hold', 'SPARROW_DIRECTION_DISTANCE': '74',
            'SPARROW_DIRECTION_FIND_CLEAR_START': '1'},
            'sparrow-directional-movement.json', 'countess-near-movement.json')
        yield from reuse('sparrow_directional_movement_review.py', {
            **common, 'SPARROW_DIRECTION_CHARACTER': 'sparrow', 'SPARROW_DIRECTION_ANGLES': '0,90,180,270',
            'SPARROW_DIRECTION_GROUPS': 'idle_tap', 'SPARROW_DIRECTION_DISTANCE': '420'},
            'sparrow-directional-movement.json', 'sparrow-far-movement.json')

        cmd('Sparrow.Skills.IgnoreCooldowns 1')
        yield from fresh()
        rig['case']('Salvo_W_montage_interrupt')
        initial = state()
        targets = rig['STATE']['dummies']
        health = [rig['health'](target) for target in targets]
        damage = float(rig['skills']().get_editor_property('skills')[1].get_editor_property('damage'))
        row = {'case': 'W_montage_interrupt', 'arrows': {}, 'batches': [], 'initial': initial}
        report['interruptions'].append(row)
        rig['use']('W', offset=(950, 0))
        started = now()
        while now() - started < 1.8:
            elapsed = now() - started
            observe(row, elapsed)
            if 'interrupted_at' not in row and len(row['arrows']) >= 2:
                row['interrupted_at'] = elapsed
                row['count_at_interrupt'] = len(row['arrows'])
                anim = rig['pawn']().get_editor_property('mesh').get_anim_instance()
                montage = anim.get_current_active_montage()
                check(montage is not None and rig['skills']().is_casting(), 'W is really casting at the interruption')
                row['montage'] = montage.get_name()
                anim.montage_stop(.035, montage)
            yield frame
        row['after'] = state()
        row['damage'] = [before - rig['health'](target) for before, target in zip(health, targets)]
        save()
        check(row.get('count_at_interrupt') == 2 and len(row['arrows']) == 2,
              'interrupting W after its second shot cancels both remaining timer shots')
        check(restored(initial), 'W montage interruption restores combat, root motion and orientation')
        check(all(abs(value - expected) < .05 for value, expected in zip(
            row['damage'], [damage * 2 / w_count, damage * 2 / w_count, 0])),
            'interrupted W deals only the two actual shots of damage')

        # The next cast uses the same pawn, without a combat-state reset or layout.
        rig['case']('Salvo_W_after_interrupt')
        health = [rig['health'](target) for target in targets]
        row = {'case': 'W_after_interrupt', 'arrows': {}, 'batches': []}
        report['interruptions'].append(row)
        rig['use']('W', offset=(950, 0))
        started = now()
        while now() - started < 1.8:
            observe(row, now() - started)
            yield frame
        row['after'] = state()
        row['damage'] = [before - rig['health'](target) for before, target in zip(health, targets)]
        save()
        check(len(row['arrows']) == w_count and len(row['batches']) == w_count,
              'the next W on the same pawn completes all native shots')
        check(restored(initial), 'the next W restores combat state normally')
        check(all(abs(value - expected) < .05 for value, expected in zip(row['damage'], [damage, damage, 0])),
              'the next W keeps its complete native damage')

        yield from fresh()
        rig['case']('Salvo_R_move_interrupt')
        initial = state()
        start = rig['pawn']().get_actor_location()
        goal = rig['ground'](start.x - 300, start.y - 320)
        row = {'case': 'R_move_interrupt', 'arrows': {}, 'batches': [], 'initial': initial}
        report['interruptions'].append(row)
        rig['use']('R', offset=(950, 0))
        started = now()
        released = False
        while now() - started < 2.0:
            elapsed = now() - started
            observe(row, elapsed)
            if 'move_pressed_at' not in row and len(row['batches']) >= 3:
                row['move_pressed_at'] = elapsed
                row['count_at_move'] = len(row['arrows'])
                cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            elif 'move_pressed_at' in row and not released and elapsed >= row['move_pressed_at'] + frame - 1e-5:
                cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                released = True
            yield frame
        row['after'] = state()
        row['distance_moved'] = rig['dist'](start, rig['pawn']().get_actor_location())
        save()
        check(row.get('count_at_move') == 3 * r_per_wave and len(row['arrows']) == row['count_at_move'] < r_waves * r_per_wave,
              'R movement cancellation stops the remaining native waves after three real waves')
        check(row['distance_moved'] > 150 and restored(initial),
              'R cancellation consumes the short move click and restores character movement')
        report['passed'] = True
        save()
    finally:
        cmd('CountessComboQA.FlushInput')
        cmd('Character.Input.TraceMove 0')
        save()
