"""Fail closed on temporal gaps, disabled cloth and visible unintended effects."""
from __future__ import annotations
import math

PHASES = {'anticipation', 'action', 'recovery', 'residual'}

def check_quality(profile: dict, report: dict) -> dict:
    contract = profile['presentation_contract']['quality_gate']
    fps = report['fixed_simulation_fps']
    if report.get('suite') != 'character_visual_quality' or not report.get('passed') or fps not in (30, 60):
        raise ValueError('Missing successful original-field temporal quality suite')
    if report.get('character_id') != profile['character_id'] or report.get('map') != '/Game/TopDown/Lvl_TopDown':
        raise ValueError('Temporal evidence belongs to a different character or field')
    if not report.get('protected_files_match'):
        raise ValueError('Temporal evidence changed protected assets')
    cases = {case['name']: case for case in report['cases']}
    required = {'locomotion', 'primary'} | {'skill_' + key for key in ('Q','W','E','R')}
    if not required <= cases.keys():
        raise ValueError('Missing movement, sharp-turn, attack or skill timeline')
    count = 0
    for name in sorted(required):
        data = cases[name]['data']
        rows = data['quality_samples']
        if len(rows) < 2:
            raise ValueError('Empty temporal evidence: ' + name)
        times = [row['time'] for row in rows]
        if any(not math.isfinite(t) for t in times) or any(b <= a or b-a > 2.1/fps for a,b in zip(times,times[1:])):
            raise ValueError('Temporal evidence has missing simulation frames: ' + name)
        duration = times[-1]-times[0]
        minimum = contract['minimum_seconds'].get(name, 0.5)
        if duration < minimum:
            raise ValueError('Incomplete action and residual timeline: ' + name)
        for row in rows:
            if row['cloth_suspended'] or row['cloth_disabled']:
                raise ValueError('Disabling cloth cannot satisfy visual acceptance')
            if row['cloth_lod_has_data'] and len(row['cloth']) not in contract['expected_cloth_count']:
                raise ValueError('Cloth simulation disappeared at a LOD with cloth render data')
            if not row['cloth_lod_has_data'] and row['cloth']:
                raise ValueError('Cloth measurements do not match the current rendered LOD')
            for cloth in row['cloth']:
                if cloth['vertices'] <= 0 or not all(math.isfinite(cloth[field]) for field in ('max_above_head_cm','p95_above_head_cm','max_radius_cm')):
                    raise ValueError('Invalid cloth particle measurements')
                for field, limit in contract['cloth_limits'].items():
                    if cloth[field] > limit:
                        raise ValueError('Cloth exceeds accepted envelope: ' + field)
            for effect in row['effects']:
                if not effect['active'] or effect['particles'] <= 0:
                    continue
                if not effect['template'] or any(fragment in effect['template'] for fragment in contract['forbidden_effects']):
                    raise ValueError('Unintended active effect: ' + effect['template'])
                for emitter in effect.get('render_emitters', []):
                    if emitter.get('renders_surface', True) and emitter['particles'] > 0 and any('WorldGridMaterial' in m or 'DefaultMaterial' in m for m in emitter['materials']):
                        raise ValueError('Active particles render a placeholder material')
        if not any(row['cloth'] for row in rows):
            raise ValueError('No detailed cloth measurement anywhere in scenario: ' + name)
        if name.startswith('skill_'):
            before, after = data['target_health_before_after']
            passive = name == 'skill_E' and profile['character_id'] == 'sparrow'
            if not (isinstance(before, (int, float)) and isinstance(after, (int, float)) and
                    ((after == before) if passive else (0 <= after < before))):
                raise ValueError('Skill timeline does not prove its successful gameplay outcome: ' + name)
            if rows[-1]['casting'] or any(effect['active'] and effect['particles'] > 0 for effect in rows[-1]['effects']):
                raise ValueError('Skill cast or residual particles have not expired: ' + name)
            if set(data.get('captured_phases', [])) != PHASES:
                raise ValueError('Skill images omit a temporal phase: ' + name)
            if name != 'skill_E' or profile['character_id'] != 'sparrow':
                if not any(row['casting'] for row in rows):
                    raise ValueError('Skill input never entered its real cast')
            elif any(row['casting'] for row in rows):
                raise ValueError('Passive E unexpectedly became an active cast')
        count += len(rows)
    return {'passed': True, 'fps': fps, 'sample_count': count, 'scenarios': sorted(required)}
