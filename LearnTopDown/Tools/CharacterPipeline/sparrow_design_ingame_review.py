"""Selectable actual gameplay captures for the eighteen design boards; reuse the existing rig."""
import json
import os
from pathlib import Path
import runpy
import shutil
import unreal

SELECTORS = {'Q':'Sparrow.DesignIngame.Q', 'V':'Sparrow.DesignIngame.V',
             'A':'Sparrow.SunArrow.Style', 'E':'Sparrow.EDesign.Style',
             'F':'Sparrow.FDesign.Style', 'D':'Sparrow.BowMuzzle.Style',
             'W':'Sparrow.Renaissance.W', 'R':'Sparrow.ArsenalStudy.R', 'S':'Sparrow.ArsenalStudy.S'}

def author(out):
    folder=Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline'
    scripts={'F':'sparrow_f_design_materials.py', 'A':'sparrow_sun_arrow_materials.py',
             'E':'sparrow_e_design_materials.py', 'D':'sparrow_bow_muzzle_study_materials.py',
             'QV':'sparrow_qv_design_materials.py', 'WRS':'sparrow_wrs_renaissance_materials.py',
             'SR':'sparrow_sr_craft_materials.py'}
    selected=os.environ.get('SPARROW_INGAME_AUTHOR','F,A,E,D,QV').split(',')
    rows=[]
    for key in selected:
        if key == 'none': continue
        if key in ('PLUME_QV', 'PLUME_E', 'PLUME_D'):
            script = {'PLUME_QV':'sparrow_qv_design_materials.py', 'PLUME_E':'sparrow_e_design_materials.py', 'PLUME_D':'sparrow_d_plume_materials.py'}[key]
            function = 'author' if key == 'PLUME_D' else 'author_plume'
            result=runpy.run_path(str(folder/script))[function](out)
            assert result['passed'],key
            rows.append({'key':key,'script':script+':'+function,'passed':True})
            continue
        if key == 'V_AUDIT':
            result=runpy.run_path(str(folder/'sparrow_qv_design_materials.py'))['audit_v6_geometry'](out)
            assert result['passed'], key
            rows.append({'key':key,'passed':True})
            continue
        if key == 'E7_TEXTURE':
            _, row=runpy.run_path(str(folder/'sparrow_e_design_materials.py'))['_bow_art']()
            rows.append({'key':key,'texture':row,'passed':True})
            continue
        if key == 'Q7':
            helper=runpy.run_path(str(folder/'sparrow_qv_design_materials.py'))
            audit=helper['audit_q7'](out)
            assert audit['passed'], 'Q7 source audit'
            result=helper['author_q7'](out)
            assert result['passed'], key
            rows.append({'key':key,'script':'sparrow_qv_design_materials.py:author_q7','passed':True})
            continue
        if key == 'V6':
            result=runpy.run_path(str(folder/'sparrow_qv_design_materials.py'))['author_v6'](out)
            assert result['passed'], key
            rows.append({'key':key,'script':'sparrow_qv_design_materials.py:author_v6','passed':True})
            continue
        result=runpy.run_path(str(folder/scripts[key]))['author'](out)
        assert result['passed'], key
        rows.append({'key':key,'script':scripts[key],'passed':True})
    # OBJ reimport can retain a section's old material ID after the generated
    # mesh is reduced to one slot. Normalize only this review's owned meshes.
    slots=runpy.run_path(str(folder/'sparrow_design_mesh_slots.py'))['author'](out)
    assert slots['passed'], 'generated mesh material slots'
    report={'passed':True,'authors':rows}
    (Path(out)/'ingame-author.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

def sequence(rig):
    folder=Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline'
    env=runpy.run_path(str(folder/'sparrow_design_reset_review.py'))['environment']
    selected=os.environ.get('SPARROW_INGAME_CASES','Q1,Q2,Q3,E1,E2,E3,A1,A2,F1,F2,F3,F4,D1,D2,D3,V1,V2,V3').split(',')
    report={'passed':False,'cases':[],'fps':rig['FPS']}
    out=rig['OUT']
    saved_selectors={key:unreal.SystemLibrary.get_console_variable_int_value(value) for key,value in SELECTORS.items()}
    saved_reference=unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Sharp.Reference')
    audit_solar = os.environ.get('SPARROW_INGAME_SOLAR_AUDIT') == '1'
    if audit_solar: rig['cmd']('Sparrow.SunArrow.Audit 1')
    audit_bow = os.environ.get('SPARROW_INGAME_BOW_AUDIT') == '1'
    if audit_bow: rig['cmd']('Sparrow.BowMuzzle.Audit 1')
    try:
        for value in SELECTORS.values(): rig['cmd'](value+' 0')
        rig['cmd']('Sparrow.Sharp.Reference 0')
        for ident in selected:
            key,style=ident[0],int(ident[1:])
            selector='Sparrow.Sharp.Reference' if key=='S' and style>=100 else SELECTORS[key]
            value=style-100 if key=='S' and style>=100 else style
            rig['cmd'](selector+' '+str(value))
            rig['check'](unreal.SystemLibrary.get_console_variable_int_value(selector)==value,ident+' selector enabled')
            scope=dict(rig)
            scope['case']=lambda value, prefix=ident: rig['case'](prefix+'_'+value)
            scope['capture']=lambda value, prefix=ident: rig['capture'](prefix+'_'+value)
            if key=='V':
                script='sparrow_native_wing_review.py'; source='sparrow-native-wing-review.json'
                values={'SPARROW_NATIVE_WING_PHASE':'entry'}
            else:
                script='sparrow_ascended_arsenal_review.py'; source='sparrow-ascended-arsenal.json'
                review_modes = 'normal,form' if ident in os.environ.get('SPARROW_INGAME_FORM_IDS','').split(',') else os.environ.get('SPARROW_INGAME_MODES','normal')
                values={'SPARROW_ASCENDED_KEYS':key, 'SPARROW_ASCENDED_MODES':os.environ.get('SPARROW_INGAME_Q_MODES','form') if key=='Q' else review_modes,
                        'SPARROW_ASCENDED_RECRAFT':'1', 'SPARROW_GAME_DESIGN_REVIEW':'1', 'SPARROW_SERAPH_POLISH':'1',
                        'SPARROW_REART_Q_SYNC':'0','ASCENDED_ARSENAL_RECOVERY':'0'}
            with env(values):
                generator=runpy.run_path(str(folder/script))['sequence'](scope)
                try:
                    for delay in generator:
                        clip=rig['STATE'].get('video_clip')
                        if clip and not clip['prefix'].startswith(ident+'_'):
                            clip['prefix']=ident+'_'+clip['prefix'];clip['case']=ident+'_'+clip['case']
                        yield delay
                finally: generator.close()
            destination=out/(ident+'.json')
            shutil.copyfile(out/source,destination)
            data=json.loads(destination.read_text(encoding='utf-8'))
            rig['check'](data['passed'],ident+' scoped gameplay checks pass')
            report['cases'].append({'id':ident,'report':destination.name,'passed':data['passed']})
            (out/'ingame-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
            rig['cmd'](selector+' 0')
        report['passed']=True
    finally:
        if audit_solar: rig['cmd']('Sparrow.SunArrow.Audit 0')
        if audit_bow: rig['cmd']('Sparrow.BowMuzzle.Audit 0')
        for key,value in SELECTORS.items(): rig['cmd'](value+' '+str(saved_selectors[key]))
        rig['cmd']('Sparrow.Sharp.Reference '+str(saved_reference))
        report['defaults_restored']={key:unreal.SystemLibrary.get_console_variable_int_value(value) for key,value in SELECTORS.items()}
        (out/'ingame-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
