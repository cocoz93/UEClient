"""Three distinct native-wing signatures, never installed as production V.

author(out) clones only the two native surface graphs into VSignature20261023.
sequence(rig) replaces their two MID slots transiently, restores them, then
destroys its review form. Native geometry, quick unfold and duration are kept.
The parent exclusively owns editor execution, captures and build integration.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
BaseStudy, valid = _BASE['Study'], _BASE['_valid']
ROOT = '/Game/TopDown/Characters/Sparrow'
PREVIEW = ROOT+'/Previews/VSignature20261023'
VERSIONS = {'V1': '2', 'V2': '1', 'V3': '2'}
TAG = unreal.Name('SparrowVSignatureStudy')
MARKER = 'SparrowSerathGoldFlameShader'
SURFACES = {'Membrane': ROOT+'/Materials/M_SparrowSerathGoldFlame',
            'Splines': ROOT+'/Materials/M_SparrowSerathSplineFlame'}
OPTIONS = ('V1', 'V2', 'V3')
DESIGNS = {
    'V1': {'label': '불사조 깃불', 'surface': '넓고 밀도 높은 세로 불꽃 깃결, 깊은 금색 틈과 밝게 타는 깃끝',
           'entry': '아래쪽 깃부터 위로 불붙는 표면 전개; 떠오르는 분리 파티클 없음',
           'hold': '원래 날개 표면의 촘촘한 깃결을 타고 계속 위로 흐르는 불꽃'},
    'V2': {'label': '백금 광맥', 'surface': '어두운 금빛 얇은 막에 밝은 백금 가지 광맥, 뼈대는 단단한 발광선',
           'entry': '등의 뿌리에서 날개 끝으로 빠르게 연결되는 광맥 점화',
           'hold': '빛이 가지 광맥을 따라 뿌리→끝으로 반복 이동; 전면 화염 채움 없음'},
    'V3': {'label': '불꽃 왕관', 'surface': '중심은 억제하고 외곽/상단의 굵고 끊긴 불꽃 왕관에 밝기 집중',
           'entry': '안쪽·중간·바깥 세 구간이 순서대로 점화되어 외곽 왕관으로 완성',
           'hold': '서로 다른 외곽 구간이 세 박자로 맥동하고 끝에서 짧게 타오름'},
}

_COMMON = '''
float3 rel = WorldPos-RootPos;
float side = abs(dot(rel,SideAxis));
float back = dot(rel,BackAxis);
float x = saturate(side/max(Span,48.0));
float h = saturate((rel.z-ZMin)/max(ZMax-ZMin,60.0));
float support = saturate(Shape);
float age = max(Age,0.0);
float spline = saturate(Spline);
'''
_SHADERS = {
    'V1': '''
// Dense flame feathers, with upward transport and dark gaps between shafts.
float bend = sin(rel.z*.027-Clock*2.8+side*.012)*.16;
float2 uv = float2(side*.022+back*.007+bend, -rel.z*.024+Clock*.96);
float fa = Texture2DSample(Fire,FireSampler,uv).r;
float fb = Texture2DSample(Fire,FireSampler,uv*float2(1.8,.72)+float2(.23,-Clock*.19)).g;
float shaft = pow(saturate(1-abs(frac(side*.055+rel.z*.004+bend*.25)-.5)*2),1.4);
float heat = saturate(fa*.78+fb*.38);
float flame = smoothstep(.11,.53,heat)*(.38+.62*shaft);
float hot = pow(smoothstep(.43,.83,heat),2)*shaft;
float reveal = 1-smoothstep(age/.30,age/.30+.16,h);
float3 color = lerp(float3(.15,.022,.001),float3(3.3,1.14,.025),flame);
color = lerp(color,float3(4.8,3.2,.66),hot*.58);
float alpha = support*(.28+.71*flame)*saturate(reveal);
return float4(color,alpha);
''',
    'V2': '''
// Bright curved branches on a restrained membrane, rather than fire-filled UVs.
float2 uv = float2(side*.014+back*.006,-rel.z*.012+Clock*.24);
float fire = Texture2DSample(Fire,FireSampler,uv).r;
float branch = frac(h*5.2-x*1.85+sin(x*5.5)*.13);
float vein = 1-smoothstep(.020,.075,abs(branch-.5));
vein *= smoothstep(.03,.18,x);
float fineBranch = 1-smoothstep(.012,.045,abs(frac(h*9.3+x*2.1)-.5));
fineBranch *= smoothstep(.28,.86,x)*.32;
vein = saturate(max(vein,fineBranch));
float signal = exp(-pow((x-frac(age*.90))/.085,2));
float ignition = 1-smoothstep(age/.33,age/.33+.11,x);
float lineStrength = saturate(vein*(.48+.52*signal)+spline*.72);
float3 color = float3(.12,.065,.006)*( .35+.65*fire);
color += float3(3.6,3.1,1.72)*lineStrength*(.68+.32*signal);
color += float3(1.4,.56,.025)*signal*.24;
float alpha = support*lerp(.12+.18*fire,.92,lineStrength)*saturate(ignition);
return float4(color,alpha);
''',
    'V3': '''
// A broad broken crown is carried by the actual outer/top wing surface.
float2 uv = float2(side*.018+back*.010+sin(Clock*1.7+h*5)*.08,-rel.z*.021+Clock*.62);
float fire = Texture2DSample(Fire,FireSampler,uv).r;
float outer = max(smoothstep(.28,.58,x),smoothstep(.38,.70,h)*smoothstep(.10,.35,x));
float teeth = .64+.36*pow(saturate(sin(x*31+h*5+fire*2)),3);
float burning = smoothstep(.055,.39,fire);
// The crown keeps a continuous gold silhouette even between fire samples.
float crown = outer*(.38+.62*burning)*teeth;
float sector = min(floor(x*3),2.0);
float phase = frac(age*.78);
float beat = exp(-pow((phase-(.12+sector*.15))/.065,2));
float entry = smoothstep(sector*.075,sector*.075+.14,age);
float3 color = float3(.11,.034,.002)*( .28+.32*fire);
color += float3(3.8,1.65,.055)*crown*(.90+.45*beat);
color += float3(4.6,3.5,1.1)*pow(crown,3)*beat*.44;
float alpha = support*(.18+.73*outer+.07*spline*outer)*entry;
return float4(color,alpha);
''',
}


def write(out, name, value):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def material_path(option, surface):
    return PREVIEW+'/M_VSignature_'+option+'_'+surface


def _hash_sources():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    paths = list(SURFACES.values())+[
        '/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath',
        '/Game/ParagonSerath/Characters/Heroes/Serath/Materials/M_NewWingsSplines2',
        '/Game/ParagonSerath/Characters/Heroes/Serath/Materials/M_WingWebbing_HolyAndEvil2']
    return {asset: hashlib.sha256((content/(asset.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
            for asset in paths}


def _hash_v2():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    paths = [material_path('V2', surface) for surface in SURFACES]
    return {asset: hashlib.sha256(path.read_bytes()).hexdigest()
            for asset in paths
            if (path := content/(asset.removeprefix('/Game/')+'.uasset')).is_file()}


def author(out):
    """Only six owned preview materials are saved; native/source assets are read."""
    before = _hash_sources()
    v2_before = _hash_v2()
    lib = unreal.MaterialEditingLibrary
    rows = []
    for option in OPTIONS:
        expected_version = VERSIONS[option]
        for surface, source in SURFACES.items():
            path = material_path(option, surface)
            assert path.startswith(PREVIEW+'/')
            target = unreal.load_asset(path)
            if target is not None:
                version = unreal.EditorAssetLibrary.get_metadata_tag(target, 'SparrowVSignatureVersion')
                assert version in ('', '1', expected_version), path
                if version == expected_version:
                    rows.append({'option': option, 'surface': surface, 'asset': path, 'reused': True})
                    continue
            else:
                target = unreal.EditorAssetLibrary.duplicate_asset(source, path)
            assert isinstance(target, unreal.Material), path
            nodes = list(lib.get_material_expressions(target))
            matches = [n for n in nodes if n.get_class().get_name() == 'MaterialExpressionCustom'
                       and n.get_editor_property('desc') == MARKER]
            assert len(matches) == 1, (path, 'native surface shader marker')
            shader = matches[0]
            wpo = lib.get_material_property_input_node(target, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
            shader.set_editor_property('code', _COMMON+_SHADERS[option])
            pins = list(shader.get_editor_property('inputs'))
            names = [str(p.get_editor_property('input_name')) for p in pins]
            for name, default in (('Age', 0.), ('Span', 190.), ('ZMin', -75.), ('ZMax', 125.),
                                  ('Spline', 1. if surface == 'Splines' else 0.)):
                if name not in names:
                    pin = unreal.CustomInput()
                    pin.set_editor_property('input_name', name)
                    pins.append(pin)
            shader.set_editor_property('inputs', pins)
            for name, default in (('Age', 0.), ('Span', 190.), ('ZMin', -75.), ('ZMax', 125.),
                                  ('Spline', 1. if surface == 'Splines' else 0.)):
                found = [n for n in lib.get_material_expressions(target)
                         if n.get_class().get_name() == 'MaterialExpressionScalarParameter' and
                         str(n.get_editor_property('parameter_name')) == 'Signature'+name]
                assert len(found) <= 1, (path, name)
                node = found[0] if found else lib.create_material_expression(target, unreal.MaterialExpressionScalarParameter)
                node.set_editor_property('parameter_name', 'Signature'+name)
                node.set_editor_property('default_value', default)
                assert lib.connect_material_expressions(node, '', shader, name)
            assert lib.get_material_property_input_node(target, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET) == wpo
            errors = lib.recompile_material(target)
            assert not errors, (path, errors)
            unreal.EditorAssetLibrary.set_metadata_tag(target, 'SparrowVSignatureVersion', expected_version)
            unreal.EditorAssetLibrary.set_metadata_tag(target, 'SparrowVSignatureOption', option)
            assert unreal.EditorAssetLibrary.save_loaded_asset(target, False), path
            rows.append({'option': option, 'surface': surface, 'asset': path, 'source': source,
                         'original_WPO_unchanged': True, 'reused': False})
    after = _hash_sources()
    assert before == after, 'production/native or original Serath package changed'
    v2_after = _hash_v2()
    assert not v2_before or v2_before == v2_after, 'accepted V2 preview package changed'
    result = {'passed': True, 'materials': rows, 'designs': DESIGNS, 'saved_scope': PREVIEW,
              'production_changed': False, 'source_hashes_unchanged': True,
              'source_hashes': after, 'V2_existing_packages_unchanged': True,
              'V2_package_hashes': v2_after, 'versions': VERSIONS,
              'visual_acceptance': 'pending actual PIE review'}
    write(out, 'V-signature-author.json', result)
    return result


class Signature(BaseStudy):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.form, self.wing, self.birth = None, None, None
        self.bones, self.slots, self.hidden, self.motion = [], [], [], []
        self.hidden_paths, self.beats = set(), set()
        self.samples = []
        self.fallback = False

    def observe(self, form):
        self.form, self.birth = form, self.now()
        self.wing = next(c for c in form.get_components_by_class(unreal.SkeletalMeshComponent)
                         if c.get_name() == 'SerathWings')
        self.bones = [self.wing.get_bone_name(i) for i in range(self.wing.get_num_bones())
                      if 'wing' in str(self.wing.get_bone_name(i)).lower()]
        for slot_name, surface in (('M12_WingSplines', 'Splines'), ('M13_WingMembrane', 'Membrane')):
            slot = self.wing.get_material_index(slot_name)
            original = self.wing.get_material(slot)
            assert slot >= 0 and isinstance(original, unreal.MaterialInstanceDynamic)
            material = unreal.load_asset(material_path(self.option, surface))
            assert material, 'Run author(out) before PIE: '+material_path(self.option, surface)
            mid = unreal.MaterialLibrary.create_dynamic_material_instance(self.rig['world'](), material)
            assert mid
            mid.copy_material_instance_parameters(original, True)
            self.wing.set_material(slot, mid)
            self.slots.append((slot, original, mid))
        self.events.append({'event': 'native_V', 'time': self.now()-self.born,
                            'surface_signature': self.option, 'mesh': self.wing.get_skeletal_mesh_asset().get_path_name()})

    def root(self):
        return self.rig['pawn']().get_editor_property('mesh').get_socket_location('spine_03')

    def point(self, side, reach, height=0.):
        root = self.root()
        right = self.rig['pawn']().get_actor_right_vector()
        points = [self.wing.get_socket_location(b) for b in self.bones] if valid(self.wing) else []
        tip = max(points, key=lambda p: (p-root).dot(right)*side) if points else None
        if tip is None or (tip-root).dot(right)*side < 24.:
            self.fallback = True
            tip = root+right*(side*150.)-self.rig['pawn']().get_actor_forward_vector()*35.+self.up*25.
        return root+(tip-root)*reach+self.up*height

    def suppress_native_entry(self):
        # Only the native V entry templates are hidden, including its precast
        # rise. Production templates themselves are never modified/deactivated.
        for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not valid(particle):
                continue
            template = particle.get_editor_property('template')
            if not template or not template.get_name().startswith('P_SparrowWingEntry'):
                continue
            path = particle.get_path_name()
            if path not in self.hidden_paths:
                self.hidden_paths.add(path)
                self.hidden.append((particle, particle.is_visible()))
                particle.set_visibility(False)

    def emit(self, key, names, side, reach, height, scale, life, rise=0., end_reach=None):
        p = self.point(side, reach, height)
        direction = self.up if rise else (self.point(side, 1.)-self.root()).normal()
        particle = self.pulse(key, names, p, unreal.MathLibrary.make_rot_from_z(direction), scale, life, 1.5)
        self.motion.append({'particle': particle, 'born': self.now(), 'life': life,
                            'side': side, 'reach': reach, 'height': height, 'rise': rise,
                            'end_reach': reach if end_reach is None else end_reach})
        self.events.append({'event': 'boundary', 'age': self.now()-self.birth, 'side': side,
                            'reach': reach, 'rise': rise, 'emitters': names})

    def update(self):
        self.suppress_native_entry()
        if self.birth is None:
            self.tick()
            return
        age = self.now()-self.birth
        root = self.root()
        right = self.rig['pawn']().get_actor_right_vector()
        bone_points = [self.wing.get_socket_location(b)-root for b in self.bones]
        span = max([abs(p.dot(right)) for p in bone_points]+[48.])+12.
        zmin = min([p.z for p in bone_points]+[-25.])-20.
        zmax = max([p.z for p in bone_points]+[45.])+20.
        for _, original, mid in self.slots:
            mid.set_scalar_parameter_value('WingAlpha', original.get_scalar_parameter_value('WingAlpha'))
            for name in ('WingRootPosition', 'WingSideAxis', 'WingBackAxis'):
                mid.set_vector_parameter_value(name, original.get_vector_parameter_value(name))
            for name, value in (('Age', age), ('Span', span), ('ZMin', zmin), ('ZMax', zmax)):
                mid.set_scalar_parameter_value('Signature'+name, value)
        if self.option == 'V2':
            beat = int(age/.085)
            # The same root-to-tip signal repeats along the surface and boundary.
            if beat not in self.beats:
                self.beats.add(beat)
                reach = min(.98, (age*.90 % 1.))
                for side in (-1, 1):
                    self.emit('muzzle', ('Sparks',), side, reach, 3., (.32,.24,.24), .20,
                              end_reach=min(1.06,reach+.13))
        elif self.option == 'V3':
            cycle = int(age*.78)
            phase = age*.78-cycle
            for step, moment in enumerate((.12,.27,.42)):
                token = (cycle, step)
                if phase >= moment and token not in self.beats:
                    self.beats.add(token)
                    for side in (-1, 1):
                        reach = (.57,.79,1.04)[step]
                        self.emit('impact', ('Main Flames','Sparks'), side, reach, 12.+step*5.,
                                  (.52,.32,.60), .26, rise=18.)
        for item in self.motion[:]:
            particle = item['particle']
            if not valid(particle) or self.now()-item['born'] >= item['life']:
                self.motion.remove(item)
                continue
            progress = (self.now()-item['born'])/item['life']
            reach = item['reach']+(item['end_reach']-item['reach'])*progress
            particle.set_world_location(self.point(item['side'], reach, item['height']+item['rise']*progress), False, False)
        self.tick()
        if not self.samples or age-self.samples[-1]['age'] >= .32:
            self.samples.append({'age': age, 'span': span, 'zmin': zmin, 'zmax': zmax,
                                 'wing_scale': self.rig['vec'](self.wing.get_world_scale()),
                                 'live_particles': sum(p.get_num_active_particles() for p,_ in self.effects if valid(p))})

    def close(self):
        for slot, original, mid in self.slots:
            if valid(self.wing) and self.wing.get_material(slot) == mid:
                self.wing.set_material(slot, original)
        for particle, visible in self.hidden:
            if valid(particle):
                particle.set_visibility(visible)
        self.motion.clear()
        return super().close()


def sequence(rig):
    options = [v.strip().upper() for v in os.environ.get(
        'SPARROW_V_SIGNATURE_OPTIONS', 'V1,V2,V3').split(',') if v.strip()]
    assert options and all(v in OPTIONS for v in options), options
    before_sources = _hash_sources()
    rows = []
    for option in options:
        rig['switch']('countess')
        yield .20
        rig['switch']('sparrow')
        yield .60
        prefix = 'V_signature_'+option
        rig['case'](prefix)
        targets = rig['layout']([(650, 0), (450, 430), (650, -430)])
        yield .20
        body = rig['pawn']().get_editor_property('mesh')
        body_materials = [body.get_material(i).get_path_name() for i in range(body.get_num_materials())]
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(body.get_skeletal_mesh_asset())
        sections = [[body.is_material_section_shown(i,lod) for i in range(body.get_num_materials())] for lod in range(lods)]
        health = [rig['health'](d) for d in targets]
        study, captures = Signature(rig, option), []
        started = study.now()
        moments = [.20,.55,1.35,2.20]
        try:
            rig['use']('V', targets[0])
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': prefix, 'prefix': prefix+'_video',
                    'cast_time': started, 'frame_times': []}
            while study.now()-started < 3.6:
                forms = unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings)
                if study.form is None and forms:
                    rig['check'](len(forms) == 1, option+' uses one real V form')
                    study.observe(forms[0])
                study.update()
                if study.birth is not None and moments and study.now()-study.birth >= moments[0]:
                    name = prefix+'_wing_'+str(round(moments.pop(0)*100)).zfill(3)
                    rig['capture'](name)
                    captures.append(name)
                yield 1./rig['FPS']
            rig['finish_video_clip']()
            rig['check'](valid(study.form) and len(study.slots) == 2 and
                         all(study.wing.get_material(slot) == mid for slot,_,mid in study.slots),
                         option+' keeps both private preview MIDs despite native wing updates')
            rig['check'](study.wing.get_skeletal_mesh_asset().get_path_name().startswith(
                '/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath.'), option+' preserves original Serath geometry')
            rig['check'](study.form.get_life_span() > 35., option+' preserves native V lifetime')
            rig['check'](len(captures) == 4 and len(study.samples) > 4 and
                         (option == 'V1' or study.peak_particles > 0),
                         option+' has actual entry/hold captures; V1 is native surface only')
            rig['check']([rig['health'](d) for d in targets] == health, option+' adds no damage')
            rig['recovered']()
            row = {'option': option, **DESIGNS[option], 'video_prefix': prefix+'_video',
                'representative_wing_ages': [.20,.55,1.35,2.20], 'captures': captures,
                'native_form_spawn_elapsed': study.birth-started, 'wing_samples': study.samples,
                'surface_materials': [material_path(option, s) for s in ('Membrane','Splines')],
                'boundary_events': study.events, 'peak_live_particles': study.peak_particles,
                'endpoint_fallback_used': study.fallback, 'production_installed': False}
        finally:
            rig['finish_video_clip']()
            failures = study.close()
            if valid(study.form):
                study.form.destroy_actor()
        yield .15
        rig['check'](not failures and not study.effects, option+' restores MID slots and removes transient particles')
        rig['check']([body.get_material(i).get_path_name() for i in range(body.get_num_materials())] == body_materials,
                     option+' restores original body materials')
        restored = [[body.is_material_section_shown(i,lod) for i in range(body.get_num_materials())] for lod in range(lods)]
        rig['check'](restored == sections, option+' restores cloak and hood state')
        rows.append(row)
        write(rig['OUT'], 'V-signature-studies.json', {'passed': False, 'phase': 'in_progress', 'studies': rows})
    assert before_sources == _hash_sources(), 'original or production source package changed'
    write(rig['OUT'], 'V-signature-studies.json', {'passed': True, 'studies': rows,
        'preview_material_scope': PREVIEW, 'production_installed': False,
        'geometry_native_unfold_and_duration_unchanged': True, 'source_hashes_unchanged': True,
        'visual_acceptance': 'pending parent actual quarter-view review',
        'limitations': ['새 전개 방향은 원래 bone animation 위의 표면 점화이며 원본 펼침 animation 자체는 유지한다.',
                        'Python 관찰/적용은 native form 생성 뒤 최대 한 프레임 늦을 수 있다.',
                        '끝점 fallback 사용 여부는 각 시안에 기록한다. 입자 수는 성능 계측이 아니다.']})
