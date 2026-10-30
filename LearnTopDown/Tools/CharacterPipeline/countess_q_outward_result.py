"""Seal Q-only source, asset, actual PIE and explicit image-review evidence."""
from __future__ import annotations

import argparse
import ast
import difflib
import json
from pathlib import Path
import re
import struct
import traceback
import zlib

from baseline import PROJECT, digest, verify

BASE = PROJECT / 'Saved/QA/CharacterPipeline/countess-q-outward-20261016'
NEW_CONTENT = {
    'Content/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.uasset',
    'Content/TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.uasset',
}
AUTHORED = {'Source/LearnTopDown/CountessSkillComponent.cpp',
            'Source/LearnTopDown/CountessSkillComponent.h'}
ALLOWED_CHANGED_METHODS = {'UCountessSkillComponent', 'StartSkillVisuals',
                           'DamageTarget', 'SpawnBlinkDualSweep'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fingerprint(path):
    path = Path(path).resolve()
    require(path.is_file(), 'Missing evidence: ' + str(path))
    return {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}


def protected_hashes():
    files = [PROJECT / 'LearnTopDown.uproject']
    for folder in ('Content', 'Config'):
        files += [p for p in (PROJECT/folder).rglob('*') if p.is_file()]
    return {p.relative_to(PROJECT).as_posix(): digest(p) for p in sorted(files)}


def png_integrity(shot):
    path = Path(shot.get('image', shot.get('path'))).resolve()
    require(path.is_relative_to(BASE.resolve()), 'Capture outside this task: ' + str(path))
    evidence = fingerprint(path)
    require(evidence['sha256'] == shot['sha256'], 'Capture hash differs: ' + str(path))
    data = path.read_bytes()
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG signature: ' + str(path))
    offset, dimensions, ended = 8, None, False
    while offset < len(data):
        require(offset+12 <= len(data), 'Truncated PNG chunk')
        length = struct.unpack_from('>I',data,offset)[0]
        kind = data[offset+4:offset+8]
        end = offset+length+12
        require(end <= len(data), 'Truncated PNG payload')
        payload = data[offset+8:offset+8+length]
        crc = struct.unpack_from('>I',data,offset+8+length)[0]
        require(zlib.crc32(kind+payload) & 0xffffffff == crc, 'PNG CRC mismatch')
        if kind == b'IHDR':
            dimensions = list(struct.unpack_from('>II',payload))
        if kind == b'IEND':
            require(length == 0 and end == len(data), 'Invalid PNG end')
            ended = True
            break
        offset = end
    require(ended and dimensions and min(dimensions) > 0, 'Invalid PNG dimensions/end')
    if 'width' in shot:
        require(dimensions == [shot['width'],shot['height']], 'Reported PNG dimensions differ')
    return evidence | {'width': dimensions[0], 'height': dimensions[1],
                       'native_capture_integrity_passed': True,
                       'visual_judgment_automatically_approved': False}


def methods(source):
    # Ignore braces inside comments/strings while preserving byte positions.
    cleaned = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                     lambda m: ' '*len(m[0]), source, flags=re.S)
    output = {}
    for found in re.finditer(r'^.*?UCountessSkillComponent::(\w+)\([^;\n]*', cleaned, re.M):
        start = cleaned.find('{',found.end())
        require(start >= 0, 'Method has no body: ' + found[1])
        depth = 0
        for end in range(start,len(cleaned)):
            depth += (cleaned[end] == '{') - (cleaned[end] == '}')
            if depth == 0:
                require(found[1] not in output, 'Duplicate method: ' + found[1])
                output[found[1]] = source[found.start():end+1]
                break
    return output


