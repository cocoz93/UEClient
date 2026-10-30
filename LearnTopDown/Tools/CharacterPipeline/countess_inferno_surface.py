"""Private A/V surfaces: readable shadows, socket swipes and a feathered V blackout.

Only Quality20261023/Inferno packages are saved. Version 2 uses continuous
shadow/ink alpha and private authored-particle copies; source packs are untouched.
The parent owns editor execution and actual visual acceptance.
"""
import hashlib
import json
from pathlib import Path

import unreal


FOLDER = '/Game/TopDown/Characters/Countess/Quality20261023/Inferno'
SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
VERSION = '2'
META = 'CountessInfernoQualityVersion'
WATER = '/Game/ParagonCountess/FX/Materials/Water/M_WaterImpact_Strand_Masked'
PROTECTED = (SOURCE, NOISE, INK,
    '/Game/TopDown/Characters/Countess/FX/SM_CountessQDualSweep',
    '/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail',
    '/Game/TopDown/Characters/Countess/FX/P_CountessW_VeilRing',
    '/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing', WATER)

SHADOW_SHADER = r'''
float n = pow(saturate((Noise-.0075)/(.5841-.0075)), .55);
float ink = pow(saturate((Ink-.0009)/(.3140-.0009)), .30);
float grain = saturate(n*.52 + ink*.48);
float vein = pow(saturate(1-abs(n-ink*.62-.16)*12), 3)*smoothstep(.25,.65,grain);
float rim = pow(saturate(Facing), 2.7) * (.55+.45*grain);
float3 charcoal = float3(.013, .0008, .0022) + float3(.030, .0015, .004)*grain*grain;
float3 edge = float3(1.0, .010, .033)*rim;
float3 etched = float3(.30, .003, .011)*vein;
float t = saturate((Clock-Start)/max(Duration,.01));
// Coherent ink islands erode only at retirement; no screen-door opacity or pixel hash.
float erode = 1-smoothstep(grain*.45+.12,grain*.45+.51,t);
float alpha = .90*erode*pow(1-t,.65);
return float4((charcoal+edge+etched)*max(Energy,0)*pow(1-t,.45),alpha);
'''

BLADE_SHADER = r'''
float n = pow(saturate((Noise-.0075)/(.5841-.0075)), .55);
float ink = pow(saturate((Ink-.0009)/(.3140-.0009)), .30);
float field = saturate(n*.62+ink*.38);
float ends = pow(saturate(sin(saturate(UV.x)*3.14159265)), .48);
float across = abs(UV.y-.5)*2;
float body = (1-smoothstep(.58,.99,across))*ends;
float razor = exp(-pow((UV.y-.72)/.095,2))*ends;
float filament = exp(-pow((UV.y-.28)/.052,2))*ends*.30;
float head = saturate(Phase*2.4+.24);
float revealed = 1-smoothstep(head-.055,head+.045,UV.x);
float erosion = smoothstep(.80,1.0,Phase);
float survive = 1-smoothstep(field*.50+.22,field*.50+.65,erosion);
float torn = .70+.30*smoothstep(.15,.68,field);
float3 charcoal = float3(.018,.0009,.003)*body;
float3 blood = float3(.39,.004,.014)*body*field*field;
float3 edge = float3(1.85,.017,.052)*(razor+filament)*(.65+.35*field);
float alpha = saturate(max(body*torn*.88,razor*.96)*revealed*survive*Opacity);
return float4((charcoal+blood+edge)*max(Energy,0),alpha);
'''

INK_SHADER = r'''
float n = pow(saturate((Noise-.0075)/(.5841-.0075)),.55);
float ink = pow(saturate((Ink-.0009)/(.3140-.0009)),.30);
float u = saturate(UV.x);
float2 p = UV*2-1;
float taper = pow(saturate(sin(u*3.14159265)),.55);
float bend = .18*sin(u*5.4+Seed)+.07*(n-.5);
float width = (Shape>3 ? .29 : .16)*taper+.015;
float d = abs(p.y-bend);
float body = 1-smoothstep(width*.48,width,d);
float swept = exp(-pow((p.y-bend-width*.65)/.055,2))*taper;
float flow = .62+.38*smoothstep(.10,.72,n*.35+ink*.65);
float endFade = smoothstep(0,.10,u)*(1-smoothstep(.86,1,u));
float fade = saturate(Fade);
float erode = 1-smoothstep(ink*.45+.18,ink*.45+.55,1-fade);
float3 charcoal = float3(.008,.0004,.0015)*body;
float3 blood = float3(.15,.0014,.006)*body*ink*ink;
float3 edge = float3(.42,.0035,.014)*swept*flow;
return float4((charcoal+blood+edge)*endFade*fade,
              saturate(body*flow*endFade*erode*fade*Opacity));
'''

