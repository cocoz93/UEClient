"""Directional E4-E6 / W1-W3 studies on actual native casts, never an install.

author(out) saves only this module's six preview materials. sequence(rig) hides
the live cast's overlapping muzzle/ring/arrow presentation, preserves its mesh,
animation, six E shots / single W shot and damage, then restores surviving
components. Native particle shards add moving texture behind the designed shape.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal

_PARTICLE_HELPER = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PARTICLE_HELPER['Study'], _PARTICLE_HELPER['_valid']


FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/EWDirection20261022'
OPTIONS = ('E4', 'E5', 'E6', 'W1', 'W2', 'W3')
DESIGNS = {
    'E4': {'label': '접힌 날개 연사', 'description': '활 양옆의 날개가 뒤로 접히며 화살에 좁은 깃날을 남김'},
    'E5': {'label': '이중 나선 연사', 'description': '백금 중심과 두 금빛 나선이 서로 엇갈려 화살의 부피를 만듦'},
    'E6': {'label': '백금 파편 연사', 'description': '중심 촉 주위의 작은 결정 조각이 발사와 명중에서 부서지는 방향'},
    'W1': {'label': '응축된 성창', 'description': '길고 단단한 창끝으로 압축한 뒤 접힌 금빛 깃날을 남기는 단발'},
    'W2': {'label': '쌍날 관통', 'description': '두 칼날이 모였다가 화살 좌우를 감싸며 터지는 단발'},
    'W3': {'label': '삼지 탄두', 'description': '세 갈래 촉과 짧은 추진 파편으로 무겁게 밀어내는 단발'},
}


def formulas():
    # X is the direction of travel; all candidates have an open rear, no floor
    # fill and no surrounding circle. Role: 0=muzzle, 1=flight, 2=impact.
    common = '''float x=UV.x; float y=UV.y-.5; float ay=abs(y);
float gate=smoothstep(.015,.08,x)*(1.-smoothstep(.92,.985,x));
float m=0.; float white=0.; float gl=0.;
'''
    end = '''
float strength=max(0.,Strength);
float3 gold=float3(3.2,2.05,.42); float3 platinum=float3(3.4,3.05,2.25);
float mask=saturate(m+white*.85+gl*.12)*strength;
return float4((gold*m+platinum*white+gold*gl*.12)*strength,saturate(mask*.92));'''
    body = {
        'E4': '''
if(Role<.5){
  float fan=.10+.26*(1.-x)*(1.-Age*.48);
  float wing=pow(saturate(1.-abs(ay-fan)*32.),1.5);
  float secondary=pow(saturate(1.-abs(ay-fan*.62)*53.),1.4);
  float comb=saturate(.28+.72*sin((x+ay*.8)*56.));
  m=(wing*.8+secondary*.6)*comb*gate;
  white=pow(saturate(1.-abs(ay-fan)*110.),1.5)*gate*.65;
}else if(Role<1.5){
  float spine=pow(saturate(1.-ay/(.008+.025*(1.-x))),1.4);
  float leafWidth=.055+.13*(1.-x);
  float feathers=pow(saturate(1.-abs(ay-leafWidth)*38.),1.5);
  float featherGate=pow(saturate(sin((x+ay*1.9)*25.)),1.7);
  m=(feathers*featherGate+spine*.25)*gate;
  white=(spine*.55+pow(saturate(1.-abs(x-.84)*12.-ay*28.),1.4))*gate;
}else{
  float flare=pow(saturate(1.-abs(x-.5)*18.-ay*3.8),1.7);
  float slash=pow(saturate(1.-abs(ay-(.04+.32*Age))*40.),1.6)*pow(saturate(1.-abs(x-.5)*3.),2.);
  m=slash;white=flare;
}''',
        'E5': '''
if(Role<.5){
  float bend=.03+.30*pow(1.-x,1.55);
  m=pow(saturate(1.-abs(ay-bend)*54.),1.7)*gate;
  white=pow(saturate(1.-ay*90.),1.6)*gate*.55;
}else if(Role<1.5){
  float helix=.10*sin(x*15.-Age*14.);
  float rail=pow(saturate(1.-abs(y-helix)*67.),1.55);
  float rail2=pow(saturate(1.-abs(y+helix)*67.),1.55);
  float depth=.35+.65*saturate(cos(x*15.-Age*14.));
  m=(rail*depth+rail2*(1.35-depth))*gate;
  white=pow(saturate(1.-ay*95.),1.4)*gate*.85;
  gl=pow(saturate(1.-ay*7.),3.)*gate*.3;
}else{
  float bent=.10+.20*Age;
  m=pow(saturate(1.-abs(ay-bent)*46.),1.5)*pow(saturate(1.-abs(x-.5)*3.),1.5);
  white=pow(saturate(1.-abs(x-.5)*20.-ay*10.),1.5);
}''',
        'E6': '''
if(Role<.5){
  float swept=.04+.30*(1.-x);
  float shards=pow(saturate(1.-abs(ay-swept)*28.),1.6)*pow(saturate(sin(x*37.)),2.);
  m=shards*gate;white=pow(saturate(1.-abs(x-.75)*10.-ay*16.),2.);
}else if(Role<1.5){
  float tip=pow(saturate(1.-abs(x-.76)*5.8-ay*11.),1.15);
  float f1=pow(saturate(1.-abs(x-.46)*12.-abs(ay-.10)*31.),1.5);
  float f2=pow(saturate(1.-abs(x-.24)*16.-abs(ay-.19)*36.),1.6);
  float spineMask=pow(saturate(1.-ay*92.),2.)*smoothstep(.1,.25,x)*(1.-smoothstep(.7,.85,x));
  m=f1*.9+f2*.65;white=tip*.85+spineMask*.6;
}else{
  float2 q=float2((x-.5)*1.25,y);float a=atan2(q.y,q.x);float r=length(q);
  float shard=pow(saturate(1.-abs(frac(a/6.283185*7.+.17)-.5)*14.),1.5);
  float envelope=pow(saturate(1.-abs(r-(.07+.26*Age))/.10),1.5);
  m=shard*envelope;white=pow(saturate(1.-r*16.),2.);
}''',
        'W1': '''
if(Role<.5){
  float spread=.08+.30*(1.-Age)*(1.-x);
  float wings=pow(saturate(1.-abs(ay-spread)*44.),1.5)*gate;
  float inner=pow(saturate(1.-abs(ay-spread*.58)*74.),1.5)*gate;
  m=wings+inner*.55;white=pow(saturate(1.-ay*85.),1.4)*gate*.65;
}else if(Role<1.5){
  float tip=pow(saturate(1.-abs(x-.80)*5.-ay*10.),1.35);
  float shaft=pow(saturate(1.-ay/(.005+.021*(1.-x))),1.45)*gate;
  float fins=pow(saturate(1.-abs(ay-(.035+.14*(1.-x)))*56.),1.5)*gate;
  m=fins*.8+shaft*.3;white=shaft*.7+tip*.7;
}else{
  float shaft=pow(saturate(1.-ay*78.),1.4)*gate;
  float breakLine=pow(saturate(1.-abs(x-.47)*90.),1.5)*pow(saturate(1.-ay*3.),2.);
  m=breakLine;white=shaft*.7;
}''',
        'W2': '''
if(Role<.5){
  float curve=.05+.30*sin(x*3.141593)*(1.-Age*.65);
  float blade=pow(saturate(1.-abs(ay-curve)/(.014+.025*(1.-x))),1.25);
  float notch=saturate(.5+.5*sin(x*32.+ay*12.));
  m=blade*gate;white=blade*notch*.7*gate;
}else if(Role<1.5){
  float curve=.018+.20*sin(x*3.141593);
  float blade=pow(saturate(1.-abs(ay-curve)/(.008+.035*sin(x*3.141593))),1.25);
  float inner=pow(saturate(1.-abs(ay-curve*.65)*85.),1.5);
  m=(blade+inner*.4)*gate;white=pow(saturate(1.-ay*100.),2.)*gate*.45+blade*.35;
}else{
  float slant=abs(y-(x-.5)*.70);
  float slash=pow(saturate(1.-slant*70.),1.4)*gate;
  float slash2=pow(saturate(1.-abs(y+(x-.5)*.70)*70.),1.4)*gate;
  m=slash2*.85;white=slash*.9;
}''',
        'W3': '''
if(Role<.5){
  float fan=.045+.35*(1.-x)*(1.-Age*.4);
  float pieces=pow(saturate(1.-abs(ay-fan)*29.),1.4)*pow(saturate(sin(x*29.)),1.8);
  m=pieces*gate;white=pow(saturate(1.-ay*100.),1.5)*gate*.6;
}else if(Role<1.5){
  float middle=pow(saturate(1.-abs(x-.77)*5.5-ay*12.),1.15);
  float side=pow(saturate(1.-abs(x-.56)*7.-abs(ay-.15)*22.),1.2);
  float fletch=pow(saturate(1.-abs(x-.24)*17.-abs(ay-.22)*32.),1.3);
  float wake=pow(saturate(1.-abs(ay-(.03+.27*(1.-x)))*82.),1.7)*gate;
  m=side*.85+fletch*.6+wake*.5;white=middle*.8;
}else{
  float p1=pow(saturate(1.-abs(x-.50)*18.-ay*4.),1.4);
  float p2=pow(saturate(1.-abs(x-.35)*24.-abs(ay-.19)*20.),1.5);
  float p3=pow(saturate(1.-abs(x-.67)*23.-abs(ay-.12)*22.),1.5);
  m=p2+p3*.8;white=p1*.8;
}''',
    }
    return {key: common + value + end for key, value in body.items()}


def author(out):
    """Only dedicated preview assets are saved; never a source PS/material."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    saved = []
    selected = {x.strip() for x in os.environ.get('SPARROW_EW_OPTIONS', ','.join(OPTIONS)).split(',') if x.strip()}
    assert selected and selected.issubset(OPTIONS), sorted(selected)
    for option, code in formulas().items():
        if option not in selected:
            continue
        name = 'M_' + option + '_DirectionalStudy'
        path = FOLDER + '/' + name
        mat = unreal.load_asset(path)
        if mat is None:
            mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        assert mat, path
        lib.delete_all_material_expressions(mat)
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided', True)
        custom = lib.create_material_expression(mat, unreal.MaterialExpressionCustom)
        custom.set_editor_property('code', code)
        custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        inputs = []
        for key in ('UV', 'Age', 'Role', 'Strength'):
            item = unreal.CustomInput()
            item.set_editor_property('input_name', key)
            inputs.append(item)
        custom.set_editor_property('inputs', inputs)
        uv = lib.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate)
        assert lib.connect_material_expressions(uv, '', custom, 'UV')
        for key, value in (('Age', 0.), ('Role', 0.), ('Strength', 1.)):
            scalar = lib.create_material_expression(mat, unreal.MaterialExpressionScalarParameter)
            scalar.set_editor_property('parameter_name', key)
            scalar.set_editor_property('default_value', value)
            assert lib.connect_material_expressions(scalar, '', custom, key)
        for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
            mask = lib.create_material_expression(mat, unreal.MaterialExpressionComponentMask)
            for key, enabled in zip(('r','g','b','a'), channels):
                mask.set_editor_property(key, enabled)
            assert lib.connect_material_expressions(custom, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(mat)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
        saved.append(path)
    result = {'passed': True, 'saved_preview_materials': saved, 'designs': DESIGNS,
              'production_defaults_changed': False, 'source_pack_assets_saved': False}
    (out / 'EW-direction-author.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


class Study(ParticleStudy):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.planes, self.hidden, self.arrow_records = [], {}, []
        self.preserved_arrow_components = set()
        self.serial, self.latest_shot, self.first_shot = 0, None, None
        self.mat = unreal.load_asset(FOLDER + '/M_' + option + '_DirectionalStudy')
        assert self.mat, option
        self.rotation = rig['pawn']().get_actor_rotation()
        self.rotation.pitch, self.rotation.roll = 0., 0.
        self.forward = rig['pawn']().get_actor_forward_vector()
        self.muzzle = self.plane(0, rig['skills']().get_arrow_origin(), (1., 1., 1.))

    def plane(self, role, position, scale):
        self.serial += 1
        name = 'SparrowEWStudy_' + self.option + '_' + str(self.serial)
        self.rig['cmd'](f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {position.x} {position.y} {position.z}')
        actor = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.StaticMeshActor)
                      if a.get_name() == name), None)
        assert actor, name
        actor.set_actor_enable_collision(False)
        actor.set_life_span(3.)
        actor.set_editor_property('tags', [unreal.Name('SparrowEWStudy')])
        mesh = actor.get_editor_property('static_mesh_component')
        mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        mesh.set_editor_property('generate_overlap_events', False)
        mesh.set_editor_property('can_ever_affect_navigation', False)
        mesh.set_editor_property('cast_shadow', False)
        mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        mesh.set_world_scale3d(unreal.Vector(*scale))
        actor.set_actor_rotation(self.rotation, True)
        mid = mesh.create_dynamic_material_instance(0, self.mat)
        assert mid, self.option
        mid.set_scalar_parameter_value('Role', role)
        mid.set_scalar_parameter_value('Strength', 0.)
        row = {'actor': actor, 'mesh': mesh, 'mid': mid, 'role': role, 'born': self.now()}
        self.planes.append(row)
        return row

    def hide_particle(self, component):
        key = component.get_path_name()
        if key not in self.hidden:
            self.hidden[key] = (component, component.is_visible())
        component.set_visibility(False)

    def suppress_overlapping_native_fx(self):
        # This isolated fixture contains one pawn/cast. Scope by native FX tags
        # and explicitly omit the study's own PSCs (tagged SparrowETextureStudy).
        for actor_class in (unreal.SparrowShotWave, unreal.SparrowBowFeedback):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), actor_class):
                if actor.get_owner() == self.rig['pawn']():
                    actor.set_actor_hidden_in_game(True)
        for component in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not _valid(component) or not component.is_active():
                continue
            tags = component.get_editor_property('component_tags')
            if unreal.Name('SparrowETextureStudy') in tags:
                continue
            if component.get_path_name() in self.preserved_arrow_components:
                continue
            if unreal.Name('SparrowSkillFX') in tags:
                self.hide_particle(component)

    def arrow(self, arrow):
        self.latest_shot = self.now()
        if self.first_shot is None:
            self.first_shot = self.latest_shot
        e = self.option.startswith('E')
        for component in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            if not e or component.get_name() not in ('ArrowTrail', 'RapidArrowFlow'):
                self.hide_particle(component)
                continue
            self.preserved_arrow_components.add(component.get_path_name())
            self.snapshots.append((component, component.is_visible(),
                component.get_editor_property('relative_scale3d'),
                component.get_editor_property('custom_time_dilation'), component.get_material(0)))
            component.set_visibility(True)
            if component.get_name() == 'ArrowTrail':
                # Keep the original directional texture, but reduce its footprint
                # so the body and moving wisps do not compete with a bright line.
                component.set_world_scale3d(unreal.Vector(1., .70, .70))
            else:
                width = {'E4': 2.0, 'E5': 2.2, 'E6': 1.55}[self.option]
                component.set_world_scale3d(unreal.Vector(1., width, width))
                component.set_editor_property('custom_time_dilation', .95 if self.option == 'E5' else 1.15)
                if self.option == 'E5':
                    # This is the already-verified 8x8 Wisps replacement; inverse
                    # tint compensates the original gold particle-color multiplier.
                    white = unreal.MaterialLibrary.create_dynamic_material_instance(
                        self.rig['world'](), unreal.load_asset('/Game/ParagonSparrow/FX/Materials/CineRescue/M_Sparrow_Wisps'))
                    assert white
                    white.set_vector_parameter_value('Param', unreal.LinearColor(.26, .36, 2.15, 1.))
                    component.set_material(0, white)
                    self.mids.append(white)
        size = {'E4': (1.9, 1.3, 1.), 'E5': (2.1, 1.35, 1.), 'E6': (1.85, 1.45, 1.),
                'W1': (4.1, 2.0, 1.), 'W2': (3.55, 2.7, 1.), 'W3': (3.4, 2.6, 1.)}[self.option]
        row = self.plane(1, arrow.get_actor_location(), size)
        row['arrow'], row['size'] = arrow, size
        # Keep a small moving, textured volume under the geometric silhouette.
        # This uses only the original Wisps emitter, not its large halo/ring.
        row['flow'] = self.pulse('muzzle', ('Wisps',), arrow.get_actor_location(), self.rotation,
                                 (1.35, 1.15, 1.15) if e else (1.35, .65, .65), .34, 1.7)
        row['second_shards'] = False
        self.arrow_records.append(row)
        origin = self.rig['skills']().get_arrow_origin()
        if self.option in ('E4', 'W1'):
            self.pulse('muzzle', ('Wisps',), origin, self.rotation,
                       (1.4 if e else 2.4, .75, .75), .18, 2.7)
        elif self.option in ('E5', 'W2'):
            self.pulse('muzzle', ('Sparks',), origin, self.rotation,
                       (1.2 if e else 1.9, .85, .85), .24, 1.8)
        else:
            self.pulse('shards', ('Flames2',), origin,
                       unreal.MathLibrary.make_rot_from_z(self.forward), (.45, .45, .60) if e else (.45,.45,.6), .30, 2.2)

    def hit(self, target, direction):
        e = self.option.startswith('E')
        size = (1.7, 1.55, 1.) if e else (3.0, 2.7, 1.)
        row = self.plane(2, target.get_actor_location(), size)
        row['deadline'] = self.now() + (.18 if e else .24)
        self.pulse('impact', ('Sparks', 'SparkTrailHeads'), target.get_actor_location(),
                   self.rotation, (.7,.7,.7) if e else (1.1,1.1,1.1), .27, 2.)

    def update(self, started):
        elapsed = self.now() - started
        self.suppress_overlapping_native_fx()
        e = self.option.startswith('E')
        row = self.muzzle
        if _valid(row['actor']):
            pulse_age = self.now() - self.latest_shot if self.latest_shot is not None else 99.
            if e:
                strength = max(0., 1. - pulse_age / .145)
                progress = min(1., pulse_age / .145)
                size = (2.7, 2.5, 1.)
            else:
                charge = min(1., elapsed / .62)
                progress = charge if self.latest_shot is None else min(1., pulse_age / .18)
                strength = (.12 + .38 * charge * charge) if self.latest_shot is None else max(0., 1. - pulse_age / .18)
                size = (3.7, 3.3, 1.)
            row['actor'].set_actor_location(self.rig['skills']().get_arrow_origin() + self.forward * (20. if e else 85.), False, True)
            row['mesh'].set_world_scale3d(unreal.Vector(*size))
            row['mid'].set_scalar_parameter_value('Strength', strength*(.46 if e else .92))
            row['mid'].set_scalar_parameter_value('Age', progress)
        for row in self.planes:
            if not _valid(row['actor']) or row['role'] == 0:
                continue
            age = self.now() - row['born']
            if row['role'] == 1:
                arrow = row['arrow']
                if not _valid(arrow):
                    row['actor'].destroy_actor()
                    continue
                row['actor'].set_actor_location(arrow.get_actor_location() - self.forward * (18. if e else 55.), False, True)
                if _valid(row['flow']):
                    row['flow'].set_world_location(arrow.get_actor_location(), False, True)
                row['mid'].set_scalar_parameter_value('Strength', .42 if e else .85)
                row['mid'].set_scalar_parameter_value('Age', age)
                if self.option == 'E6' and not row['second_shards'] and age >= .08:
                    self.pulse('shards', ('Flames2',), arrow.get_actor_location(),
                               unreal.MathLibrary.make_rot_from_z(self.forward), (.38,.38,.5), .28, 2.2)
                    row['second_shards'] = True
            else:
                lifetime = row['deadline'] - row['born']
                if self.now() >= row['deadline']:
                    row['actor'].destroy_actor()
                    continue
                row['mid'].set_scalar_parameter_value('Strength', max(0., 1.-age/lifetime)*(.55 if e else 1.))
                row['mid'].set_scalar_parameter_value('Age', min(1., age/lifetime))
        self.tick()

    def close(self):
        for row in self.planes:
            if _valid(row['actor']):
                row['actor'].destroy_actor()
        self.planes.clear()
        restored = 0
        for component, visible in self.hidden.values():
            if _valid(component):
                component.set_visibility(visible)
                restored += 1
        self.hidden.clear()
        # Any short-lived ring actor surviving an interrupted preview is restored.
        for actor_class in (unreal.SparrowShotWave, unreal.SparrowBowFeedback):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), actor_class):
                if actor.get_owner() == self.rig['pawn']():
                    actor.set_actor_hidden_in_game(False)
        return restored + super().close()