def native_evidence():
    before = read(BASE/'before-source-hashes.json')
    external = read(BASE/'observed-concurrent-HUD-changes.json')
    require(external.get('authored_by_this_Q_task') is False, 'Concurrent changes must not be claimed as authored')
    external_native = external['native_changes']
    require(set(external_native) == {'Source/LearnTopDown/CharacterSkillHUD.cpp'}, 'Only the observed exact HUD file may differ externally')
    current = {p.relative_to(PROJECT).as_posix(): digest(p)
               for p in (PROJECT/'Source').rglob('*') if p.is_file()}
    require(set(before) == set(current), 'Native files added or removed outside Q scope')
    changed = {p for p,h in before.items() if current[p] != h}
    require(changed == AUTHORED | set(external_native), 'Unrecorded native changes outside Countess Q: ' + repr(sorted(changed)))
    for path, entry in external_native.items():
        require(before[path] == entry['before_sha256'] and current[path] == entry['current_sha256'], 'Concurrent HUD changed after recording: ' + path)
    for path,expected in before.items():
        require(digest(BASE/'before'/path) == expected, 'Native backup differs: ' + path)

    # The approved wiring script contains literal, count-checked replacements.
    # Reconstruct its complete expected result; this also protects all unlisted branches.
    wiring_path = PROJECT/'Tools/CharacterPipeline/countess_q_outward_update.py'
    tree = ast.parse(wiring_path.read_text(encoding='utf-8-sig'))
    changes = [n.value for n in tree.body if isinstance(n,ast.Expr)
               and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name)
               and n.value.func.id == 'change']
    require(len(changes) == 2, 'Expected exactly two approved Q source edit descriptions')
    reconstructed = {}
    for call in changes:
        require(isinstance(call.args[0],ast.BinOp) and isinstance(call.args[0].right,ast.Constant),
                'Unexpected wiring target description')
        path = call.args[0].right.value
        require(path in AUTHORED, 'Wiring targeted a non-Q file')
        expected = (BASE/'before'/path).read_bytes()
        for old,new,count in ast.literal_eval(call.args[1]):
            a,b = [x.replace('\n','\r\n').encode('utf-8') for x in (old,new)]
            require(expected.count(a) == count, 'Approved old bytes no longer unique: ' + path)
            expected = expected.replace(a,b)
        require((PROJECT/path).read_bytes() == expected, 'Native source differs from narrow Q wiring: ' + path)
        expected.decode('utf-8')
        require(not expected.startswith(b'\xef\xbb\xbf') and b'\n' not in expected.replace(b'\r\n',b''),
                'Native UTF-8 no-BOM CRLF contract failed: ' + path)
        reconstructed[path] = True
    require(set(reconstructed) == AUTHORED, 'Missing approved source reconstruction')
    old = (BASE/'before/Source/LearnTopDown/CountessSkillComponent.cpp').read_text(encoding='utf-8')
    new = (PROJECT/'Source/LearnTopDown/CountessSkillComponent.cpp').read_text(encoding='utf-8')
    original_methods, final_methods = methods(old), methods(new)
    require(original_methods.keys() == final_methods.keys(), 'Countess methods added or removed')
    changed_methods = {name for name in original_methods if original_methods[name] != final_methods[name]}
    require(changed_methods == ALLOWED_CHANGED_METHODS,
            'Unexpected changed Countess methods: ' + repr(sorted(changed_methods)))
    a,b = 'const TCHAR* Animations[]','ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
    require(old[old.index(a):old.index(b)] == new[new.index(a):new.index(b)], 'Skill definitions changed')
    require('TEXT("Countess.Skills.QPresentation"), 3,' in new, 'Default Q variant must be 3')
    diff = []
    for path in sorted(AUTHORED):
        original = (BASE/'before'/path).read_text(encoding='utf-8')
        final = (PROJECT/path).read_text(encoding='utf-8')
        diff += difflib.unified_diff(original.splitlines(True),final.splitlines(True),
                                     fromfile='before/'+path,tofile='after/'+path)
    (BASE/'native-change.diff').write_text(''.join(diff),encoding='utf-8')
    return {'authored_files': sorted(AUTHORED), 'source_hashes': current,
            'unchanged_native_files': len(before)-len(AUTHORED)-len(external_native),
            'observed_concurrent_unowned_native_changes':external_native,
            'concurrent_HUD_source_in_accepted_Q_binary':False,
            'exact_approved_Q_wiring_bytes_verified': True,
            'wiring_description': fingerprint(wiring_path),
            'skill_definitions_byte_identical': True,
            'W_E_R_and_non_Q_branches_byte_identical': True,
            'unchanged_methods': sorted(set(original_methods)-changed_methods),
            'changed_Q_methods': sorted(changed_methods), 'utf8_no_bom_crlf_preserved': True}


def resolve_report(value,name):
    value = Path(value).resolve()
    return value/name if value.is_dir() else value