TRAIL_SHADER = r'''
float n = pow(saturate((Noise-.0075)/(.5841-.0075)),.55);
float v = abs(UV.y-.5)*2;
float band = 1-smoothstep(.68,.99,v);
float razor = exp(-pow((UV.y-.73)/.095,2));
float thread = exp(-pow((UV.y-.27)/.05,2))*.25;
float tail = 1-smoothstep(.10,.97,UV.x);
float fade = pow(saturate(1-Age),.65)*tail;
float3 c = float3(.017,.0008,.0025)*band;
c += float3(.35,.0035,.012)*band*(.35+.65*n);
c += float3(1.65,.015,.045)*(razor+thread)*(.65+.35*n);
float alpha = max(band*.70,razor*.95)*fade;
return float4(c,alpha);
'''

SURROUNDINGS_SHADER = r'''
float2 radius = max(float2(FieldScreen.z,RadiusY),float2(.02,.03));
float d = length((UV-FieldScreen.xy)/radius);
// Broad feathering preserves a central event without a circular spotlight edge.
float focus = 1-smoothstep(.32,1.60,d);
focus = pow(saturate(focus),1.12);
float3 gain = lerp(float3(.15,.10,.12),float3(.87,.76,.79),focus);
return lerp(Scene.rgb,Scene.rgb*gain,saturate(Strength));
'''


def _hashes():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    rows = {}
    for asset in PROTECTED:
        package = content/(asset.removeprefix('/Game/')+'.uasset')
        if not package.is_file():
            raise RuntimeError('Inferno source package missing: '+str(package))
        rows[asset] = hashlib.sha256(package.read_bytes()).hexdigest()
    return rows


def _enum(enum_type, cpp_name):
    # Match the reflected member, rather than assuming a Python spelling from C++.
    target = cpp_name.replace('_','').lower()
    names = [name for name in dir(enum_type)
             if not name.startswith('_') and name.replace('_','').lower() == target]
    if len(names) != 1:
        raise RuntimeError('Unavailable reflected enum '+enum_type.__name__+'.'+cpp_name)
    return getattr(enum_type, names[0])


class _Graph:
    def __init__(self, material):
        self.material = material
        self.lib = unreal.MaterialEditingLibrary

    def node(self, kind, **properties):
        expression = self.lib.create_material_expression(
            self.material, getattr(unreal,'MaterialExpression'+kind))
        if expression is None:
            raise RuntimeError('Cannot create Inferno '+kind)
        for key, value in properties.items():
            expression.set_editor_property(key,value)
        return expression

    def wire(self, source, channel, target, pin):
        if not self.lib.connect_material_expressions(source,channel,target,pin):
            raise RuntimeError('Cannot connect Inferno '+target.get_name()+':'+pin)

    def custom(self, code, names, output):
        expression = self.node('Custom',code=code,output_type=output)
        pins = []
        for name in names:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name',name)
            pins.append(pin)
        expression.set_editor_property('inputs',pins)
        return expression

    def scalar(self, name, value):
        return self.node('ScalarParameter',parameter_name=name,default_value=value)

    def output(self, expression, prop, channels=None):
        if channels:
            mask = self.node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
            self.wire(expression,'',mask,'')
            expression = mask
        if not self.lib.connect_material_property(expression,'',prop):
            raise RuntimeError('Cannot connect Inferno property '+str(prop))

    def ink_samples(self, uv):
        samples = []
        for path, sx, sy in ((NOISE,.035,-.08),(INK,-.045,.025)):
            texture = unreal.load_asset(path)
            if texture is None:
                raise RuntimeError('Missing Inferno texture '+path)
            pan = self.node('Panner',speed_x=sx,speed_y=sy)
            sample = self.node('TextureSample',texture=texture)
            self.wire(uv,'',pan,'Coordinate')
            self.wire(pan,'',sample,'UVs')
            samples.append(sample)
        return samples


