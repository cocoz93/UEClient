"""Create only the project-owned tapered Q slash material; source pack stays intact."""
import json
import os
from pathlib import Path
import traceback
import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
PATH = '/Game/TopDown/Characters/Countess/Materials/M_CountessQImpactAccent'
report = {'passed':False, 'asset':PATH}
try:
    material = unreal.load_asset(PATH)
    if material is None:
        folder,name=PATH.rsplit('/',1)
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    material.modify()
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    library=unreal.MaterialEditingLibrary
    existing=list(library.get_material_expressions(material))
    cursor=0
    def node(kind,**properties):
        global cursor
        expected='MaterialExpression'+kind
        if cursor < len(existing):
            result=existing[cursor]
            if result.get_class().get_name()!=expected:
                raise RuntimeError('Existing Q graph differs at node '+str(cursor))
        else:
            result=library.create_material_expression(material,getattr(unreal,expected))
        cursor+=1
        for key,value in properties.items(): result.set_editor_property(key,value)
        return result
    def constant(value): return node('Constant',r=float(value))
    def operation(kind,a,b=None):
        result=node(kind)
        inputs=list(library.get_material_expression_input_names(result))
        if not inputs or (b is not None and len(inputs)<2):
            raise RuntimeError('Unexpected material inputs: '+kind+' '+str(inputs))
        first=inputs[0]
        second=inputs[1] if b is not None else None
        if not library.connect_material_expressions(a,'',result,first):
            raise RuntimeError('Unconnected material input: '+kind+'.'+first)
        if b is not None and not library.connect_material_expressions(b,'',result,second):
            raise RuntimeError('Unconnected material input: '+kind+'.'+second)
        return result
    uv=node('TextureCoordinate')
    u=node('ComponentMask',r=True,g=False,b=False,a=False)
    v=node('ComponentMask',r=False,g=True,b=False,a=False)
    for mask in (u,v):
        first=library.get_material_expression_input_names(mask)[0]
        if not library.connect_material_expressions(uv,'',mask,first):
            raise RuntimeError('Unconnected UV mask')
    sine=operation('Sine',operation('Multiply',u,constant(.5)))
    center=operation('Add',constant(.5),operation('Multiply',sine,constant(.10)))
    distance=operation('Abs',operation('Subtract',v,center))
    width=operation('Saturate',operation('Subtract',constant(1),operation('Multiply',distance,constant(16))))
    tips=operation('Power',operation('Saturate',sine),constant(.65))
    edge=operation('Multiply',operation('Power',width,constant(2)),tips)
    core=operation('Multiply',operation('Power',width,constant(12)),tips)
    red=node('Constant3Vector',constant=unreal.LinearColor(5,.015,.005,1))
    hot=node('Constant3Vector',constant=unreal.LinearColor(26,8,6,1))
    color=operation('Add',operation('Multiply',edge,red),operation('Multiply',core,hot))
    time=node('Time',ignore_pause=False)
    start=node('ScalarParameter',parameter_name='SpawnTime',default_value=0)
    duration=node('ScalarParameter',parameter_name='Duration',default_value=.3)
    age=operation('Divide',operation('Subtract',time,start),duration)
    fade=operation('Power',operation('Saturate',operation('Subtract',constant(1),age)),constant(1.5))
    if not library.connect_material_property(color,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Unconnected emissive output')
    if not library.connect_material_property(operation('Multiply',edge,fade),'',unreal.MaterialProperty.MP_OPACITY):
        raise RuntimeError('Unconnected opacity output')
    if existing and cursor!=len(existing):
        raise RuntimeError('Unexpected extra nodes in the owned Q material')
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material,False):
        raise RuntimeError('Q accent material could not be saved')
    report.update(passed=True,graph_connections_verified=True,shader_compile_verified=False,
                  original_materials_changed=False,shape='curved tapered slash with a thin hot core',
                  duration_seconds=.3,collision=False)
except Exception:
    report['error']=traceback.format_exc()
finally:
    (OUT/'material.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