def run_evidence(path,fps,case_count,capture_count,module,motion=False):
    report = read(path)
    directory = path.parent
    launch,process = read(directory/'launch-result.json'),read(directory/'process-result.json')
    require(report.get('passed') is True and launch.get('passed') is True,'Failed QA report or launch')
    require(launch.get('return_code') == 0 and process.get('return_code') == 0
            and not process.get('timed_out'), 'Editor failed or timed out')
    require(not launch.get('q_material_compile_errors') and not launch.get('shader_compile_errors'),
            'Shader compile error reported')
    require(launch.get('q_shader_compile_verified') is True, 'Q shader compile not verified by launcher')
    require(report.get('fixed_simulation_fps') == fps, 'Wrong simulation FPS')
    require(report.get('protected_files_match') is True and report.get('baseline_after',{}).get('passed') is True,
            'Runtime protected files verification failed')
    require(report.get('capture_integrity',{}).get('passed') is True, 'Runtime capture integrity failed')
    require(len(report['cases']) == case_count and all(c.get('passed') is True for c in report['cases']),
            'Wrong case count or failed case')
    log_path = directory/'editor.log'
    log = log_path.read_text(encoding='utf-8',errors='replace')
    suffixes = set(re.findall(r'UnrealEditor-LearnTopDown-(\d+)\.dll',log))
    require(module in suffixes, 'Accepted module not observed in actual editor: ' + str(path))
    require(not re.search(r'(?:Failed to compile Material|Error.*M_CountessQOutwardCut|M_CountessQOutwardCut.*Error)',log,re.I),
            'Outward material compile/fallback error in editor log')
    shots = report['screenshots']
    require(len(shots) == capture_count, 'Unexpected capture count: ' + str(path))
    captures = [png_integrity(s) for s in shots]
    cases = {c['name']:c.get('data',{}) for c in report['cases']}
    if motion:
        original,enhanced = cases['Q_motion_original'],cases['Q_motion_enhanced']
        frames_a,frames_b = original['frames'],enhanced['frames']
        require(len(frames_a) == len(frames_b) == 16, 'Motion comparison must retain 16 paired frames')
    else:
        original,enhanced = cases['Q_original'],cases['Q_enhanced']
        require(original['damage'] == enhanced['damage'] == 35 and
                original['target_health'] == enhanced['target_health'] == 65, 'Q damage changed')
        require(abs(original['first_damage_seconds']-enhanced['first_damage_seconds']) <= 1/fps,
                'Q action timing differs across variants')
        for key in ('E_with_original_Q_setting','E_with_enhanced_Q_setting'):
            require(cases[key]['target_health_minimum'] == 55, 'E damage changed')
        frames_a,frames_b = original['phases'],enhanced['phases']
        require(len(frames_a) == len(frames_b) == 6, 'Q comparison needs six paired phases')
    for a,b in zip(frames_a,frames_b):
        require(abs(a['elapsed']-b['elapsed']) <= 1/fps+.0001, 'Q paired simulation times differ')
        for field in ('camera','pawn'):
            require(max(abs(x-y) for x,y in zip(a[field],b[field])) < .05, 'Q paired '+field+' differs')
    return ({'report': fingerprint(path), 'launch': fingerprint(directory/'launch-result.json'),
             'process': fingerprint(directory/'process-result.json'), 'editor_log': fingerprint(log_path),
             'actual_module_suffixes': sorted(suffixes), 'fps': fps, 'cases':case_count,
             'captures':capture_count, 'native_images':captures, 'case_data':cases},captures)