def _material(name, source=None):
    path = FOLDER+'/'+name
    material = unreal.load_asset(path)
    if material is not None:
        if not isinstance(material,unreal.Material):
            raise RuntimeError('Owned Inferno asset is not a Material: '+path)
        desired = '1' if name == 'M_CountessInfernoSurroundings' else VERSION
        current = unreal.EditorAssetLibrary.get_metadata_tag(material,META)
        if current == desired:
            return material,True
        if current != '1' or desired != '2':
            raise RuntimeError('Unreviewed existing Inferno material version: '+path)
        return material,False
    if source:
        material = unreal.EditorAssetLibrary.duplicate_asset(source,path)
    else:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name,FOLDER,unreal.Material,unreal.MaterialFactoryNew())
    if not isinstance(material,unreal.Material):
        raise RuntimeError('Cannot create private Inferno material '+path)
    return material,False


def _finish(material):
    errors = unreal.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError('Inferno material compile failed: '+repr(errors))
    desired = '1' if material.get_name() == 'M_CountessInfernoSurroundings' else VERSION
    unreal.EditorAssetLibrary.set_metadata_tag(material,META,desired)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material,False):
        raise RuntimeError('Cannot save private Inferno material '+material.get_path_name())


def _shadow():
    material,reused = _material('M_CountessInfernoShadow',SOURCE)
    if reused:
        return {'path':material.get_path_name(),'reused':True}
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    for prop,value in {'blend_mode':unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided':True,'used_with_skeletal_mesh':True,
                       'dither_opacity_mask':False}.items():
        material.set_editor_property(prop,value)
    graph = _Graph(material)
    relative = graph.node('Subtract')
    graph.wire(graph.node('WorldPosition'),'',relative,'A')
    graph.wire(graph.node('ObjectPositionWS'),'',relative,'B')
    uv = graph.custom('return float2(dot(Position,float3(.014,.006,.004)),dot(Position,float3(-.004,.010,.017)));',
                      ('Position',),unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    graph.wire(relative,'',uv,'Position')
    noise,ink = graph.ink_samples(uv)
    shader = graph.custom(SHADOW_SHADER,
        ('Noise','Ink','Facing','Energy','Clock','Start','Duration'),
        unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    for expression,output,pin in (
        (noise,'R','Noise'),(ink,'R','Ink'),
        (graph.node('Fresnel',exponent=1.0,base_reflect_fraction=.015),'','Facing'),
        (graph.scalar('InfernoEnergy',1.),'','Energy'),(graph.node('Time'),'','Clock'),
        (graph.scalar('DissolveStart',1000000.),'','Start'),
        (graph.scalar('DissolveDuration',.18),'','Duration')):
        graph.wire(expression,output,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False))
    graph.output(shader,unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))
    _finish(material)
    return {'path':material.get_path_name(),'reused':False,
            'source_alpha_WPO_preserved':False,'whole_face_glow':False,
            'alpha':'coherent continuous .90 body; broad texture-island erosion only during original retirement span',
            'source_package_unchanged':True,'pixel_dither':False}


def _blade():
    material,reused = _material('M_CountessInfernoBlade')
    if reused:
        return {'path':material.get_path_name(),'reused':True}
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    graph = _Graph(material)
    uv = graph.node('TextureCoordinate')
    noise,ink = graph.ink_samples(uv)
    shader = graph.custom(BLADE_SHADER,('UV','Noise','Ink','Phase','Opacity','Energy'),
                          unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    for expression,channel,pin in ((uv,'','UV'),(noise,'R','Noise'),(ink,'R','Ink'),
        (graph.scalar('CutPhase',.5),'','Phase'),(graph.scalar('CutOpacity',1.),'','Opacity'),
        (graph.scalar('CutEnergy',1.),'','Energy')):
        graph.wire(expression,channel,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False))
    graph.output(shader,unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))
    _finish(material)
    return {'path':material.get_path_name(),'reused':False,
            'shape':'existing measured dual weapon strips; narrow dark back/crimson razor, progressive tear',
            'white_flash':False,'continuous_alpha_floor':.70,'erosion_starts_at_phase':.80}


