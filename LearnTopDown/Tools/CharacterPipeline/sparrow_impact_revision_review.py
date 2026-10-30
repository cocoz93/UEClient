"""Latest scoped visual/functional review, reusing the established actual game rig."""
import os
from pathlib import Path
import runpy
import shutil
import unreal

def author(out):
    folder=Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline'
    if os.environ.get('SPARROW_IMPACT_AUTHOR') == 'qwdv':
        results=[]
        for name in ('sparrow_ascended_shot_materials.py','sparrow_flame_studies.py','sparrow_final_impact_material.py'):
            result=runpy.run_path(str(folder/name))['author'](out)
            assert result['passed'],name
            results.append(result)
        return {'passed':True,'authors':results}
    if os.environ.get('SPARROW_IMPACT_AUTHOR') == 'f':
        result=runpy.run_path(str(folder/'sparrow_arsenal_adoption.py'))['author'](out)
        assert result['passed']
        result=runpy.run_path(str(folder/'sparrow_ascended_arsenal_materials.py'))['author'](out)
        assert result['passed']
        return result
    result=runpy.run_path(str(folder/'sparrow_celestial_review.py'))['author'](out)
    result['w_finisher']=runpy.run_path(str(folder/'sparrow_final_impact_material.py'))['author'](out)
    return result

def sequence(rig):
    folder=Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline'
    phase=os.environ.get('SPARROW_IMPACT_PHASE','applied')
    os.environ['SPARROW_SERAPH_POLISH']='1'
    os.environ['SPARROW_ASCENDED_RECRAFT']='1'
    if phase=='all':
        for part in ('applied','v','s'):
            os.environ['SPARROW_IMPACT_PHASE']=part
            yield from sequence(rig)
        os.environ['SPARROW_IMPACT_PHASE']='all'
    elif phase=='f_form':
        os.environ['SPARROW_ASCENDED_KEYS']='F'
        os.environ['SPARROW_ASCENDED_MODES']='form'
        yield from runpy.run_path(str(folder/'sparrow_ascended_arsenal_review.py'))['sequence'](rig)
    elif phase=='fa':
        for keys,modes,name in [('F','normal,form','f'),('A','form','a')]:
            os.environ['SPARROW_ASCENDED_KEYS']=keys
            os.environ['SPARROW_ASCENDED_MODES']=modes
            yield from runpy.run_path(str(folder/'sparrow_ascended_arsenal_review.py'))['sequence'](rig)
            shutil.copyfile(rig['OUT']/'sparrow-ascended-arsenal.json',rig['OUT']/('revised-'+name+'.json'))
    elif phase in ('refined','reart'):
        rig['cmd']('Sparrow.ArsenalStudy.R 0')
        rig['cmd']('Sparrow.ArsenalStudy.S 10')
        rig['cmd']('Sparrow.FlameStudy.V 3')
        batches=[('F,D','normal,form','fd'),('A,Q' if phase=='reart' else 'W,Q','form','aq' if phase=='reart' else 'wq')]
        for keys,modes,name in batches:
            os.environ['SPARROW_ASCENDED_KEYS']=keys
            os.environ['SPARROW_ASCENDED_MODES']=modes
            yield from runpy.run_path(str(folder/'sparrow_ascended_arsenal_review.py'))['sequence'](rig)
            shutil.copyfile(rig['OUT']/'sparrow-ascended-arsenal.json',rig['OUT']/('revised-'+name+'.json'))
        for part in ('v','s'):
            os.environ['SPARROW_IMPACT_PHASE']=part
            yield from sequence(rig)
        os.environ['SPARROW_IMPACT_PHASE']=phase
    elif phase in ('applied','recovery'):
        if phase=='recovery' and os.environ.get('SPARROW_REART_Q_SYNC')=='1':
            rig['check'](unreal.SystemLibrary.get_console_variable_int_value('Sparrow.ArsenalStudy.S')==10,
                         'fresh game installs S10 by default without a preview override')
        os.environ['SPARROW_CELESTIAL_PHASE']=phase
        os.environ.setdefault('SPARROW_CELESTIAL_KEYS','W,F,A,D')
        yield from runpy.run_path(str(folder/'sparrow_celestial_review.py'))['sequence'](rig)
        if phase=='recovery' and os.environ.get('SPARROW_REART_Q_SYNC')=='1':
            rig['switch']('countess'); yield .2
            rig['switch']('sparrow'); yield .7
            rig['use']('V',offset=(950,0)); yield 3.
            rig['case']('Q_delayed_owner_cleanup')
            targets=rig['layout']([(420,0),(700,0),(600,370)]); yield .15
            initial=[rig['health'](target) for target in targets]
            rig['use']('Q',offset=(420,0)); yield .45
            rig['check']([rig['health'](target) for target in targets]==initial,
                         'transformed Q never damages before its slow first contact')
            rig['switch']('countess'); yield 1.2
            rig['check']([rig['health'](target) for target in targets]==initial,
                         'switching owner before delayed Q contact clears pending damage')
    elif phase=='v':
        os.environ['SPARROW_NATIVE_WING_PHASE']='entry'
        yield from runpy.run_path(str(folder/'sparrow_native_wing_review.py'))['sequence'](rig)
    elif phase=='s':
        os.environ['SERAPH_S_CASES']='S9,S10'
        yield from runpy.run_path(str(folder/'sparrow_seraph_s_review.py'))['sequence'](rig)
    else:
        raise ValueError(phase)