def main():
    parser = argparse.ArgumentParser()
    for name in ('assets','compare60','compare30','motion'):
        parser.add_argument('--'+name,required=True)
    parser.add_argument('--module',default='6164')
    parser.add_argument('--editor-build',type=Path,default=BASE/'build-editor-01.log')
    parser.add_argument('--game-build',type=Path,default=BASE/'build-game-01.log')
    parser.add_argument('--visual-review',type=Path,default=BASE/'visual-review.json')
    parser.add_argument('--editor-restart-required',action='store_true')
    args = parser.parse_args()
    before = read(BASE/'baseline-before.json')['protected_hashes']
    require(len(before) == 7017, 'Expected 7017 protected files before Q change')
    baseline_result = verify(BASE/'baseline-before.json')
    require(baseline_result['passed'], 'Original content/config/project hashes changed')
    current = protected_hashes()
    concurrent = read(BASE/'observed-concurrent-HUD-changes.json')
    external_content = concurrent['content_additions']
    expected_ui_names = {'T_Exp_Rail','T_Glass_Sheen','T_Globe_Cavity','T_Life_Frame','T_Life_Globe','T_Life_Liquid',
                         'T_Mana_Frame','T_Mana_Globe','T_Mana_Liquid','T_SkillSlot_Active','T_SkillSlot_Frame'}
    expected_ui_names |= {'T_SkillIcon_'+str(i) for i in range(10)}
    require(set(external_content)=={'Content/TopDown/UI/Textures/'+name+'.png' for name in expected_ui_names}, 'External UI additions differ from the exact observed 21 PNGs')
    require(len(current) == 7040 and set(current)-set(before) == NEW_CONTENT | set(external_content),
            'Unrecorded content additions exist outside the two Q assets and exact external UI images')
    require(all(current[path]==value for path,value in external_content.items()), 'Concurrent UI files changed after recording')
    native = native_evidence()
    asset_path = resolve_report(args.assets,'material.json')
    assets = read(asset_path)
    require(assets.get('passed') is True and assets.get('graph_connections_verified') is True,
            'Outward assets failed authoring validation')
    require(assets.get('centerlines_straight') is True and assets.get('blend') == 'Translucent',
            'Outward shape/material contract differs')
    require(680 < assets['total_lateral_span_cm'] < 820 and assets['max_import_position_error_cm'] < .01,
            'Outward dimensions/import positions differ')
    require(assets.get('protected_content_changes') == [], 'Asset author modified protected Content')
    for blade in assets['geometry']:
        require(blade['max_centerline_curve_deviation_cm'] < .001 and blade['outward_angle_from_lateral_degrees'] < 15,
                'Q blades are curved or not lateral')
        require(blade['disconnected_fleck_quads'] == 12,'Q flecks not independently authored')
    builds = []
    for path in (args.editor_build,args.game_build):
        require('Result: Succeeded' in path.read_text(encoding='utf-8',errors='replace'), 'Native build failed: '+str(path))
        builds.append(fingerprint(path))
    module = PROJECT/f'Binaries/Win64/UnrealEditor-LearnTopDown-{args.module}.dll'
    require(read(PROJECT/'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown'] == module.name,
            'Current editor module manifest differs')
    specs = [(args.compare60,60,6,21,False),(args.compare30,30,6,21,False),(args.motion,60,8,37,True)]
    runs,images = [],[]
    for value,fps,cases,shots,motion in specs:
        evidence,captures = run_evidence(resolve_report(value,f'countess-q-comparison-{fps}.json'),
                                         fps,cases,shots,args.module,motion)
        runs.append(evidence)
        images += captures
    require(len({i['path'] for i in images}) == len(images), 'Duplicate QA captures')
    review = read(args.visual_review)
    require(review.get('render_review_passed') is True and review.get('user_style_approval') is False,
            'Explicit render review missing or user approval falsely implied')
    reviewed = review.get('reviewed_source_images',[])
    require(bool(reviewed),'Explicitly reviewed source-image hash list missing')
    source_images = {i['path']:i['sha256'] for i in images}
    for source in reviewed:
        path = str(Path(source.get('path',source.get('image'))).resolve())
        require(path in source_images and source['sha256'] == source_images[path], 'Reviewed source hash not in accepted native captures')
        require(digest(Path(path)) == source['sha256'], 'Reviewed source changed after judgment')
    baseline_path = BASE/'baseline-current.json'
    baseline = {'schema_version':1,'project':str(PROJECT),'protected_hashes':current,
                'baseline_kind':'hashes_only','content_backup_created_by_this_seal':False,
                'parent_baseline':fingerprint(BASE/'baseline-before.json'),
                'source_hashes_at_seal':native['source_hashes']}
    if baseline_path.exists():
        require(read(baseline_path)['protected_hashes'] == current,'Existing current baseline differs')
    else:
        baseline_path.write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    result = {'passed':True,'status':'Q_outward_cuts_implemented_and_explicit_render_review_completed',
              'scope':'Countess Q presentation only','user_style_approval':False,
              'render_review_passed':True,'visual_judgment_automatically_approved':False,
              'verification':runs,'cases':20,'native_captures':len(images),
              'explicitly_reviewed_native_images':len(reviewed),
              'visual_review':fingerprint(args.visual_review),'native_source':native,
              'authoring':fingerprint(asset_path),'builds':builds,
              'editor_module':fingerprint(module),
              'editor_module_manifest':fingerprint(PROJECT/'Binaries/Win64/UnrealEditor.modules'),
              'original_7017_baseline_verification':baseline_result,
              'current_baseline':fingerprint(baseline_path),'current_protected_files':len(current),
              'new_content_hashes':{p:current[p] for p in sorted(NEW_CONTENT)},
              'observed_concurrent_HUD_changes':fingerprint(BASE/'observed-concurrent-HUD-changes.json'),
              'concurrent_HUD_changes_are_not_claimed_authored_or_verified':True,
              'E_unchanged':True,'W_R_unchanged':True,'Q_gameplay_unchanged':True,
              'physical_OS_input_tested':False,'continuous_video':False,
              'GPU_performance_benchmark':False,
              'user_editor_restart_required':args.editor_restart_required,
              'restart_status_is_supplied_from_observed_live_editor_module_check':True}
    (BASE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'cases':20,'captures':len(images),'protected_files':len(current),
                      'result':str(BASE/'result.json')}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        failure = {'passed':False,'status':'seal_failed','error':traceback.format_exc(),
                   'user_style_approval':False,'visual_judgment_automatically_approved':False}
        (BASE/'result.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
        raise
