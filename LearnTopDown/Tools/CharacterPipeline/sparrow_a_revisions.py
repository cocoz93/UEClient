"""Actual A projectile presentations, with production gameplay untouched.

Authors one isolated preview material. Actual native gear arrows supply motion,
160cm/s, 90 damage and the existing repeated contact accents. All component
overrides are restored. Source packs and production materials are never saved.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_PART = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PART['Study'], _PART['_valid']
FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/ARevisions20261023'
MATERIAL = FOLDER + '/M_SparrowARevisions'
AURA = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltArrow'
AURA_NAMES = ('RibbonTrail', 'DebugRibbon', 'TrailsLinger', 'Flare_Big', 'Flare', 'Sparks',
              'SparksTrailing', 'Refraction', 'Particle Emitter', 'MeshCoronaLarge', 'AirglowFlash', 'Airglow')
OPTIONS = ('A6', 'A7', 'A8', 'A9')
DESIGNS = {
    'A6': {'label': '금속 광륜톱', 'description': '열두 개의 넓은 금속 날과 안쪽 절삭살, 작은 허브가 회전하는 밀도 높은 황금 톱날'},
    'A7': {'label': '교차 절삭날', 'description': '네 갈래의 길고 가는 칼날이 교차해 회전하며, 뒤꼬리는 짧게 압축'},
    'A8': {'label': '액체 황금 분쇄핵', 'description': '원본 금빛 Aura 메시와 내부 흐름을 본체로 쓰고, 뒤로 찢어진 짧은 화염편을 남기는 느린 분쇄탄'},
    'A9': {'label': '금속톱 + 황금 불꽃핵', 'description': 'A6의 금속 회전톱 외곽 안에 작은 액체 황금 핵을 담고, 짧게 찢긴 불꽃 꼬리를 남기는 혼합형'},
}


def _write(out, name, result):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


def _selected():
    result = [item.strip() for item in os.environ.get('SPARROW_A_REVISION_OPTIONS', ','.join(OPTIONS)).split(',') if item.strip()]
    assert result and all(item in OPTIONS for item in result), result
    return result


def author(out):
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(MATERIAL)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            MATERIAL.rsplit('/', 1)[1], FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    for field, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                         'shading_model': unreal.MaterialShadingModel.MSM_UNLIT, 'two_sided': True}.items():
        material.set_editor_property(field, value)
    def node(kind, **values):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for field, value in values.items():
            item.set_editor_property(field, value)
        return item
    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float2 p = (UV-.5)*2.;
float r = length(p);
float a = atan2(p.y,p.x);
float mask = 0.;
float sharp = 0.;
float facet = 0.;
float bevel = 0.;
float metal = .65+.35*cos(a*2.-Clock*1.8+r*11.);
if(Style<.5){
    float sector = frac(a/6.2831853*12.+r*.18);
    float tooth = smoothstep(.035,.14,sector)*(1.-smoothstep(.72,.90,sector));
    float reach = .73+.19*(1.-sector);
    float blades = tooth*smoothstep(.34,.42,r)*(1.-smoothstep(reach-.025,reach,r));
    float web = (1.-smoothstep(.07,.105,abs(r-.51)))*(.32+.68*tooth);
    float spokes = pow(abs(cos(a*6.)),14.)*smoothstep(.16,.21,r)*(1.-smoothstep(.47,.55,r));
    float hub = 1.-smoothstep(.014,.036,abs(r-.125));
    mask = saturate(blades+web+spokes*.85+hub*.75);
    sharp = tooth*(1.-smoothstep(.009,.032,abs(r-reach)))+hub*.38;
    facet = smoothstep(.16,.70,sector)*(.30+.70*smoothstep(.38,.85,r));
    bevel = tooth*(1.-smoothstep(.025,.080,abs(r-reach)))+spokes*.28;
}else{
    float ax=abs(p.x), ay=abs(p.y);
    float wx=.13*(1.-smoothstep(.50,.91,ax))+.012;
    float wy=.13*(1.-smoothstep(.50,.91,ay))+.012;
    float bx=(1.-smoothstep(wx-.015,wx+.012,ay))*smoothstep(.13,.20,ax)*(1.-smoothstep(.86,.94,ax));
    float by=(1.-smoothstep(wy-.015,wy+.012,ax))*smoothstep(.13,.20,ay)*(1.-smoothstep(.86,.94,ay));
    float hub=1.-smoothstep(.014,.035,abs(r-.12));
    mask=saturate(bx+by+hub*.7);
    sharp=bx*(1.-smoothstep(.010,.035,abs(ay-wx*.70)))+by*(1.-smoothstep(.010,.035,abs(ax-wy*.70)));
    facet=saturate(bx*(.5+.5*p.y/max(wx,.02))+by*(.5-.5*p.x/max(wy,.02)));
    bevel=bx*smoothstep(.50,.92,ay/max(wx,.02))+by*smoothstep(.50,.92,ax/max(wy,.02));
}
float grain=.88+.12*sin(r*117.+sin(a*17.)*2.);
float3 bronze=lerp(float3(.12,.044,.008),float3(.55,.26,.035),saturate(facet))*(.78+.22*metal)*grain;
float3 goldEdge=float3(1.20,.66,.11)*saturate(bevel)*.65;
float3 razor=float3(2.8,2.55,1.9)*saturate(sharp);
float3 surface = bronze+goldEdge+razor;
float kernel = (1.-smoothstep(.22,.29,r))*Hybrid;
float2 moltenUV = p*2.7 + sin(p.yx*5.+Clock)*.13 - float2(Clock*.13,Clock*.58);
float fireA = Texture2DSample(Fire,FireSampler,moltenUV).r;
float fireB = Texture2DSample(Fire,FireSampler,moltenUV*1.6+float2(.3,Clock*.18)).g;
float heat = smoothstep(.12,.82,saturate(fireA*.7+fireB*.4));
float sphereDepth = sqrt(saturate(1.-r*r/(.29*.29)));
float3 fluid = lerp(float3(.22,.038,.002),float3(2.6,1.22,.055),heat)*(.38+.62*sphereDepth);
fluid += float3(4.2,3.0,.65)*pow(smoothstep(.68,.96,heat),2.)*.34;
surface = lerp(surface,fluid,kernel);
mask = max(mask,kernel*(.70+.28*heat));
return float4(surface*Strength,saturate(mask*Strength));
''')
    inputs = []
    for name in ('UV', 'Style', 'Strength', 'Clock', 'Hybrid', 'Fire'):
        item = unreal.CustomInput(); item.set_editor_property('input_name', name); inputs.append(item)
    shader.set_editor_property('inputs', inputs)
    for source, target in ((node('TextureCoordinate'), 'UV'),
                           (node('ScalarParameter', parameter_name='Style', default_value=0.), 'Style'),
                           (node('ScalarParameter', parameter_name='Strength', default_value=1.), 'Strength'),
                           (node('Time'), 'Clock'),
                           (node('ScalarParameter', parameter_name='Hybrid', default_value=0.), 'Hybrid'),
                           (node('TextureObject', texture=unreal.load_asset('/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D')), 'Fire')):
        assert lib.connect_material_expressions(source, '', shader, target)
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        assert lib.connect_material_expressions(shader, '', mask, '')
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    assert isinstance(unreal.load_asset(AURA), unreal.ParticleSystem)
    report = {'passed': True, 'preview_material_saved': MATERIAL, 'material_count': 1,
              'source_assets_saved': False, 'production_A_changed': False, 'options': DESIGNS}
    _write(out, 'A-revisions-author.json', report)
    return report


class Study(ParticleStudy):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.arrow_actor = None
        self.static_rows, self.particle_rows = [], []
        self.next_emit = 0.
        self.next_core = 0.
        self.core_rows = []
        self.last_hit = -99.
        self.source = unreal.load_asset(AURA)

    def arrow(self, arrow):
        self.arrow_actor = arrow
        for component in arrow.get_components_by_class(unreal.StaticMeshComponent):
            if not component.get_name().startswith('FeatherRing'):
                continue
            self.static_rows.append((component, component.is_visible(),
                                     component.get_editor_property('relative_scale3d'), component.get_material(0)))
            index = int(component.get_name()[-1])
            if self.option == 'A8' or (self.option == 'A7' and index == 1):
                component.set_visibility(False)
                continue
            material = unreal.MaterialLibrary.create_dynamic_material_instance(self.rig['world'](), unreal.load_asset(MATERIAL))
            material.set_scalar_parameter_value('Style', 0. if self.option in ('A6', 'A9') else 1.)
            material.set_scalar_parameter_value('Strength', 1. if index == 0 else .68)
            material.set_scalar_parameter_value('Hybrid', 1. if self.option == 'A9' and index == 0 else 0.)
            component.set_material(0, material)
            size = 1.75 if index == 0 else 1.15
            component.set_relative_scale3d(unreal.Vector(size, size if self.option in ('A6', 'A9') else size*.83, 1.))
            self.mids.append(material)
        for component in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            if component.get_name() not in ('CondensedCore', 'ArrowTrail'):
                continue
            self.particle_rows.append({'component': component, 'visible': component.is_visible(),
                'scale': component.get_editor_property('relative_scale3d'),
                'speed': component.get_editor_property('custom_time_dilation'),
                'template': component.get_editor_property('template'),
                'materials': [component.get_material(i) for i in range(component.get_num_materials())]})
            if component.get_name() == 'CondensedCore':
                if self.option != 'A8':
                    component.set_visibility(False)
                else:
                    component.set_template(self.source)
                    component.set_relative_scale3d(unreal.Vector(1.20, 2.0, 2.0))
                    component.activate(True)
                    for name in AURA_NAMES:
                        component.set_emitter_enable(name, name in ('MeshCoronaLarge', 'SparksTrailing'))
                    self.next_core = self.now() + .30
            elif self.option != 'A8':
                component.set_relative_scale3d(unreal.Vector(.25, .35, .35) if self.option == 'A7' else unreal.Vector(.35, .45, .45))
                component.set_editor_property('custom_time_dilation', 1.6 if self.option == 'A7' else 1.3)

    def core(self, arrow):
        # Rebirth retains the original Aura material and its particle DynamicParameter chain.
        # Its .55s lifetime overlaps the .30s cadence: at most two temporary cores coexist.
        direction = arrow.get_flight_direction()
        # A9 keeps the small fluid center inside the unchanged A6 cutting silhouette.
        offset = 55. if self.option == 'A9' else 35.
        scale = (.90, 1.20, 1.20) if self.option == 'A9' else (1.20, 2.0, 2.0)
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.source, arrow.get_actor_location()+direction*offset,
            unreal.MathLibrary.make_rot_from_x(direction), unreal.Vector(*scale),
            False, unreal.PSCPoolMethod.NONE, False)
        assert particle, self.option + ' original Aura core'
        deadline = self.now() + .55
        self.effects.append((particle, deadline))
        self.core_rows.append((particle, deadline))
        self.created += 1
        particle.set_editor_property('component_tags', [unreal.Name('SparrowARevisionCore')])
        # The authored aura mesh is disabled in LOD1-3; these preview cores
        # must follow the native arrow's explicit LOD0 presentation.
        direct = next(getattr(unreal.ParticleSystemLODMethod, name)
                      for name in dir(unreal.ParticleSystemLODMethod) if 'DIRECT' in name.upper())
        particle.set_editor_property('override_lod_method', True)
        particle.set_editor_property('lod_method', direct)
        particle.activate(True)
        for name in AURA_NAMES:
            particle.set_emitter_enable(name, name == 'MeshCoronaLarge')

    def update(self):
        now = self.now()
        boost = 1. + .28 * max(0., 1. - (now-self.last_hit)/.14)
        for index, material in enumerate(self.mids):
            material.set_scalar_parameter_value('Strength', boost * (1. if index == 0 else .68))
        arrow = self.arrow_actor
        if self.option == 'A8' and _valid(arrow):
            direction = arrow.get_flight_direction()
            if now >= self.next_core:
                self.next_core = now + .30
                self.core(arrow)
            self.core_rows = [(particle, deadline) for particle, deadline in self.core_rows
                              if _valid(particle) and now < deadline]
            offset = 55. if self.option == 'A9' else 35.
            for particle, _ in self.core_rows:
                particle.set_world_location(arrow.get_actor_location()+direction*offset, False, False)
                particle.set_world_rotation(unreal.MathLibrary.make_rot_from_x(direction), False, False)
        if self.option in ('A8', 'A9') and _valid(arrow) and now >= self.next_emit:
            hybrid = self.option == 'A9'
            self.next_emit = now + (.16 if hybrid else .14)
            direction = arrow.get_flight_direction()
            self.pulse('shards', ('Flames2',), arrow.get_actor_location()-direction*(34. if hybrid else 52.),
                       unreal.MathLibrary.make_rot_from_z(direction*-1.),
                       (.22,.14,.32) if hybrid else (.24,.16,.38), .20 if hybrid else .24, 2.2)
        self.tick()

    def close(self):
        failures, restored = [], 0
        for component, visible, scale, material in self.static_rows:
            if _valid(component):
                component.set_visibility(visible); component.set_relative_scale3d(scale); component.set_material(0, material)
                if component.get_material(0) != material or component.is_visible() != visible:
                    failures.append(component.get_path_name())
                restored += 1
        for row in self.particle_rows:
            component = row['component']
            if _valid(component):
                component.set_template(row['template']); component.set_relative_scale3d(row['scale'])
                component.set_editor_property('custom_time_dilation', row['speed'])
                for index, material in enumerate(row['materials']):
                    component.set_material(index, material)
                component.set_visibility(row['visible'])
                if component.get_editor_property('template') != row['template']:
                    failures.append(component.get_path_name())
                restored += 1
        super().close()
        self.core_rows.clear()
        return restored, failures


def sequence(rig):
    rows = []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in _selected():
        rig['switch']('countess'); yield .10
        rig['switch']('sparrow'); yield .55
        rig['case']('A_revision_' + option)
        targets = rig['layout']([(470,0), (800,350), (800,-350)])
        yield .20
        initial = previous = rig['health'](targets[0])
        study, seen, hits, samples = Study(rig, option), set(), [], []
        started = now()
        try:
            rig['use']('A', targets[0])
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': option, 'prefix': option+'_video', 'cast_time': started, 'frame_times': []}
            moments = [.75,1.25,2.1]
            while now()-started < 3.6:
                elapsed = now()-started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowGearArrow):
                    path = arrow.get_path_name()
                    if arrow.get_owner() == rig['pawn']() and path not in seen:
                        seen.add(path); study.arrow(arrow)
                        samples.append({'speed': arrow.get_flight_speed(), 'piercing': arrow.is_piercing()})
                health = rig['health'](targets[0])
                if health < previous-.01:
                    hits.append({'elapsed': elapsed, 'damage': previous-health}); study.last_hit = now()
                previous = health; study.update()
                if moments and elapsed >= moments[0]:
                    rig['capture'](option+'_at_'+str(round(moments.pop(0)*100)))
                yield 1/rig['FPS']
            rig['finish_video_clip'](); rig['recovered']()
            actual = initial-rig['health'](targets[0])
            rig['check'](len(seen)==1, option+' observes one actual native A projectile')
            rig['check'](samples and all(abs(s['speed']-160.)<.1 and s['piercing'] for s in samples), option+' uses 160 speed and preserves piercing')
            rig['check'](abs(actual-90.)<.03, option+' preserves 90 native damage')
            row={'id':option, **DESIGNS[option], 'actual_damage':actual, 'hits':hits,
                 'native_projectiles':len(seen), 'samples':samples, 'temporary_PSCs_created':study.created,
                 'native_three_contact_accents_unchanged':True, 'production_installed':False}
        finally:
            rig['finish_video_clip'](); restored, failures = study.close()
        rig['check'](not failures and not study.effects, option+' restores original appearance and removes temporary effects')
        row['restored_components']=restored; row['restoration_failures']=failures
        rows.append(row)
        yield .15
    _write(rig['OUT'], 'A-revisions-studies.json', {'passed':True,'studies':rows,
        'source_assets_saved_in_PIE':False,'production_A_changed':False,'visual_review':'pending actual selected-clip review'})
