"""Seal Q tone/length and Rogue cape evidence without running an editor or build."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import traceback
import zlib

from baseline import PROJECT, digest

BASE = PROJECT/'Saved/QA/CharacterPipeline/q-tone-cape-20261016'
COUNTESS = 'Source/LearnTopDown/CountessSkillComponent.cpp'
SPARROW = 'Source/LearnTopDown/SparrowCharacter.cpp'
SPARROW_HEADER = 'Source/LearnTopDown/SparrowCharacter.h'
VIEWPORT_QA = 'Source/LearnTopDown/Tests/CharacterVisualAutomation.cpp'
MOUSE_QA = 'Source/LearnTopDown/Tests/CountessComboAutomation.cpp'
BUILD = 'Source/LearnTopDown/LearnTopDown.Build.cs'
AUTHORED = {COUNTESS,SPARROW,SPARROW_HEADER,BUILD,VIEWPORT_QA,MOUSE_QA}
NEW_MATERIAL = 'Content/TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted.uasset'
OLD_MATERIAL = 'Content/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.uasset'
OUTWARD_MESH = 'Content/TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.uasset'
ROGUE_MESH = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue.Sparrow_Rogue'
ROGUE_CLOTH = ROGUE_MESH+':Sparrow_Rogue_APEX'


def require(value,message):
    if not value:
        raise AssertionError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def fingerprint(path):
    path=Path(path).resolve()
    require(path.is_file(),'Missing evidence: '+str(path))
    return {'path':str(path),'sha256':digest(path),'bytes':path.stat().st_size}


def protected_hashes():
    """The sole complete protected-file hashing pass in this seal."""
    files=[PROJECT/'LearnTopDown.uproject']
    for folder in ('Content','Config'):
        files += [p for p in (PROJECT/folder).rglob('*') if p.is_file()]
    return {p.relative_to(PROJECT).as_posix():digest(p) for p in sorted(files)}


def png(shot):
    path=Path(shot.get('image',shot.get('path'))).resolve()
    require(path.is_relative_to(BASE.resolve()),'Capture outside task: '+str(path))
    data=path.read_bytes()
    sha=hashlib.sha256(data).hexdigest()
    require(sha==shot['sha256'],'Native PNG hash changed: '+str(path))
    require(data[:8]==b'\x89PNG\r\n\x1a\n','Invalid PNG signature')
    offset,dimensions,ended=8,None,False
    while offset<len(data):
        require(offset+12<=len(data),'Truncated PNG chunk')
        length=struct.unpack_from('>I',data,offset)[0]
        kind=data[offset+4:offset+8]
        end=offset+length+12
        require(end<=len(data),'Truncated PNG payload')
        payload=data[offset+8:offset+8+length]
        crc=struct.unpack_from('>I',data,offset+8+length)[0]
        require(zlib.crc32(kind+payload)&0xffffffff==crc,'PNG CRC mismatch')
        if kind==b'IHDR':
            dimensions=list(struct.unpack_from('>II',payload))
        if kind==b'IEND':
            require(length==0 and end==len(data),'Invalid PNG final chunk')
            ended=True
            break
        offset=end
    require(ended and dimensions==[shot['width'],shot['height']],'PNG dimensions/end differ')
    return {'path':str(path),'sha256':sha,'bytes':len(data),'width':dimensions[0],'height':dimensions[1],
            'case':shot.get('case'),'native_capture_integrity_passed':True}


def methods(source,class_name):
    cleaned=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                   lambda m:' '*len(m[0]),source,flags=re.S)
    output={}
    pattern=r'^.*?'+re.escape(class_name)+r'::(\w+)\([^;\n]*'
    for found in re.finditer(pattern,cleaned,re.M):
        start=cleaned.find('{',found.end())
        require(start>=0,'Missing method body: '+found[1])
        depth=0
        for end in range(start,len(cleaned)):
            depth+=(cleaned[end]=='{')-(cleaned[end]=='}')
            if depth==0:
                require(found[1] not in output,'Duplicate method: '+found[1])
                output[found[1]]=source[found.start():end+1]
                break
    return output


def native_evidence(observed_external=None):
    before=read(BASE/'before-source-hashes.json')
    require(len(before)==45,'Expected preserved 45-file native baseline')
    current={p.relative_to(PROJECT).as_posix():digest(p) for p in (PROJECT/'Source').rglob('*') if p.is_file()}
    require(before.keys()==current.keys(),'Native files added or removed')
    changed={p for p,h in before.items() if current[p]!=h}
    external={}
    external_evidence=None
    if observed_external is not None:
        descriptor=read(observed_external)
        require(descriptor.get('authored_by_this_task') is False,'External delta must be explicitly unowned')
        external=descriptor.get('native_changes',{})
        hud='Source/LearnTopDown/CharacterSkillHUD.cpp'
        require(set(external)=={hud},'Only the explicitly observed concurrent HUD file may be excepted')
        require(external[hud].get('before_sha256')==before[hud] and
                external[hud].get('current_sha256')==current[hud] and before[hud]!=current[hud],
                'Observed external HUD baseline/current hashes differ or drifted')
        limit=descriptor.get('integration_limit','')
        require(isinstance(limit,str) and len(limit)>30,
                'External delta must explicitly describe its build/review integration limit')
        require(isinstance(descriptor.get('integrated_in_accepted_builds'),bool),
                'External delta must state whether the final accepted builds include its source')
        external_evidence={'descriptor':fingerprint(observed_external),'authored_by_this_task':False,
                           'native_changes':external,'integration_limit':limit,
                           'integrated_in_accepted_builds':descriptor['integrated_in_accepted_builds'],
                           'reviewed_or_functionally_verified_by_this_task':False}
    require(changed==AUTHORED|set(external),'Unexpected native changes: '+repr(sorted(changed)))
    for path,expected in before.items():
        require(digest(BASE/'before'/path)==expected,'Native backup differs: '+path)
    for path in AUTHORED:
        old=(BASE/'before'/path).read_bytes()
        new=(PROJECT/path).read_bytes()
        require(old.startswith(b'\xef\xbb\xbf')==new.startswith(b'\xef\xbb\xbf'),'Native BOM changed: '+path)
        require(b'\n' not in new.replace(b'\r\n',b''),'Native CRLF changed: '+path)
        new.decode('utf-8-sig')
    edits=read(BASE/'countess-approved-edits.json')
    require(len(edits)==4,'Expected four approved Countess Q-only edits')
    expected=(BASE/'before'/COUNTESS).read_bytes()
    for old,new in edits:
        a,b=[v.replace('\n','\r\n').encode('utf-8') for v in (old,new)]
        require(expected.count(a)==1,'Approved Q edit old bytes not unique')
        expected=expected.replace(a,b)
    require(expected==(PROJECT/COUNTESS).read_bytes(),'Countess differs from approved Q-only byte edits')
    old=(BASE/'before'/COUNTESS).read_text(encoding='utf-8-sig')
    new=(PROJECT/COUNTESS).read_text(encoding='utf-8-sig')
    a,b=methods(old,'UCountessSkillComponent'),methods(new,'UCountessSkillComponent')
    require(a.keys()==b.keys(),'Countess methods added or removed')
    changed_methods={n for n in a if a[n]!=b[n]}
    require(changed_methods=={'UCountessSkillComponent','SpawnBlinkDualSweep'},'Non-Q method changed')
    start,end='const TCHAR* Animations[]','ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
    require(old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],'Skill definitions changed')
    require('TEXT("Countess.Skills.QTone"), 1,' in new and
            'TEXT("Countess.Skills.QLengthScale"), 0.52f,' in new,'Q defaults differ from requested tone/52% length')

    old_s=(BASE/'before'/SPARROW).read_text(encoding='utf-8-sig')
    new_s=(PROJECT/SPARROW).read_text(encoding='utf-8-sig')
    namespace_start=new_s.index('\nnamespace\n{\n')
    namespace_end=new_s.index('\n}\n\nASparrowCharacter::ASparrowCharacter',namespace_start)+3
    helper=new_s[namespace_start:namespace_end]
    require('void ConfigureSparrowRogueCape(' in helper and ROGUE_MESH in helper and
            'TEXT(":Sparrow_Rogue_APEX")' in helper,'Cape helper is not restricted to original Rogue mesh/cloth')
    require(helper.count('void ConfigureSparrowRogueCape(')==1 and
            helper.count('bool ConfigureSparrowCapePointWind(')==1,'Expected two bounded cape helper functions')
    require('Cloth->SetDamping(Damping, LocalDamping);' in helper and
            'if (!SourceConfig->bUsePointBasedWindModel)' in helper and
            'Cloth->SetWind(Drag, Lift, SourceAirDensity, FVector(WindSpeed, 0.0f, 0.0f), OuterDrag, OuterLift);' in helper,
            'Cape helper differs from bounded damping/original-aerodynamics policy')
    require(not any(t in helper for t in ('SetTimer','TickComponent','SetActorTickEnabled','SetWorldLocation','->Modify(','SavePackage')),
            'Cape helper unexpectedly introduces a driver or persistent asset mutation')
    for clause in ('NewObject<UWindDirectionalSourceComponent>(Owner, TEXT("SparrowCapeWind"), RF_Transient)',
                   'Owner->AddInstanceComponent(Wind);','Wind->SetupAttachment(CharacterMesh);',
                   'Wind->SetRelativeLocation(FVector(0.0f, 5.0f, 0.0f));',
                   'constexpr float WindRadius = 20.0f;','constexpr float SourceOffset = 5.0f;',
                   'constexpr float LegacyWindScale = 100.0f * 25.0f;',
                   'Wind->SetWindType(EWindSourceType::Point);','Wind->SetRadius(WindRadius);',
                   'Wind->SetMinimumGustAmount(0.0f);','Wind->SetMaximumGustAmount(0.0f);',
                   'bWindApplied = ConfigureSparrowCapePointWind(CharacterMesh, WindSpeed);'):
        require(clause in helper,'Bounded original-model point wind contract missing: '+clause)
    require(helper.count('Wind->SetRelativeLocation(')==1,'Unexpected additional point wind location writes')
    restored=new_s[:namespace_start]+new_s[namespace_end:]
    added_includes=('ChaosCloth/ChaosClothConfig.h','ChaosCloth/ChaosClothingSimulationInteractor.h',
                    'ClothingAsset.h','ClothingSimulationInstance.h','ClothingSimulationInteractor.h',
                    'Engine/SkeletalMesh.h','HAL/IConsoleManager.h',
                    'Components/WindDirectionalSourceComponent.h','SceneProxies/WindSourceSceneProxy.h','TimerManager.h')
    for include in added_includes:
        line='#include "'+include+'"\n'
        require(restored.count(line)==1,'Unexpected cape include count')
        restored=restored.replace(line,'')
    sa,sb=methods(old_s,'ASparrowCharacter'),methods(new_s,'ASparrowCharacter')
    driver_names={'StartCapeFlutter','UpdateCapeFlutter','StopCapeFlutter'}
    require(set(sb)-set(sa)==driver_names and not set(sa)-set(sb) and
            {n for n in sa if sa[n]!=sb[n]}=={'BeginPlay','EndPlay'},
            'Sparrow locomotion/combat/movement methods changed')
    for name in driver_names:
        chunk=sb[name]+'\n\n'
        require(restored.count(chunk)==1,'Cape driver method cannot be removed exactly: '+name)
        restored=restored.replace(chunk,'')
    for call in ('\tConfigureSparrowRogueCape(GetMesh());\n','\tStartCapeFlutter();\n','\tStopCapeFlutter();\n'):
        require(restored.count(call)==1,'Cape lifecycle call must occur exactly once after removing the private driver')
        restored=restored.replace(call,'')
    require(restored==old_s,'Sparrow changed outside Rogue setup, private driver, and BeginPlay/EndPlay calls')
    start_driver,update_driver,stop_driver=[sb[n] for n in ('StartCapeFlutter','UpdateCapeFlutter','StopCapeFlutter')]
    for clause in ('CVarSparrowClothPresentation.GetValueOnGameThread() <= 0','CapeFlutterWind = Wind;',
                   'CapeFlutterStartTime = GetWorld()->GetTimeSeconds();','TimerParameters.bLoop = true;',
                   'TimerParameters.bMaxOncePerFrame = true;','TimerParameters.FirstDelay = 0.05f;',
                   'GetWorldTimerManager().SetTimer(CapeFlutterTimer, this, &ASparrowCharacter::UpdateCapeFlutter, 0.05f, TimerParameters);'):
        require(clause in start_driver,'Cape 20Hz owner timer setup differs: '+clause)
    for clause in ('Wind->GetOwner() != this','Wind->GetAttachParent() != CharacterMesh',
                   'StopCapeFlutter();','World->GetTimeSeconds()) - CapeFlutterStartTime',
                   '110.0 + 50.0 * FMath::Sin(TwoPi * 0.65 * Age)',
                   '20.0 * FMath::Sin(TwoPi * 1.15 * Age + 0.8)',
                   '1.3 * FMath::Sin(TwoPi * 0.48 * Age)',
                   '0.7 * FMath::Sin(TwoPi * 0.83 * Age + 0.5)',
                   '1.0f - (25.0f + FMath::Square(Lateral)) / 400.0f',
                   'Wind->SetRelativeLocation(FVector(Lateral, 5.0f, 0.0f));',
                   'Wind->SetSpeed(TargetSpeed / (100.0f * 25.0f * Falloff));'):
        require(clause in update_driver,'Bounded cape wind update differs: '+clause)
    require('World->GetTimerManager().ClearTimer(CapeFlutterTimer);' in stop_driver and
            'CapeFlutterTimer.Invalidate();' in stop_driver and 'CapeFlutterWind.Reset();' in stop_driver,
            'Cape timer/weak-source cleanup missing')
    require(sb['EndPlay'].index('StopCapeFlutter();')<sb['EndPlay'].index('Super::EndPlay('),
            'Cape timer is not stopped before pawn EndPlay')
    for name,value in (('WindSpeed','180.0f'),('Damping','0.08f'),('LocalDamping','0.12f')):
        require('TEXT("Sparrow.Cloth.'+name+'"), '+value+',' in helper,'Accepted cape native default differs: '+name)
    old_h=(BASE/'before'/SPARROW_HEADER).read_text(encoding='utf-8-sig')
    new_h=(PROJECT/SPARROW_HEADER).read_text(encoding='utf-8-sig')
    header_edits=[('class USpringArmComponent;','class USpringArmComponent;\nclass UWindDirectionalSourceComponent;'),
                  ('\tvoid ClearStopHeading();','\tvoid ClearStopHeading();\n\tvoid StartCapeFlutter();\n\tvoid UpdateCapeFlutter();\n\tvoid StopCapeFlutter();'),
                  ('\tbool bFinishingStopHeading = false;',
                   '\tbool bFinishingStopHeading = false;\n\n\tTWeakObjectPtr<UWindDirectionalSourceComponent> CapeFlutterWind;\n\tFTimerHandle CapeFlutterTimer;\n\tdouble CapeFlutterStartTime = 0.0;\n\tfloat CapeFlutterMaxSpeed = 0.0f;')]
    expected_header=old_h
    for before_text,after_text in header_edits:
        require(expected_header.count(before_text)==1,'Cape header anchor not unique')
        expected_header=expected_header.replace(before_text,after_text)
    require(expected_header==new_h,'Cape header change exceeds private weak source/timer state')
    viewport_edits=read(BASE/'viewport-approved-edits.json')
    require(len(viewport_edits)==2,'Expected include plus one approved editor-only viewport command')
    viewport_expected=(BASE/'before'/VIEWPORT_QA).read_bytes()
    for before_text,after_text in viewport_edits:
        before_bytes,after_bytes=[v.replace('\n','\r\n').encode('utf-8') for v in (before_text,after_text)]
        require(viewport_expected.count(before_bytes)==1,'Viewport approved edit anchor not unique')
        viewport_expected=viewport_expected.replace(before_bytes,after_bytes)
    require(viewport_expected==(PROJECT/VIEWPORT_QA).read_bytes(),'Viewport QA changed existing commands')
    require(viewport_expected.startswith(b'#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS\r\n')
            and viewport_expected.rstrip().endswith(b'#endif'),'Viewport QA command escaped editor/dev guard')
    mouse_edit=read(BASE/'mouse-approved-edit.json')
    require(mouse_edit['file']==MOUSE_QA and mouse_edit['before_sha256']==before[MOUSE_QA]
            and mouse_edit['after_sha256']==current[MOUSE_QA],'Approved mouse QA edit fingerprints differ')
    mouse_original=(BASE/'before'/MOUSE_QA).read_bytes()
    mouse_old,mouse_new=[mouse_edit[k].encode('utf-8') for k in ('old','new')]
    require(mouse_original.count(mouse_old)==1 and
            mouse_original.replace(mouse_old,mouse_new)==(PROJECT/MOUSE_QA).read_bytes(),
            'Mouse QA change exceeds the one approved viewport-coordinate inverse')
    require('GetViewportLocalToPixelScale' in mouse_edit['new'] and
            'Position / ToViewportPixelScale' in mouse_edit['new'],
            'Mouse QA injection does not invert the actual fixed-render pixel conversion')
    old_build=(BASE/'before'/BUILD).read_bytes()
    first=b'"ChaosCloth", "ClothingSystemRuntimeInterface"'
    second=b'"ChaosCloth", "ClothingSystemRuntimeInterface", "ClothingSystemRuntimeCommon"'
    require(old_build.count(first)==1 and old_build.replace(first,second)==(PROJECT/BUILD).read_bytes(),
            'Build dependency change exceeds original cloth runtime common dependency')
    diff=[]
    for path in sorted(AUTHORED):
        original=(BASE/'before'/path).read_text(encoding='utf-8-sig')
        final=(PROJECT/path).read_text(encoding='utf-8-sig')
        diff+=difflib.unified_diff(original.splitlines(True),final.splitlines(True),fromfile='before/'+path,tofile='after/'+path)
    (BASE/'native-change.diff').write_text(''.join(diff),encoding='utf-8')
    return {'authored_files':sorted(AUTHORED),'source_hashes':current,
            'other_native_files_unchanged':len(before)-len(AUTHORED)-len(external),
            'source_unowned_deltas':external_evidence,
            'countess_approved_edits':fingerprint(BASE/'countess-approved-edits.json'),
            'countess_exact_Q_only_byte_edits_verified':True,'Countess_skill_definitions_byte_identical':True,
            'Countess_unchanged_methods':sorted(set(a)-changed_methods),'W_E_R_native_unchanged':True,
            'Sparrow_changed_existing_methods':['BeginPlay','EndPlay'],'Sparrow_new_private_methods':sorted(driver_names),
            'Sparrow_other_methods_byte_identical':True,
            'original_shared_cloth_policy_byte_identical':True,
            'original_legacy_cloth_model_preserved':True,'wind_source_radius_cm':20,'wind_source_owner':'current Rogue pawn',
            'point_wind_component_setup_has_no_new_tick':True,
            'Rogue_helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),
            'cape_driver_method_hashes':{n:hashlib.sha256(sb[n].encode()).hexdigest() for n in sorted(driver_names)},
            'owner_bound_flutter_timer_hz':20,'flutter_timer_stopped_in_EndPlay':True,
            'no_new_actor_Tick':True,'source_encoding_and_CRLF_preserved':True,
            'viewport_QA_approved_edits':fingerprint(BASE/'viewport-approved-edits.json'),
            'mouse_QA_approved_edit':fingerprint(BASE/'mouse-approved-edit.json'),
            'other_mouse_QA_commands_byte_preserved':True,
            'existing_viewport_QA_commands_byte_preserved':True,'fixed_size_is_native_render_target_not_image_processing':True}


def run_common(directory,name,fps,cases,module):
    directory=Path(directory).resolve()
    path=directory/name
    report,launch,process=read(path),read(directory/'launch-result.json'),read(directory/'process-result.json')
    require(report.get('passed') is True and launch.get('passed') is True,'Failed report/launch: '+str(directory))
    require(launch.get('return_code')==0 and process.get('return_code')==0 and process.get('timed_out') is False,
            'Abnormal editor completion: '+str(directory))
    require(not launch.get('q_material_compile_errors') and not launch.get('shader_compile_errors'),'Shader compile errors')
    require(report.get('fixed_simulation_fps')==fps and len(report['cases'])==cases and
            all(c.get('passed') is True for c in report['cases']),'Wrong FPS/case count or case failure')
    require(report.get('protected_files_match') is True and report.get('baseline_after',{}).get('passed') is True
            and report['baseline_after']['protected_files']==7040,'Runtime did not preserve the current 7040-file baseline')
    require(report.get('capture_integrity',{}).get('passed') is True,'Runtime capture integrity failed')
    log_path=directory/'editor.log'
    log=log_path.read_text(encoding='utf-8',errors='replace')
    module_lines=[line for line in log.splitlines() if "InternalLoadLibrary: 'LearnTopDown'" in line]
    modules=sorted(set(re.findall(r'UnrealEditor-LearnTopDown-(\d+)\.dll','\n'.join(module_lines))))
    require(modules==[module],'Actual accepted native module not uniquely observed: '+str(directory))
    require(not any('Failed to compile Material' in line or 'Default Material will be used' in line for line in log.splitlines()),
            'Material compiler fallback observed')
    captures=[png(s) for s in report['screenshots']]
    require(bool(captures),'No actual native captures')
    require(all(c['width']==700 and c['height']==330 for c in captures),
            'Accepted native captures must all share the fixed 700x330 rendering size')
    evidence={'report':fingerprint(path),'launch':fingerprint(directory/'launch-result.json'),
              'process':fingerprint(directory/'process-result.json'),'editor_log':fingerprint(log_path),
              'actual_native_module_suffixes':modules,'actual_module_load_lines':module_lines,
              'fps':fps,'cases':cases,'captures':len(captures)}
    return report,launch,log,evidence,captures


def q_run(directory,fps,module):
    report,launch,log,evidence,captures=run_common(directory,f'countess-q-comparison-{fps}.json',fps,6,module)
    require(len(captures)==21 and launch.get('q_shader_compile_verified') is True,'Q captures/shader validation differ')
    if fps==30:
        require(report.get('native_fixed_viewport_size')==[700,330] and
                'CharacterVisualQA.ViewportSize requested=(700,330) actual=(700,330) match=1' in log,
                'Fresh final Q30 must use the actual fixed PIE render size')
    cases={c['name']:c.get('data',{}) for c in report['cases']}
    original,enhanced=cases['Q_original'],cases['Q_enhanced']
    require(original['damage']==enhanced['damage']==35 and original['target_health']==enhanced['target_health']==65,
            'Q damage changed')
    require(abs(original['first_damage_seconds']-enhanced['first_damage_seconds'])<=1/fps+.0001,'Q timing differs')
    require(len(original['phases'])==len(enhanced['phases'])==6,'Q needs six paired phases')
    for a,b in zip(original['phases'],enhanced['phases']):
        require(abs(a['elapsed']-b['elapsed'])<=1/fps+.0001,'Q phase times differ')
        for field in ('pawn','camera'):
            require(max(abs(x-y) for x,y in zip(a[field],b[field]))<.05,'Q paired '+field+' differs')
    for variant,tone,length in ((original,0,1),(enhanced,1,.52)):
        blades=[blade for phase in variant['phases'] for accent in phase['accents'] for blade in accent['blades']]
        require(bool(blades) and all('M_CountessQOutwardMuted' in b['material'] and
                abs(b['tone_mix']-tone)<.001 and 'NO_COLLISION' in b['collision'] for b in blades),
                'Actual Q MID tone/material/collision differs')
        outward=[b for b in blades if 'SM_CountessQOutwardCut' in b['mesh']]
        require(bool(outward) and all(abs(b['scale'][0]-length)<.001 and abs(b['scale'][1]-1)<.001
                and abs(b['scale'][2]-1)<.001 for b in outward),'Q visual lateral length differs')
    for name in ('E_with_original_Q_setting','E_with_enhanced_Q_setting'):
        require(cases[name]['target_health_minimum']==55,'E damage changed')
    evidence.update(kind='Q_tone_and_length_comparison',before_tone=0,after_tone=1,
                    before_lateral_scale=1,after_lateral_scale=.52,
                    color_and_length_change_together=True,case_data=cases)
    return evidence,captures


def cape_run(directory,fps,variant,module):
    report,launch,log,evidence,captures=run_common(directory,f'sparrow-cape-{fps}.json',fps,13,module)
    require(report['cape_variant']==variant and launch.get('variant')==variant,'Wrong cape variant')
    require(launch.get('full_trace_hashes_passed') is True and launch.get('runtime_configuration_logged') is True,
            'Cape full traces/runtime configuration were not verified')
    lines=[line for line in log.splitlines() if 'SparrowCape mode='+str(variant) in line]
    require(bool(lines),'Cape runtime configuration missing')
    require(all(ROGUE_CLOTH in line for line in lines),'Cape applied to a different cloth asset')
    if not variant:
        require(all('wind_applied=0' in line for line in lines),'Reused old variant unexpectedly applies new wind')
    require('CharacterVisualQA.ViewportSize requested=(700,330) actual=(700,330) match=1' in log,
            'Final cape comparison requires one explicitly fixed native PIE viewport')
    flutter=launch.get('flutter_timer_validation')
    native_starts={}
    if variant:
        require(any('wind_applied=1' in line and 'legacy_wind=1' in line for line in lines),
                'Cape point wind was not configured for the verified original legacy model')
        require(launch.get('point_wind_queries_passed') is True,'Point wind component query validation failed')
        point_rows=launch.get('point_wind_query_values',[])
        require(bool(point_rows),'Point wind query values missing')
        targets=[float(value) for line in lines for value in re.findall(r'requested_wind_speed_cm_s=([\d.]+)',line)]
        require(bool(targets),'Point wind requested speed missing')
        for row in point_rows:
            require(row.get('registered')==row.get('mesh_wind_enabled')==row.get('mesh_query_in_range')==1
                    and row.get('mesh_query_weight',0)>0,'Point wind is not active at the actual cloth query origin')
            require(row.get('outside_query_in_range')==0 and row.get('outside_query_weight')==0,
                    'Point wind extends beyond its bounded radius')
            require(abs(row.get('radius_cm',0)-20)<.001 and abs(row.get('offset_cm',0)-5)<.001,
                    'Point wind radius or offset differs')
            require(abs(row.get('source_speed_scene_m_s',-1)*.9375*100*25
                        -row.get('source_equivalent_legacy_cm_s',-1000))<.02,'Legacy scene wind scale was not compensated')
            require(any(abs(row.get('source_equivalent_legacy_cm_s',-1000)-target)<.02 for target in targets),
                    'Measured source-equivalent speed differs from the requested cape airflow')
        directions=[tuple(map(float,m)) for line in launch.get('point_wind_query_lines',[])
                    for m in re.findall(r'mesh_query_direction=\(([+-]?[\d.]+),([+-]?[\d.]+),([+-]?[\d.]+)\)',line)]
        require(bool(directions) and all(abs(z)<.00001 for x,y,z in directions),'Point wind adds a vertical direction')
        require(flutter and flutter.get('passed') is True and flutter.get('start_values_passed') is True and
                flutter.get('timer_cleanup_passed') is True and flutter.get('native_start_clock_phase_passed') is True
                and flutter.get('source_frame_phase_checks',0)>0 and flutter.get('phase_errors')==[],
                'Actual flutter timer lifecycle/native clock phase validation failed')
        require(flutter['maximum_native_start_vs_creation_clock_difference_seconds']<=1/fps+.00001,
                'Flutter native-start and pawn-age clocks differ beyond one frame')
        native_starts=flutter['native_start_values']
        require(bool(native_starts),'Flutter native start observations missing')
        for owner,entries in native_starts.items():
            require(len(entries)==1,'Flutter driver started more than once per owner')
            start=entries[0]
            require(abs(start['interval_seconds']-.05)<.000001 and start['max_once_per_frame']==1
                    and abs(start['max_wind_speed_cm_s']-180)<.001,'Flutter timer/defaults differ')
            stops=flutter['native_stop_values'].get(owner,[])
            require(any(s['active_timer_after_cleanup']==0 and s['time']>=start['start_time'] for s in stops),
                    'Destroyed cape owner retained a flutter timer')
    traces=[]
    source_phase_checks=0
    for case in report['cases']:
        desc=case['data']['full_simulation_trace']
        path=Path(desc['path']).resolve()
        require(path.is_relative_to(BASE.resolve()),'Trace outside task')
        raw=path.read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        require(sha==desc['sha256'],'Cape full trace hash differs')
        trace=json.loads(raw)
        require(trace['fps']==fps and trace['cape_variant']==variant and len(trace['samples'])==desc['samples'],
                'Cape full trace FPS/variant/sample count differs')
        rows=[r for r in trace['samples'] if r.get('pawn_class')=='BP_SparrowCharacter_C']
        if variant and case['name']!='room':
            configuration=case['data'].get('cape_configuration_at_spawn',{})
            require(abs(configuration['wind_speed_cvar']-180)<.001 and abs(configuration['damping_cvar']-.08)<.001
                    and abs(configuration['local_damping_cvar']-.12)<.001,
                    'Accepted cape QA must match the actual final native default values')
            sources=configuration.get('owner_wind_sources',[])
            require(len(sources)==1,'New cape must have one actual owner-local source')
            source=sources[0]
            require(source['class']=='/Script/Engine.WindDirectionalSourceComponent' and source['owner_is_current_pawn']
                    and source['point_wind'] and abs(source['radius_cm']-20)<.001 and source['mesh_origin_distance_cm']<=math.sqrt(29)+.01,
                    'New cape source owner/type/radius/origin differs')
            require(source['minimum_gust']==source['maximum_gust']==0,'Point wind unexpectedly adds gust driving')
            require(source['pulse_fit_using_creation_age']['matches'] is True,'Actual source does not fit the bounded driver timing')
        if variant and case['name']=='numeric_owner_cleanup':
            cleanup=case['data'].get('wind_owner_cleanup',{})
            require(bool(cleanup.get('source_paths_before')) and all(cleanup['source_references_invalid_after'])
                    and cleanup['remaining_tagged_sources']==[],'Destroyed owner left a point wind source')
        for row in rows:
            require(not row['cloth_disabled'] and not row['cloth_suspended'],'Cape simulation disabled/suspended')
            for cloth in row['cloth']:
                require(all(math.isfinite(cloth[k]) and cloth[k]<=limit for k,limit in
                            (('max_above_head_cm',30),('p95_above_head_cm',10),('max_radius_cm',130))),
                        'Cape exceeded existing stability bounds')
            sources=row.get('cape_observation',{}).get('owner_wind_sources',[])
            require(variant or not sources,'Old cape unexpectedly acquired the new source component')
            for source in sources:
                source_phase_checks+=1
                x,y,z=source['relative_location_cm']
                require(source['owner_is_current_pawn'] and abs(x)<=2.001 and abs(y-5)<.001 and abs(z)<.001,
                        'Flutter source no longer follows its owner inside the horizontal envelope')
                require(source['point_wind'] and abs(source['radius_cm']-20)<.001 and
                        source['mesh_origin_distance_cm']<=math.sqrt(29)+.01,'Flutter source radius/distance differs')
                falloff=1-(source['mesh_origin_distance_cm']/20)**2
                effective=source['raw_source_speed']*falloff*100*25
                require(abs(falloff-source['computed_point_falloff'])<.00001 and
                        abs(effective-source['computed_equivalent_legacy_wind_cm_per_second'])<.02 and
                        40-.02<=effective<=180+.02,'Flutter airflow falloff/conversions/range differ')
                require(source['pulse_fit_using_creation_age']['matches'] is True,
                        'Observed source speed/lateral displacement do not share a compatible driver time')
                owner=source['owner_name']
                require(owner in native_starts,'Source owner has no actual native flutter start log')
                native_age=row['time']-native_starts[owner][0]['start_time']
                require(abs(native_age-source['pawn_creation_age_seconds'])<=1/fps+.00001,
                        'Actual native flutter start clock differs from the observation clock')
        if variant and case['name']=='idle_flutter':
            observed=[source for row in rows for source in row.get('cape_observation',{}).get('owner_wind_sources',[])]
            require(bool(observed),'Idle flutter has no observed source trajectory')
            speeds=[s['computed_equivalent_legacy_wind_cm_per_second'] for s in observed]
            lateral=[s['relative_location_cm'][0] for s in observed]
            require(max(speeds)-min(speeds)>40 and max(lateral)-min(lateral)>1,
                    'Final idle observation does not contain changing airflow and side sway')
        traces.append({'case':case['name'],'path':str(path),'sha256':sha,'bytes':len(raw),
                       'samples':len(trace['samples']),'archer_frames':len(rows)})
    if variant:
        require(source_phase_checks==flutter['source_frame_phase_checks'],'Flutter phase-check count differs from the raw full traces')
    evidence.update(kind='cape_observation',variant=variant,full_traces=traces,
                    runtime_queued_configuration_lines=lines,
                    point_wind_queries=launch.get('point_wind_query_values',[]),
                    flutter_timer_validation=flutter,
                    runtime_queued_configuration_is_not_solver_readback=True,
                    motion_statistics_are_not_style_approval=True)
    return evidence,captures


def cape_summary(directory,fps,new_only,runs):
    directory=Path(directory).resolve()
    launch=read(directory/'launch-result.json')
    require(launch.get('passed') is True and launch.get('comparison_return_code')==0,'Cape summary launcher failed')
    name=f'sparrow-cape-stability-{fps}.json' if new_only else f'sparrow-cape-comparison-{fps}.json'
    path=directory/name
    summary=read(path)
    require(summary.get('passed') is True and summary['fps']==fps,'Cape derived summary failed')
    require(set(summary['runs'])==({'new'} if new_only else {'old','new'}),'Cape summary variant scope differs')
    for mode,evidence in runs.items():
        require(Path(summary['runs'][mode]['report']).resolve()==Path(evidence['report']['path']) and
                summary['runs'][mode]['sha256']==evidence['report']['sha256'],'Cape summary refers to a different source report')
        require(len(summary['runs'][mode]['cases'])==13,'Cape summary missing case observations')
        require(summary['runs'][mode]['source_module']=='UnrealEditor-LearnTopDown-'+evidence['actual_native_module_suffixes'][0]+'.dll',
                'Cape summary source module differs from actual load log')
    if new_only:
        require(summary.get('comparison') is None and summary.get('paired_native_captures')==0,
                '30fps new-only stability must not imply a before/after comparison')
    else:
        require(summary['case_count_per_variant']==13 and bool(summary.get('capture_pairs')),'60fps cape pairs missing')
        require(all(p.get('equal_viewport_size') is True for p in summary['capture_pairs']),'Cape paired viewport dimensions differ')
        require(summary.get('same_module_binary')==(runs['old']['actual_native_module_suffixes']==runs['new']['actual_native_module_suffixes']),
                'Cape summary misrepresents old/new native module identity')
        reused=launch.get('reused_old')
        old_directory=Path(runs['old']['report']['path']).parent.resolve()
        if old_directory!=(directory/'old').resolve():
            require(reused and reused.get('passed') is True and reused.get('copied_or_rewritten') is False,
                    'External old cape evidence must be explicitly revalidated in place')
            require(Path(reused['directory']).resolve()==old_directory and
                    Path(summary['reused_old_directory']).resolve()==old_directory,'Reused old directory differs')
            require(reused['case_count']==13 and reused['protected_before_contract_equal'] is True and
                    reused['current_protected_source_match']['passed'] is True,'Reused old evidence contract failed')
            expected_module='UnrealEditor-LearnTopDown-'+runs['old']['actual_native_module_suffixes'][0]+'.dll'
            require(reused['source_module']==expected_module,'Reused old source module differs')
            for field,key in (('report','report'),('launch','launch'),('process_result','process'),('editor_log','editor_log')):
                item=reused['artifacts'][field]
                require(Path(item['path']).resolve()==Path(runs['old'][key]['path']).resolve() and
                        item['sha256']==runs['old'][key]['sha256'],'Reused old artifact fingerprint differs: '+field)
            job_descriptor=reused['artifacts']['job']
            job_path=Path(job_descriptor['path'])
            require(digest(job_path)==job_descriptor['sha256'],'Reused old job fingerprint differs')
            job=read(job_path)
            require(job['fps']==60 and job['cape_variant']==0,'Reused old job variant/FPS differ')
            require(read(Path(job['baseline']))['protected_hashes']==read(BASE/'baseline-before.json')['protected_hashes'],
                    'Reused old original baseline contract differs')
            old_traces={t['path']:t['sha256'] for t in runs['old']['full_traces']}
            require(len(reused['full_traces_checked'])==13 and all(old_traces.get(str(Path(t['path']).resolve()))==t['sha256']
                    for t in reused['full_traces_checked']),'Reused old full traces differ')
            paired_old={str(Path(p['before']['image']).resolve()):p['before']['sha256'] for p in summary['capture_pairs']}
            require(len(reused['native_captures_checked'])==runs['old']['captures'] and
                    all(paired_old.get(str(Path(s['path']).resolve()))==s['sha256'] for s in reused['native_captures_checked']),
                    'Reused old native capture list differs')
    return {'summary':fingerprint(path),'launch':fingerprint(directory/'launch-result.json'),
            'scope':'new30stabilityonly' if new_only else '60fps_old_new_comparison',
            '30fps_before_after_difference_verified':False}


def authoring(directory,current):
    directory=Path(directory).resolve()
    path=directory/'tone-material.json'
    data=read(path)
    require(data.get('passed') is True and data.get('graph_connections_verified') is True,'Muted material authoring failed')
    for key in ('new_material_only','color_expressions_only_changed','all_non_color_shader_bytes_identical',
                'tone_zero_reconstructs_previous_RGB','shape_UV_reveal_noise_timing_unchanged','original_materials_unchanged'):
        require(data.get(key) is True,'Muted material contract failed: '+key)
    require(data['protected_changes']==[] and data['protected_additions']==[],'Author changed other protected files')
    require(set(data['graph_inputs_wired'])=={'UV','Clock','SpawnTime','Duration','Mode','ToneMix'},'Muted graph inputs differ')
    require(data['tone_parameter']['default']==1 and data['new_asset_sha256']==current[NEW_MATERIAL],
            'Muted saved material/default no longer matches authoring evidence')
    require(data['mesh_unchanged']['sha256']==current[OUTWARD_MESH],'Original outward mesh changed')
    source=PROJECT/'Tools/CharacterPipeline/countess_q_outward_assets.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    original=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='SHADER' for t in n.targets))
    restored=data['shader']
    require(len(data['colors'])==8,'Expected eight RGB-only tone edits')
    for entry in data['colors']:
        require(restored.count(entry['new_expression'])==1,'Muted RGB edit not unique')
        restored=restored.replace(entry['new_expression'],entry['old_literal'])
    require(restored==original,'Muted material changed non-color shader code')
    process=read(directory/'process-result.json')
    require(process.get('return_code')==0 and process.get('timed_out') is False,'Asset author editor did not finish normally')
    return {'report':fingerprint(path),'process':fingerprint(directory/'process-result.json'),
            'color_only_shader_reconstruction_verified':True,'original_mesh_sha256':current[OUTWARD_MESH],
            'original_bright_material_sha256':current[OLD_MATERIAL],'colors':data['colors']}


def q_source_parity(path,current_native,accepted_q_module,final_module,editor_build,compile_log):
    descriptor=read(path)
    require(descriptor['Q_source_sha256']==current_native['source_hashes'][COUNTESS],
            'Countess Q source changed after the accepted earlier-module QA')
    obj=Path(descriptor['Q_object']['path'])
    old_module=PROJECT/f'Binaries/Win64/UnrealEditor-LearnTopDown-{accepted_q_module}.dll'
    require(descriptor[f'editor_{accepted_q_module}_sha256']==digest(old_module),
            'Earlier accepted Q editor module differs from the preserved parity observation')
    build_log=Path(compile_log).read_text(encoding='utf-8',errors='replace')
    require('Result: Succeeded' in build_log and re.search(r'Compile.*CountessSkillComponent\.cpp',build_log),
            'Recorded successful editor build must compile the unchanged Countess source')
    return {'descriptor':fingerprint(path),'accepted_Q_module_suffix':accepted_q_module,
            'final_module_suffix':final_module,'Q_source_unchanged':True,
            'Q_object_recompiled_in_recorded_prior_build':True,'object_bytes_unchanged_claimed':False,
            'earlier_object_sha256':descriptor['Q_object']['sha256'],
            'current_native_object':fingerprint(obj),'earlier_editor_module':fingerprint(old_module),
            'Countess_compile_evidence':fingerprint(compile_log),'final_editor_build':fingerprint(editor_build),
            'final_build_may_reuse_the_existing_UBT_native_object':True,'final_module_Q_30fps_regression_required':True,
            'scope':'Countess Q source parity and fresh final-module 30fps validation; compiled object bytes may differ after PCH/build changes'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--assets',type=Path,default=BASE/'assets-03')
    parser.add_argument('--q60',type=Path,default=BASE/'q-tone-60-02')
    parser.add_argument('--q30',type=Path,default=BASE/'q-tone-30-03')
    parser.add_argument('--cape60',type=Path,required=True)
    parser.add_argument('--cape30',type=Path,required=True)
    parser.add_argument('--module',default='6168')
    parser.add_argument('--q60-module',default='6165')
    parser.add_argument('--old-cape-module',help='Must equal the final module for the final paired cape validation.')
    parser.add_argument('--q-parity',type=Path,default=BASE/'Q-binary-parity-before-6166.json')
    parser.add_argument('--q-compile-evidence',type=Path,default=BASE/'build-editor-03.log')
    parser.add_argument('--editor-build',type=Path,default=BASE/'build-editor-05.log')
    parser.add_argument('--game-build',type=Path,default=BASE/'build-game-04.log')
    parser.add_argument('--visual-review',type=Path,default=BASE/'visual-review.json')
    parser.add_argument('--observed-external',type=Path,
                        help='Root-observed, hash-pinned concurrent HUD delta; never permits any other file.')
    parser.add_argument('--editor-restart-required',action='store_true')
    args=parser.parse_args()
    require(args.old_cape_module is None or args.old_cape_module==args.module,
            'Final cape before/after evidence must run the same final native module')
    args.old_cape_module=args.module
    native=native_evidence(args.observed_external)
    builds=[]
    for path in (args.editor_build,args.game_build):
        require('Result: Succeeded' in path.read_text(encoding='utf-8',errors='replace'),'Native build failed: '+str(path))
        builds.append(fingerprint(path))
    module=PROJECT/f'Binaries/Win64/UnrealEditor-LearnTopDown-{args.module}.dll'
    require(read(PROJECT/'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown']==module.name,'Current editor module manifest differs')
    parity=q_source_parity(args.q_parity,native,args.q60_module,args.module,args.editor_build,args.q_compile_evidence) if args.q60_module!=args.module else None
    runs,images=[],[]
    for path,fps in ((args.q60,60),(args.q30,30)):
        evidence,captures=q_run(path,fps,args.q60_module if fps==60 else args.module)
        runs.append(evidence);images+=captures
    # A final comparison may explicitly reuse the already completed old variant.
    # Resolve its immutable report from the paired summary, never from a candidate new run.
    paired=read(args.cape60/'sparrow-cape-comparison-60.json')
    old_directory=Path(paired['runs']['old']['report']).resolve().parent
    cape_runs={}
    for name,path,fps,variant in (('old60',old_directory,60,0),('new60',args.cape60/'new',60,1),('new30',args.cape30/'new',30,1)):
        evidence,captures=cape_run(path,fps,variant,args.old_cape_module if variant==0 else args.module)
        cape_runs[name]=evidence
        runs.append(evidence);images+=captures
    summaries=[cape_summary(args.cape60,60,False,{'old':cape_runs['old60'],'new':cape_runs['new60']}),
               cape_summary(args.cape30,30,True,{'new':cape_runs['new30']})]
    require(len({i['path'] for i in images})==len(images),'Duplicate native capture paths')
    review=read(args.visual_review)
    require(review.get('render_review_passed') is True and review.get('user_style_approval') is False,'Explicit visual review incomplete or user approval falsely implied')
    reviewed=review.get('reviewed_source_images',[])
    require(bool(reviewed),'Explicit reviewed source-image list missing')
    accepted={i['path']:i['sha256'] for i in images}
    for item in reviewed:
        path=str(Path(item.get('path',item.get('image'))).resolve())
        require(accepted.get(path)==item['sha256'],'Reviewed source not in accepted native captures')

    # One full read after QA/source verification; reuse this map for preservation,
    # authoring comparisons and the new hash-only baseline instead of calling verify().
    before=read(BASE/'baseline-before.json')['protected_hashes']
    require(len(before)==7040,'Expected original 7040-file protected baseline')
    current=protected_hashes()
    require(all(current.get(p)==h for p,h in before.items()),'An existing Content/Config/project file changed')
    require(len(current)==7041 and set(current)-set(before)=={NEW_MATERIAL},'Only one new private Q material may be added')
    assets=authoring(args.assets,current)
    baseline_path=BASE/'baseline-current.json'
    baseline={'schema_version':1,'project':str(PROJECT),'protected_hashes':current,'baseline_kind':'hashes_only',
              'content_backup_created_by_this_seal':False,'parent_baseline':fingerprint(BASE/'baseline-before.json'),
              'source_hashes_at_seal':native['source_hashes']}
    if baseline_path.exists():
        require(read(baseline_path)['protected_hashes']==current,'Existing current baseline differs')
    else:
        baseline_path.write_text(json.dumps(baseline,indent=2),encoding='utf-8')
    result={'passed':True,'scope':'Countess Q muted tone/52 percent lateral length; Sparrow Rogue cape damping and bounded 20Hz horizontal flutter',
            'cases':sum(r['cases'] for r in runs),'Q_comparison_cases':12,'cape_observation_cases':39,
            'native_captures':len(images),'verification':runs,'native_images':images,'cape_summaries':summaries,
            'native_source':native,'authoring':assets,'builds':builds,'editor_module':fingerprint(module),
            'Q_cross_module_source_parity':parity,
            'old_cape_source_report':cape_runs['old60']['report'],
            'old_cape_reused_in_place':old_directory.resolve()!=(args.cape60/'old').resolve(),
            'old_cape_mode_zero_preserved_in_final_source':True,
            'source_unowned_deltas':native['source_unowned_deltas'],
            'observed_external_source_included_in_accepted_builds':native['source_unowned_deltas']['integrated_in_accepted_builds']
                if native['source_unowned_deltas'] else None,
            'editor_module_manifest':fingerprint(PROJECT/'Binaries/Win64/UnrealEditor.modules'),
            'render_review_passed':True,'user_style_approval':False,'visual_judgment_automatically_approved':False,
            'explicitly_reviewed_source_images':len(reviewed),'visual_review':fingerprint(args.visual_review),
            'original_protected_files_preserved':len(before),'current_protected_files':len(current),
            'protected_hashes_full_passes_in_this_seal':1,'new_content_files':[NEW_MATERIAL],
            'new_material_sha256':current[NEW_MATERIAL],'current_baseline':fingerprint(baseline_path),
            'Q_color_and_lateral_length_changed_together_in_comparison':True,
            'Q_opacity_and_reveal_timing_unchanged':True,'Q_damage_range_cooldown_unchanged':True,
            'E_W_R_unchanged':True,'cape_60fps_old_new_comparison':True,'cape_30fps_new_variant_stability_only':True,
            'cape_30fps_before_after_improvement_verified':False,
            'runtime_wind_evidence':'CPU wind component observations and bounded timer-clock fit; no solver phase readback',
            'physical_OS_input_tested':False,'continuous_video':False,'GPU_performance_benchmark':False,
            'user_editor_restart_required':args.editor_restart_required,
            'restart_status_supplied_from_external_live_editor_module_observation':True}
    require(result['cases']==51,'Expected 12 Q cases plus 39 cape observations')
    (BASE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'cases':result['cases'],'captures':len(images),'protected_files':len(current),
                      'result':str(BASE/'result.json')}))


if __name__=='__main__':
    try:
        main()
    except Exception:
        (BASE/'result.json').write_text(json.dumps({'passed':False,'status':'seal_failed','error':traceback.format_exc(),
            'user_style_approval':False,'visual_judgment_automatically_approved':False},indent=2),encoding='utf-8')
        raise