def _ink():
    material,reused = _material('M_CountessInfernoInk')
    if reused:
        return {'path':material.get_path_name(),'reused':True}
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    for prop,value in {'blend_mode':unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided':True,'dither_opacity_mask':False}.items():
        material.set_editor_property(prop,value)
    graph = _Graph(material)
    uv = graph.node('TextureCoordinate')
    noise,ink = graph.ink_samples(uv)
    shader = graph.custom(INK_SHADER,('UV','Noise','Ink','Shape','Seed','Fade','Opacity'),
                          unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    for expression,channel,pin in ((uv,'','UV'),(noise,'R','Noise'),(ink,'R','Ink'),
        (graph.scalar('Shape',4.),'','Shape'),(graph.scalar('Seed',0.),'','Seed'),
        (graph.scalar('Fade',1.),'','Fade'),(graph.scalar('Opacity',1.),'','Opacity')):
        graph.wire(expression,channel,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False))
    graph.output(shader,unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))
    _finish(material)
    return {'path':material.get_path_name(),'reused':False,'pixel_dither':False,
            'shape':'continuous charcoal wake and blood edge on native outer cards; no pepper/fleck mask'}


def _trail():
    material,reused = _material('M_CountessInfernoTrail')
    if reused:
        return material,{'path':material.get_path_name(),'reused':True}
    unreal.MaterialEditingLibrary.delete_all_material_expressions(material)
    for prop,value in {'blend_mode':unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model':unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided':True,'used_with_beam_trails':True,
                       'used_with_particle_sprites':True,'dither_opacity_mask':False}.items():
        material.set_editor_property(prop,value)
    graph = _Graph(material)
    uv = graph.node('TextureCoordinate')
    noise,_ = graph.ink_samples(uv)
    shader = graph.custom(TRAIL_SHADER,('UV','Noise','Age'),unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    for expression,channel,pin in ((uv,'','UV'),(noise,'R','Noise'),
                                   (graph.node('ParticleRelativeTime'),'','Age')):
        graph.wire(expression,channel,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False))
    graph.output(shader,unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))
    _finish(material)
    return material,{'path':material.get_path_name(),'reused':False,
                     'actual_animtrail_uv':True,'alpha':'continuous dark wake and crimson razor; particle lifetime fade'}


