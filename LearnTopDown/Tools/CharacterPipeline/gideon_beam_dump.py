"""F 제로베이스(10-19 23차) 후보 고르기용: 파라곤 입자 효과의 이미터별 빔 끝점 방식·흔들림·색 인자 이름을 읽는다.
FX_DUMP = 쉼표로 이은 입자 효과 경로. 각 이미터 → LOD 0 모듈마다 읽히는 속성을 전부 적는다(값은 300자까지). 에셋은 저장하지 않는다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SYSTEMS = [p for p in os.environ.get('FX_DUMP', '').split(',') if p]
report = {'passed': False, 'systems': []}
# 캐스케이드 모듈 속성은 dir()에 안 잡히지만(블루프린트 비공개) 이름을 대면 get_editor_property로 읽힌다(10-19 23차 확인).
NAMES = {
    'ParticleModuleTypeDataBeam2': ['beam_method', 'texture_tile', 'texture_tile_distance', 'sheets', 'max_beam_count', 'speed',
                                    'interpolation_points', 'always_on', 'up_vector_step_size', 'distance', 'taper_method',
                                    'taper_factor', 'taper_scale', 'render_geometry', 'render_direct_line', 'render_tessellation'],
    'ParticleModuleBeamSource': ['source_method', 'source_name', 'b_source_absolute', 'source', 'b_lock_source',
                                 'source_tangent_method', 'source_strength'],
    'ParticleModuleBeamTarget': ['target_method', 'target_name', 'target', 'b_target_absolute', 'b_lock_target',
                                 'target_tangent_method', 'target_strength', 'lock_radius'],
    'ParticleModuleBeamNoise': ['b_low_freq_enabled', 'frequency', 'frequency_low_range', 'noise_range', 'noise_range_scale',
                                'noise_speed', 'b_smooth', 'noise_lock_radius', 'b_noise_lock', 'b_oscillate', 'noise_lock_time',
                                'noise_tension', 'noise_tessellation', 'b_target_noise', 'frequency_distance',
                                'b_apply_noise_scale', 'noise_scale'],
    'ParticleModuleRequired': ['material', 'b_use_local_space', 'screen_alignment', 'emitter_duration', 'emitter_loops',
                               'b_kill_on_completed', 'emitter_delay'],
    'ParticleModuleTypeDataMesh': ['mesh', 'b_override_material', 'axis_lock_option', 'b_camera_facing'],
    'ParticleModuleParameterDynamic': ['dynamic_params'],
}
PARAM = ['parameter_name', 'param_mode', 'min_input', 'max_input', 'min_output', 'max_output', 'constant']


def read(obj, name):
    value = obj.get_editor_property(name)
    if isinstance(value, unreal.Object) and 'Distribution' in value.get_class().get_name():
        item = {'class': value.get_class().get_name()}
        for key in PARAM + ['min', 'max']:
            try:
                item[key] = str(value.get_editor_property(key))[:200]
            except Exception:
                pass
        return item
    return str(value)[:300]


def props(obj):
    row = {'class': obj.get_class().get_name()}
    for name in NAMES.get(row['class'], []):
        try:
            row[name] = read(obj, name)
        except Exception as error:
            row[name] = f'unreadable: {error}'[:120]
    return row


def path_of(obj):
    return unreal.SystemLibrary.get_path_name(obj) if obj else None


try:
    for path in SYSTEMS:
        system = unreal.load_asset(path)
        prefix = system.get_path_name() + ':'
        entry = {'system': path, 'emitters': []}
        objects = [o for o in unreal.ObjectIterator(unreal.Object) if unreal.SystemLibrary.get_path_name(o).startswith(prefix)]
        # LOD 레벨의 모듈 목록은 파이썬에 안 열려 있어(「Failed to find property 'modules'」) 이미터별로 못 나눈다.
        # 대신 시스템에 딸린 모듈 중 빔·흔들림·색·인자 모듈을 전부 적는다.
        emitters = [o for o in objects if 'Emitter' in o.get_class().get_name() and 'Module' not in o.get_class().get_name()]
        for emitter in emitters:
            try:
                entry['emitters'].append({'emitter': path_of(emitter)[len(prefix):], 'name': str(emitter.get_editor_property('emitter_name'))})
            except Exception:
                entry['emitters'].append({'emitter': path_of(emitter)[len(prefix):]})
        keys = ('Beam', 'TypeData', 'Required', 'ParameterDynamic')
        entry['modules'] = [props(o) | {'path': path_of(o)[len(prefix):]} for o in objects
                            if o.get_class().get_name().startswith('ParticleModule') and any(k in o.get_class().get_name() for k in keys)]
        # 인스턴스 인자(코드에서 SetFloatParameter·SetVectorParameter·SetActorParameter로 넣는 값) 이름.
        entry['parameters'] = []
        for o in objects:
            if 'ParticleParameter' in o.get_class().get_name():
                item = {'class': o.get_class().get_name(), 'path': path_of(o)[len(prefix):]}
                for key in PARAM:
                    try:
                        item[key] = str(o.get_editor_property(key))[:200]
                    except Exception:
                        pass
                entry['parameters'].append(item)
        report['systems'].append(entry)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'beam-dump.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
