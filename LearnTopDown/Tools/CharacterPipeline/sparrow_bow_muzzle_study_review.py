"""D1-3 bow study captures through the established actual-key PIE harness.

SPARROW_BOW_MUZZLE_STYLES=1,2,3; SPARROW_BOW_MUZZLE_MODES=normal by default.
The parent runs author() and sequence(). This file never launches Unreal.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy
import shutil

import unreal


@contextmanager
def environment(values):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def author(output):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    return runpy.run_path(str(folder / 'sparrow_bow_muzzle_study_materials.py'))['author'](output)


def sequence(rig):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    out, cmd, check = rig['OUT'], rig['cmd'], rig['check']
    selector = 'Sparrow.BowMuzzle.Style'
    styles = [int(x) for x in os.environ.get('SPARROW_BOW_MUZZLE_STYLES', '1,2,3').split(',')]
    modes = os.environ.get('SPARROW_BOW_MUZZLE_MODES', 'normal')
    check(bool(styles) and set(styles) <= {1, 2, 3}, 'D bow study selection is known')
    result = {'passed': False, 'styles': styles, 'modes': modes, 'cases': [],
              'visual_acceptance': 'requires direct actual image/video review; geometry counts are not appearance proof'}

    def save():
        (out / 'bow-muzzle-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    try:
        for style in styles:
            label = 'BowD' + str(style)
            cmd(selector + ' ' + str(style))
            cmd('Sparrow.FlameStudy.D 0')
            scoped = dict(rig)
            scoped['case'] = lambda value: rig['case'](label + '_' + value)
            scoped['capture'] = lambda value: rig['capture'](label + '_' + value)
            observed = {}
            with environment({'SPARROW_ASCENDED_KEYS': 'D', 'SPARROW_ASCENDED_MODES': modes,
                              'SPARROW_ASCENDED_RECRAFT': '1', 'SPARROW_SERAPH_POLISH': '1',
                              'ASCENDED_ARSENAL_RECOVERY': '0'}):
                generator = runpy.run_path(str(folder / 'sparrow_ascended_arsenal_review.py'))['sequence'](scoped)
                try:
                    for delay in generator:
                        clip = rig['STATE'].get('video_clip')
                        if clip and not clip['prefix'].startswith(label + '_'):
                            clip['prefix'] = label + '_' + clip['prefix']
                            clip['case'] = label + '_' + clip['case']
                        pawn = rig['pawn']()
                        body = pawn.get_editor_property('mesh')
                        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowBowMuzzleStudy):
                            if actor.get_owner() != pawn:
                                continue
                            row = observed.setdefault(actor.get_name(), {'design': actor.get_design(), 'samples': 0,
                                'released_seen': False, 'max_endpoint_error': 0., 'max_segments': 0, 'materials': []})
                            row['samples'] += 1
                            row['released_seen'] |= actor.has_released()
                            row['max_segments'] = max(row['max_segments'], actor.get_visible_segment_count())
                            errors = [(actor.get_tracked_nock() - body.get_socket_location('arrow_nock')).length(),
                                      (actor.get_tracked_upper_tip() - body.get_socket_location('bow_string_top')).length(),
                                      (actor.get_tracked_lower_tip() - body.get_socket_location('bow_string_bott')).length()]
                            row['max_endpoint_error'] = max(row['max_endpoint_error'], *errors)
                            row['bow_span'] = actor.get_bow_span()
                            for component in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
                                material = component.get_material(0)
                                if material:
                                    row['materials'] = sorted(set(row['materials']) | {material.get_base_material().get_path_name()})
                        yield delay
                finally:
                    generator.close()
            destination = out / (label + '-gameplay.json')
            shutil.copyfile(out / 'sparrow-ascended-arsenal.json', destination)
            gameplay = json.loads(destination.read_text(encoding='utf-8'))
            check(gameplay['passed'], label + ' keeps native single piercing arrow, damage and timing')
            check(bool(observed) and all(x['design'] == style and x['released_seen'] for x in observed.values()),
                  label + ' creates and releases the selected real bow study')
            check(all(20 < x['bow_span'] < 250 and x['max_segments'] > 30 for x in observed.values()),
                  label + ' follows the character-sized physical bow')
            check(all(x['max_endpoint_error'] < 1.0 for x in observed.values()),
                  label + ' tips and nock follow the live animated bones within one centimetre')
            check(all(len(x['materials']) == 5 and all('/BowMuzzle20261027/' in m for m in x['materials']) for x in observed.values()),
                  label + ' loads only its own five optical material layers')
            result['cases'].append({'label': label, 'gameplay_report': destination.name, 'actors': observed})
            save()
        result['passed'] = True
    finally:
        cmd(selector + ' 0')
        cmd('CountessComboQA.FlushInput')
        result['default_restored'] = unreal.SystemLibrary.get_console_variable_int_value(selector) == 0
        save()