def _storm_strands():
    material,reused = _material('M_CountessInfernoStormStrands',WATER)
    if reused:
        return material,{'path':material.get_path_name(),'reused':True}
    graph = _Graph(material)
    alpha = graph.lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_OPACITY_MASK)
    alpha_output = graph.lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_OPACITY_MASK)
    if alpha is None:
        raise RuntimeError('Original water strand opacity mask missing')
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('dither_opacity_mask',False)
    opacity = graph.node('Multiply',const_b=.68)
    clamped = graph.node('Saturate')
    graph.wire(alpha,alpha_output,clamped,'')
    graph.wire(clamped,'',opacity,'A')
    graph.output(opacity,unreal.MaterialProperty.MP_OPACITY)
    emissive = graph.lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    emissive_output = graph.lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if emissive is not None:
        muted = graph.node('Multiply',const_b=.70)
        graph.wire(emissive,emissive_output,muted,'A')
        graph.output(muted,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    _finish(material)
    return material,{'path':material.get_path_name(),'reused':False,'source':WATER,
                     'original_texture_normal_ParticleColor_DP_graph_preserved':True,
                     'change':'dithered masked strands become continuous translucent source alpha *.68; emissive *.70'}


def _particle(name, source, strands=None, trail=None):
    path = FOLDER+'/'+name
    particle = unreal.load_asset(path)
    if particle is None:
        particle = unreal.EditorAssetLibrary.duplicate_asset(source,path)
    if not isinstance(particle,unreal.ParticleSystem):
        raise RuntimeError('Cannot duplicate private Inferno particle '+source)
    desired = '3' if trail is not None else VERSION
    if unreal.EditorAssetLibrary.get_metadata_tag(particle,META) == desired:
        return {'path':particle.get_path_name(),'reused':True}
    prefix = particle.get_path_name()+':'
    objects = [item for item in unreal.ObjectIterator(unreal.Object)
               if unreal.SystemLibrary.get_path_name(item).startswith(prefix)]
    changes,lifetimes,tessellation = [],[],[]
    for item in objects:
        kind = item.get_class().get_name()
        if kind == 'ParticleModuleRequired':
            old = item.get_editor_property('material')
            replace = trail is not None or (strands is not None and old and old.get_base_material().get_path_name().split('.')[0] == WATER)
            if replace:
                item.set_editor_property('material',trail if trail is not None else strands)
                changes.append({'module':item.get_path_name(),'property':'material','old':old.get_path_name() if old else None})
        elif kind == 'ParticleModuleMeshMaterial' and strands is not None:
            materials = list(item.get_editor_property('MeshMaterials'))
            changed = False
            for index,old in enumerate(materials):
                if old and old.get_base_material().get_path_name().split('.')[0] == WATER:
                    materials[index] = strands
                    changed = True
                    changes.append({'module':item.get_path_name(),'property':'mesh_materials','slot':index,'old':old.get_path_name()})
            if changed:
                item.set_editor_property('MeshMaterials',materials)
        elif kind == 'ParticleModuleLifetime' and trail is not None:
            distribution = item.get_editor_property('lifetime').get_editor_property('distribution')
            if distribution is None or not distribution.get_path_name().startswith(prefix):
                raise RuntimeError('Trail lifetime distribution is not privately owned')
            distribution_kind = distribution.get_class().get_name()
            if distribution_kind == 'DistributionFloatConstant':
                distribution.set_editor_property('constant',.12)
            elif distribution_kind == 'DistributionFloatUniform':
                distribution.set_editor_property('min',.12)
                distribution.set_editor_property('max',.12)
            else:
                raise RuntimeError('Unreviewed trail lifetime '+distribution_kind)
            lifetimes.append(distribution.get_path_name())
        elif kind == 'ParticleModuleTypeDataAnimTrail' and trail is not None:
            # The original E-only copy deliberately disabled all spline tessellation.
            # Fast rotating A/V shadows need their actual sampled weapon path interpolated.
            values = {'bEnablePreviousTangentRecalculation':True,
                      'bTangentRecalculationEveryFrame':False,
                      'DistanceTessellationStepSize':12.,
                      'TangentTessellationStepSize':10.,
                      'WidthTessellationStepSize':8.}
            for prop,value in values.items():
                item.set_editor_property(prop,value)
            tessellation.append({'module':unreal.SystemLibrary.get_path_name(item),
                                 'properties':values})
    if trail is not None and (not changes or not lifetimes):
        raise RuntimeError('Private AnimTrail material/lifetime adaptation did not apply')
    if trail is not None and not tessellation:
        raise RuntimeError('No private AnimTrail type data was interpolated')
    if strands is not None and not changes:
        raise RuntimeError('No referenced masked strand material was replaced in '+path)
    # No spawn, location, velocity, color, dynamic parameters or emitter budgets change.
    unreal.EditorAssetLibrary.set_metadata_tag(particle,META,desired)
    if not unreal.EditorAssetLibrary.save_loaded_asset(particle,False):
        raise RuntimeError('Cannot save private Inferno particle '+path)
    return {'path':particle.get_path_name(),'source':source,'reused':False,
            'material_changes':changes,'private_trail_lifetimes':lifetimes,
            'actual_socket_path_tessellation':tessellation,
            'emission_motion_counts_unchanged':True,'source_saved':False,
            'copy_contract':'EditorAssetLibrary.duplicate_asset copies complete template; only private-prefix required/mesh-material, trail lifetime and trail tessellation subobjects edited',
            'subobject_prefix':prefix,
            'native_binding':'CountessInfernoVisual loads this complete private template before PSC registration/activation',
            'actual_renderer_material_confirmation':'root quality-fx A/V render_emitters receipt pending'}


def _curve_uv(output):
    mesh = unreal.load_asset('/Game/TopDown/Characters/Countess/FX/SM_CountessQDualSweep')
    destination = output/'inferno-uv-audit-temporary.obj'
    task = unreal.AssetExportTask()
    for prop,value in {'object':mesh,'exporter':unreal.StaticMeshExporterOBJ(),'filename':str(destination),
                       'selected':False,'replace_identical':True,'prompt':False,'automated':True,
                       'write_empty_files':False}.items():
        task.set_editor_property(prop,value)
    try:
        if not unreal.Exporter.run_asset_export_task(task):
            raise RuntimeError('Could not read actual Inferno curved mesh UVs')
        rows = [tuple(float(x) for x in line.split()[1:3])
                for line in destination.read_text(encoding='utf-8-sig',errors='replace').splitlines()
                if line.startswith('vt ')]
        if not rows:
            raise RuntimeError('Actual curved mesh has no exported UVs')
        bounds = [[min(row[i] for row in rows),max(row[i] for row in rows)] for i in (0,1)]
        covered = all(lo >= -.001 and hi <= 1.001 for lo,hi in bounds)
        if not covered:
            raise RuntimeError('Actual curved mesh UVs are outside reviewed shader domain: '+repr(bounds))
        return {'uv_count':len(rows),'ranges':bounds,'shader_domain_0_1_compatible':covered,
                'temporary_export_removed':True}
    finally:
        if destination.is_file():
            destination.unlink()


def _surroundings():
    material,reused = _material('M_CountessInfernoSurroundings')
    if reused:
        return {'path':material.get_path_name(),'reused':True}
    material.set_editor_property('material_domain',_enum(unreal.MaterialDomain,'MD_PostProcess'))
    material.set_editor_property('blendable_location',
                                _enum(unreal.BlendableLocation,'BL_SceneColorAfterTonemapping'))
    material.set_editor_property('blendable_priority',22)
    graph = _Graph(material)
    scene = graph.node('SceneTexture',scene_texture_id=_enum(unreal.SceneTextureId,'PPI_PostProcessInput0'))
    screen = graph.node('ScreenPosition')
    center = graph.node('VectorParameter',parameter_name='FieldScreen',
                        default_value=unreal.LinearColor(.5,.43,.20,.24))
    shader = graph.custom(SURROUNDINGS_SHADER,('Scene','UV','FieldScreen','RadiusY','Strength'),
                          unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    for expression,channel,pin in ((scene,'','Scene'),(screen,'ViewportUV','UV'),
        (center,'RGB','FieldScreen'),(graph.scalar('FieldRadiusY',.24),'','RadiusY'),
        (graph.scalar('SurroundingsStrength',0.),'','Strength')):
        graph.wire(expression,channel,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    _finish(material)
    return {'path':material.get_path_name(),'reused':False,
            'location':'SceneColorAfterTonemapping; full composite including existing translucent V',
            'center':'native per-frame viewport projection, camera lag included',
            'feather_radii':[.32,1.60],'default_strength':0.,
            'native_ColorGain_override_disabled_when_loaded':True}


def author(output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    before = _hashes()
    pp_package = Path(unreal.Paths.project_content_dir())/(FOLDER.removeprefix('/Game/')+'/M_CountessInfernoSurroundings.uasset')
    pp_before = hashlib.sha256(pp_package.read_bytes()).hexdigest() if pp_package.is_file() else None
    rows = [_shadow(),_ink(),_surroundings()]
    trail,trail_row = _trail()
    strands,strand_row = _storm_strands()
    rows.extend((trail_row,strand_row))
    particles = [
        _particle('P_CountessInfernoSwordTrail',PROTECTED[4],trail=trail),
        _particle('P_CountessInfernoVeil',PROTECTED[5],strands=strands),
        _particle('P_CountessInfernoSpiral',PROTECTED[6],strands=strands)]
    after = _hashes()
    if before != after:
        raise RuntimeError('An original Countess/pack source package changed')
    pp_unchanged = pp_before is None or pp_before == hashlib.sha256(pp_package.read_bytes()).hexdigest()
    if not pp_unchanged:
        raise RuntimeError('Accepted V center postprocess package changed')
    result = {'passed':True,'version':VERSION,'review_revision':3,'materials':rows,'particles':particles,
              'supplemental_Q_curve_removed':True,'rendered_cut_geometry':'actual primary-attack weapon socket AnimTrail only',
              'saved_folder':FOLDER,'source_hashes_unchanged':True,'source_hashes':after,
              'accepted_center_postprocess_hash_unchanged':pp_unchanged,
              'pack_assets_saved':False,'native_gameplay_changed':False,
              'visual_acceptance':'actual A/V capture pending; asset compilation is not aesthetic approval'}
    (output/'countess-inferno-surface.json').write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