def sequence(rig):
    rows = []
    options = [x.strip() for x in os.environ.get('SPARROW_EW_OPTIONS', ','.join(OPTIONS)).split(',') if x.strip()]
    assert options and all(x in OPTIONS for x in options), options
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for index, option in enumerate(options):
        if index:
            rig['switch']('countess')
            yield .15
        rig['switch']('sparrow')
        yield .55
        rig['case']('sparrow_' + option + '_direction')
        targets = rig['layout']([(750, 0), (750, 350), (750, -350)])
        yield .25
        target = targets[0]
        key = option[0]
        study = Study(rig, option)
        seen, hits, frames = set(), [], []
        stacks = rig['skills']().get_relentless_stacks(target)
        expected = (sum(10.*(1.+min(stacks+i, 10)*.0175) for i in range(6))
                    if key == 'E' else 35.*(1.+stacks*.0175))
        health_before = last_health = rig['health'](target)
        started = now()
        try:
            rig['use'](key, target)
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': 'sparrow_' + option + '_direction',
                    'prefix': option + '_direction_video', 'cast_time': started, 'frame_times': []}
            moments = [.23, .65] if key == 'E' else [.74, .90]
            while now() - started < 1.5:
                elapsed = now() - started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    identity = arrow.get_path_name()
                    if arrow.get_owner() != rig['pawn']() or identity in seen:
                        continue
                    seen.add(identity)
                    study.arrow(arrow)
                health = rig['health'](target)
                if health < last_health - .01:
                    study.hit(target, study.forward)
                    hits.append({'elapsed': round(elapsed, 4), 'damage': round(last_health-health, 4)})
                last_health = health
                study.update(started)
                if moments and elapsed >= moments[0]:
                    label = option + '_direction_' + str(len(frames))
                    rig['capture'](label)
                    frames.append({'label': label, 'elapsed': round(elapsed, 4)})
                    moments.pop(0)
                yield 1/60
            rig['finish_video_clip']()
            rig['recovered']()
            rig['check'](len(seen) == (6 if key == 'E' else 1), 'direction study preserves native arrow count')
            actual = health_before-rig['health'](target)
            rig['check'](abs(actual-expected) < .03, 'direction study preserves native damage and passive stacks')
            row = {'option': option, **DESIGNS[option], 'screenshots': frames,
                   'observed_arrows': len(seen), 'actual_hit_events': hits,
                   'expected_damage': expected, 'actual_damage': actual,
                   'preview_particles_created': study.created, 'study_planes_created': study.serial}
        finally:
            rig['finish_video_clip']()
            restored = study.close()
        row['surviving_components_restored'] = restored
        remaining = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.StaticMeshActor)
                     if unreal.Name('SparrowEWStudy') in a.get_editor_property('tags')]
        rig['check'](not remaining, 'temporary direction study meshes cleaned')
        row['temporary_meshes_cleaned'] = not remaining
        rows.append(row)
    result = {'passed': True, 'revision': 2, 'options': rows, 'production_defaults_changed': False,
              'source_pack_assets_saved': False, 'source': 'native E/W casts with transient presentation replacement',
              'visual_review': 'pending actual frame review',
              'limitations': ['Preview layers observe native releases/hits and may lag by one simulation frame.',
                             'Study shapes use transparent planes plus native moving particles; they are not new production meshes.']}
    (rig['OUT']/'EW-direction-studies.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
