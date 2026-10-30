"""E7/E9 history and two denser compositions driven by six native E arrows.

Only this helper is new. Shared particle templates, source materials, native
skill code and production choices are never edited. Call author(out) before
PIE, then sequence(rig) through the existing new_skills_probe hook. The existing
audited SubUV A-opacity/R-light material supplies all torn-flame sprites.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_FRESH = runpy.run_path(str(Path(__file__).with_name('sparrow_fresh_studies.py')))
_PARTICLES = _FRESH['_PARTICLES']
FreshStudy = _FRESH['Study']
ParticleStudy = _PARTICLES['Study']
_valid = _PARTICLES['_valid']
SOURCE_PLASMA = '/Game/ParagonSparrow/FX/Materials/Energy/Plasma/M_Plasma_v5_Flipbook2'
ENERGY_MESH = '/Game/TopDown/Characters/Sparrow/Meshes/SM_SparrowEnergyWings'
ENERGY_MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowEnergyWings'
OPTIONS = ('E7r', 'E9r', 'E10', 'E11')
DENSE_OPTIONS = ('E10', 'E11')
DESIGNS = {
    'E7r': {
        'label': '정제한 황금 깃불 쇄도',
        'description': '활의 압축 불꽃이 세 단계로 짧게 열리고, 좁은 찢긴 불꽃 두 줄과 작은 깃편이 실제 화살을 따른다',
        'release': '발사 순간·+.033초·+.067초에 압축→벌어짐→가는 후류, 넓은 섬광/바닥 고리 없음',
        'flight': '원본 진행선과 불꽃결 유지, 굵은 덩어리 대신 좁은 두 줄과 간헐적 작은 곡면 깃편',
        'hit': '진행축 뒤로 짧게 찢어지는 황금 편과 불티, 6발 중 마지막에만 약한 백금 여운',
    },
    'E9r': {
        'label': '정제한 황금 깃편 소용돌이',
        'description': '원래 곡면 불꽃의 두께를 유지한 세 겹 깃편과 작은 불티가 화살 중심을 따라가며 명중에서 방향성 부채로 갈라진다',
        'release': '좌우 작은 깃편 두 장과 세로로 압축된 불꽃결, 큰 파열광 없음',
        'flight': '나선 반경17~23cm와 길이별 크기차, 위치가 무작위로 흔들리지 않는 일정한 세 겹 흐름',
        'hit': '진행 방향을 기준으로 작은 깃편5개와 낮은 강도 불티, 원본 명중 섬광은 증폭하지 않음',
    },
    'E10': {
        'label': '익궁 · 황금 깃불 날개',
        'description': '활 앞의 고정된 여섯 띠 황금 익궁이 발사 내내 맥동하고, 중앙의 불꽃이 화살을 밀어낸다',
        'release': '준비에서 작은 양익 → 발사 순간 중앙 압축 → .033/.067초 깃끝과 불티로 연결',
        'flight': '금색 기본 화살과 원본 침식 불꽃 후류, 반복된 큰 Wisps층 제거; 측면 익궁이 발사 간격을 채움',
        'hit': '큰 원본 흰 파열을 이 시안에서만 가리고 짧은 금빛 깃편·방향성 불티로 접촉을 드러냄',
    },
    'E11': {
        'label': '백금 쇄도 · 층상 깃불 추진',
        'description': '좁고 긴 여섯 금빛 추진핀이 세 겹 깃불과 함께 활 앞으로 분출하고, 금색 중심 화살이 목표로 쏟아진다',
        'release': '작은 준비 깃불을 좁은 전방 세 층으로 연결하고, 매 발 두 갈래 짧은 불티가 가속감을 만듦',
        'flight': '흰 구름을 제거한 금색 몸체와 짧은 황금 후류; 긴 원형 광선이나 바닥 원 없음',
        'hit': '중심을 향해 압축되는 작은 세 갈래 파편과 짧은 불티; 넓은 흰 섬광은 교체',
    },
}


def _selected():
    selected = [item.strip() for item in os.environ.get(
        'SPARROW_E_REFINED_OPTIONS', ','.join(DENSE_OPTIONS)).split(',') if item.strip()]
    assert selected and all(item in OPTIONS for item in selected), selected
    assert len(selected) == len(set(selected)), selected
    return selected


def _write(out, name, result):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    """Read-only emitter and material audit. No shader/asset authoring in PIE."""
    source_report = _PARTICLES['author'](out)
    material = unreal.load_asset(_FRESH['PLASMA_PREVIEW'])
    assert isinstance(material, unreal.Material), 'Run sparrow_fresh_studies.author_fx once before this helper'
    custom = [node for node in unreal.MaterialEditingLibrary.get_material_expressions(material)
              if isinstance(node, unreal.MaterialExpressionCustom)]
    assert len(custom) == 1, 'Expected the already audited torn-flame material'
    code = str(custom[0].get_editor_property('code'))
    assert 'TextureAlpha' in code and 'TextureRed' in code and 'ParticleAlpha' in code, code
    assert 'max(' not in code, 'RGB maximum must never become this flipbook opacity'
    source_plasma = unreal.load_asset(SOURCE_PLASMA)
    assert isinstance(source_plasma, unreal.Material), SOURCE_PLASMA
    lib = unreal.MaterialEditingLibrary
    source_scalars = [str(name) for name in lib.get_scalar_parameter_names(source_plasma)]
    assert 'Param' in source_scalars, source_scalars
    opacity = lib.get_material_property_input_node(source_plasma, unreal.MaterialProperty.MP_OPACITY)
    assert isinstance(opacity, unreal.MaterialExpressionSubtract), opacity
    opacity_inputs = [node for node in lib.get_inputs_for_material_expression(source_plasma, opacity) if node]
    product = next(node for node in opacity_inputs if isinstance(node, unreal.MaterialExpressionMultiply))
    fade = next(node for node in opacity_inputs if isinstance(node, unreal.MaterialExpressionLinearInterpolate))
    alpha_inputs = [node for node in lib.get_inputs_for_material_expression(source_plasma, product) if node]
    alpha_bindings = [{'class': node.get_class().get_name(),
                       'output': str(lib.get_input_node_output_name_for_material_expression(product, node))}
                      for node in alpha_inputs]
    assert {'class': 'MaterialExpressionParticleSubUV', 'output': 'A'} in alpha_bindings, alpha_bindings
    assert {'class': 'MaterialExpressionParticleColor', 'output': 'A'} in alpha_bindings, alpha_bindings
    fade_inputs = [node.get_class().get_name()
                   for node in lib.get_inputs_for_material_expression(source_plasma, fade) if node]
    assert 'MaterialExpressionParticleRelativeTime' in fade_inputs, fade_inputs
    result = {'passed': source_report['passed'], 'options': {key: DESIGNS[key] for key in _selected()},
              'material': material.get_path_name(), 'opacity_basis': 'Original SubUV A; internal light from R',
              'E7_main_material': source_plasma.get_path_name(),
              'E7_opacity_basis': 'Audited original: SubUV.A * ParticleAlpha - lerp(Param,.5,ParticleRelativeTime)',
              'E7_source_opacity_graph': {'root': opacity.get_class().get_name(),
                                         'alpha_product_inputs': alpha_bindings,
                                         'fade_inputs': fade_inputs},
              'material_graph_unchanged': True, 'source_assets_saved': False, 'assets_saved': False,
              'native_skill_code_changed': False, 'production_defaults_changed': False,
              'selection_required_for_production': True, 'revision': 7,
              'new_dense_options': list(DENSE_OPTIONS),
              'new_material_or_particle_assets_created': False}
    if any(option in DENSE_OPTIONS for option in _selected()):
        mesh = unreal.load_asset(ENERGY_MESH)
        wing_material = unreal.load_asset(ENERGY_MATERIAL)
        assert isinstance(mesh, unreal.StaticMesh), ENERGY_MESH
        assert isinstance(wing_material, unreal.Material), ENERGY_MATERIAL
        scalars = [str(name) for name in lib.get_scalar_parameter_names(wing_material)]
        assert all(name in scalars for name in ('Envelope', 'Growth')), scalars
        result['reused_project_owned_mesh'] = mesh.get_path_name()
        result['reused_project_owned_mesh_material'] = wing_material.get_path_name()
        result['reused_assets_saved'] = False
    _write(out, 'E-refined-author.json', result)
    return result


def _basis(direction):
    length = direction.length()
    assert length > .001, direction
    forward = unreal.Vector(direction.x / length, direction.y / length, direction.z / length)
    right = unreal.Vector(-forward.y, forward.x, 0.)
    if right.length() < .001:
        right = unreal.Vector(0., 1., 0.)
    right_length = right.length()
    right = unreal.Vector(right.x / right_length, right.y / right_length, right.z / right_length)
    up = unreal.Vector(forward.y * right.z - forward.z * right.y,
                       forward.z * right.x - forward.x * right.z,
                       forward.x * right.y - forward.y * right.x)
    return forward, right, up


class Study(FreshStudy):
    """Layer existing particles by direction, scale and timing on instances."""
    def __init__(self, rig, option):
        assert option in OPTIONS, option
        super().__init__(rig, 'E7' if option == 'E7r' else 'E9')
        self.variant = option
        self.events, self.particle_refs = [], []
        self.hit_serial = 0
        self.release_stages = [0, 0, 0]
        self.emitter_selections = set()
        self.material_bindings = {}
        # Preserve the accepted E7 torn-flame body. Revision 1 reduced width,
        # opacity and duration together, and actual quarter-view captures then
        # showed mostly small fragments. Refinement must supplement that body.
        # Sparse platinum accents never become an extra full-white flash.
        self.gold.set_vector_parameter_value('Tint', unreal.LinearColor(3.2, 2.05, .38, 1.))
        self.gold.set_scalar_parameter_value('OpacityGain', 1.5)
        self.white.set_vector_parameter_value('Tint', unreal.LinearColor(2.85, 2.75, 2.10, 1.))
        self.white.set_scalar_parameter_value('OpacityGain', 1.05)
        self.e7_native_flame = None
        if self.variant == 'E7r':
            # The accepted source material erodes weak alpha over particle life.
            # The fresh material's sqrt(alpha) with no erosion made overlapping
            # E7 wakes into soft square clouds at .47 seconds in revision 2.
            # Restore that real A/R source on E7 only; E9 stays unchanged.
            self.e7_native_flame = unreal.MaterialLibrary.create_dynamic_material_instance(
                rig['world'](), unreal.load_asset(SOURCE_PLASMA))
            assert self.e7_native_flame, SOURCE_PLASMA
            self.e7_native_flame.set_scalar_parameter_value('Param', 0.)
            self.mids.append(self.e7_native_flame)

    def _audit_binding(self, particle, slot, material, label):
        actual = particle.get_material(slot)
        assert actual == material, (label, slot, actual, material)
        if label not in self.material_bindings:
            parent = material.get_editor_property('parent')
            self.material_bindings[label] = {
                'component': particle.get_path_name(), 'slot': slot,
                'num_materials': particle.get_num_materials(),
                'bound_material': actual.get_path_name(),
                'parent': parent.get_path_name() if parent else None,
                'binding_matches': True}

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1., white=False):
        particle = ParticleStudy.pulse(self, key, names, position, rotation, scale, seconds, speed)
        self.particle_refs.append(particle)
        self.emitter_selections.add(key + ':' + ','.join(names))
        if 'Wisps' in names:
            # SetMaterial slots retain original template order after filtering.
            slot = _PARTICLES['EMITTERS'][key].index('Wisps')
            material = self.white if white else self.gold
            if self.variant == 'E7r' and not white:
                material = self.e7_native_flame
            particle.set_material(slot, material)
            self._audit_binding(particle, slot, material, key + '_wisps_' + ('white' if white else 'gold'))
        return particle

    def fragment(self, position, direction, width, length, life=.20, speed=2.5):
        # The source curved mesh uses local Z for velocity. Its original
        # textured material remains intact; no white disc/plane replacement.
        return self.pulse('shards', ('Flames2',), position,
                          unreal.MathLibrary.make_rot_from_z(direction),
                          (width, width * .82, length), life, speed)

    def _later(self, delay, action, *args):
        self.events.append((self.now() + delay, action, args))

    def _release(self, stage, origin, direction, right, up, serial):
        self.release_stages[stage] += 1
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        if self.variant == 'E7r':
            if stage == 0:
                self.pulse('muzzle', ('Wisps',), origin, rotation, (1.80, 1.05, 1.05), .20, 1.6)
                self.pulse('muzzle', ('Sparks',), origin, rotation, (.48, .36, .36), .14, 2.5)
            elif stage == 1:
                for side in (-1., 1.):
                    self.fragment(origin + direction * 15. + right * (side * 12.),
                                  direction + right * (side * .12), .30, .40, .22, 2.2)
            else:
                self.pulse('muzzle', ('Wisps',), origin + direction * 29., rotation,
                           (.84, .28, .30), .13, 2.2, serial % 3 == 2)
        else:
            if stage == 0:
                self.pulse('muzzle', ('Wisps',), origin, rotation, (.95, .40, .54), .14, 2.1)
                for side in (-1., 1.):
                    self.fragment(origin + right * (side * 14.), direction + right * (side * .1),
                                  .27, .40, .24, 2.2)
            elif stage == 1:
                self.pulse('muzzle', ('Sparks',), origin + direction * 12., rotation,
                           (.50, .34, .38), .15, 2.5)
                self.fragment(origin + direction * 14. + up * 8., direction,
                              .29, .43, .24, 2.2)
            else:
                self.pulse('muzzle', ('Wisps',), origin + direction * 24., rotation,
                           (.76, .27, .34), .13, 2.3, serial % 3 == 2)

    def arrow(self, arrow):
        direction, right, up = _basis(arrow.get_flight_direction())
        serial = len(self.arrows)
        row = {'arrow': arrow, 'born': self.now(), 'next_emit': self.now() + .035,
               'serial': serial, 'emissions': 0, 'direction': direction, 'right': right, 'up': up}
        self.arrows.append(row)
        for particle in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            name = particle.get_name()
            if name not in ('ArrowTrail', 'RapidArrowFlow'):
                continue
            self.modified_components[name] += 1
            self.snapshots.append((particle, particle.is_visible(),
                particle.get_editor_property('relative_scale3d'),
                particle.get_editor_property('custom_time_dilation'), particle.get_material(0)))
            if name == 'ArrowTrail':
                particle.set_world_scale3d(unreal.Vector(1., .72, .72))
            else:
                width = 1.30 if self.variant == 'E7r' else 1.25
                particle.set_world_scale3d(unreal.Vector(1., width, width))
                if self.variant == 'E7r':
                    particle.set_material(0, self.e7_native_flame)
                    self._audit_binding(particle, 0, self.e7_native_flame, 'RapidArrowFlow')
        origin = self.rig['skills']().get_arrow_origin()
        self._release(0, origin, direction, right, up, serial)
        self._later(.033, self._release, 1, origin, direction, right, up, serial)
        self._later(.067, self._release, 2, origin, direction, right, up, serial)

    def hit(self, target, direction):
        forward, right, up = _basis(direction)
        point = target.get_actor_location()
        rotation = unreal.MathLibrary.make_rot_from_x(forward)
        serial = self.hit_serial
        self.hit_serial += 1
        self.pulse('impact', ('Sparks', 'SparkTrailHeads'), point, rotation,
                   (.44, .38, .38), .19, 2.35)
        if self.variant == 'E7r':
            # Two small torn pieces travel forward/outward instead of forming
            # a repeated circle over the original native target flash.
            for side in (-1., 1.):
                self.fragment(point - forward * 12. + right * (side * 10.),
                              forward + right * (side * .38) + up * .12,
                              .13, .22, .18, 2.6)
            if serial == 5:
                self.pulse('impact', ('Wisps',), point - forward * 10., rotation,
                           (.54, .27, .31), .16, 2.3, True)
        else:
            # Small ordered fan: centre long, sides progressively shorter.
            for index, side in enumerate((-1., -.5, 0., .5, 1.)):
                height = (1. - abs(side)) * 15. - 4.
                self.fragment(point - forward * (8. + abs(side) * 8.) + right * (side * 20.) + up * height,
                              forward + right * (side * .48) + up * (.07 + index * .025),
                              .09 + (1. - abs(side)) * .025, .15 + (1. - abs(side)) * .06, .19, 2.8)
            self._later(.045, self.pulse, 'impact', ('Sparks',),
                        point + forward * 9. + up * 5., rotation, (.35, .29, .29), .14, 2.6)

    def _flight(self, row):
        arrow = row['arrow']
        if not _valid(arrow):
            return
        direction, right, up = row['direction'], row['right'], row['up']
        position = arrow.get_actor_location()
        age = self.now() - row['born']
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        step = row['emissions']
        if self.variant == 'E7r':
            # Keep the accepted thick two-wisp main layer, then add the smaller
            # orderly fragments. Changing every layer into a thin accent loses
            # volume at the actual play camera even if an enlarged crop is neat.
            for side in (-1., 1.):
                spread = 15. + 2. * math.sin(step * 1.7 + row['serial'] * .35)
                point = position - direction * (29. + (side + 1.) * 5.) + right * (side * spread)
                self.pulse('muzzle', ('Wisps',), point, rotation,
                           (1.05 if side < 0. else 1.15, .75, .75), .25, 1.4)
            if step % 2 == 0:
                side = -1. if (step + row['serial']) % 4 < 2 else 1.
                self.fragment(position - direction * 24. + right * (side * 13.) + up * 5.,
                              direction + right * (side * .10), .13, .23, .17, 2.7)
        else:
            # Preserve E9's three native curved fragments at their readable
            # original size, but align phases and shorten the outer fragments.
            # A new shot begins at the same phase, rather than arbitrary offsets.
            for strand in range(3):
                phase = age * 13.0 + strand * math.tau / 3.
                radius = 20. + 3. * math.sin(age * 9.)
                point = position - direction * (22. + strand * 15.) + right * (math.cos(phase) * radius) + up * (math.sin(phase) * radius * .74)
                tangent = direction + right * (-math.sin(phase) * .16) + up * (math.cos(phase) * .14)
                self.fragment(point, tangent, (.22, .20, .18)[strand],
                              (.32, .29, .26)[strand], .27, 2.0)
            if step % 2 == 0:
                self.pulse('muzzle', ('Wisps',), position - direction * 37., rotation,
                           (.78, .27, .31), .15, 2.1)
        if step % 3 == 1:
            self.pulse('muzzle', ('Sparks',), position - direction * 18., rotation,
                       (.26, .25, .25), .13, 2.6)
        row['emissions'] += 1

    def update(self, started):
        now = self.now()
        # Suppress only the old decorative E ring/feedback actors while the
        # study is active. Real projectile texture and native hit stay visible.
        for cls in (unreal.SparrowShotWave, unreal.SparrowBowFeedback):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), cls):
                if actor.get_owner() == self.rig['pawn']():
                    actor.set_actor_hidden_in_game(True)
        for due, action, args in self.events[:]:
            if now >= due:
                self.events.remove((due, action, args))
                action(*args)
        for row in self.arrows:
            if _valid(row['arrow']) and now >= row['next_emit']:
                row['next_emit'] = now + .075
                self._flight(row)
        self.tick()

    def close(self):
        self.events.clear()
        return super().close()


class DenseStudy(Study):
    """Two different silhouettes, with a connected bow/feed/flight/hit rhythm.

    Uses original curved Flames2 and the source flipbook's real age erosion.
    No material is authored. Native target flashes are hidden on matching PSC
    instances inside this isolated preview, so fine contact detail is readable.
    """
    def __init__(self, rig, option):
        assert option in DENSE_OPTIONS, option
        super().__init__(rig, 'E7r')
        self.dense_option = option
        self.dense_started = None
        self.feed_serial = 0
        self.next_feed = 0.
        self.preparation_events = 0
        self.replaced_native_particles = set()
        self.native_replacement_counts = {'muzzle': 0, 'impact': 0}
        self.mesh_proxy = None
        self.mesh_proxy_refs = []
        self.mesh_component = None
        self.mesh_mid = None
        self.last_dense_release = -99.
        self.mesh_samples = []

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1., white=False):
        # All sprite additions use the original alpha/age erosion. Platinum
        # enters through the native flight material, not a broad white flare.
        particle = ParticleStudy.pulse(self, key, names, position, rotation, scale, seconds, speed)
        self.particle_refs.append(particle)
        self.emitter_selections.add(key + ':' + ','.join(names))
        if 'Wisps' in names:
            slot = _PARTICLES['EMITTERS'][key].index('Wisps')
            particle.set_material(slot, self.e7_native_flame)
            self._audit_binding(particle, slot, self.e7_native_flame, key + '_wisps_source_erosion')
        return particle

    def _replace_native_at(self, point, template):
        # Only called at six real releases/hits, not once per frame. The fixture
        # has one active cast. Exact template, native tag, locality and our own
        # exclusion tag keep the override scoped to its visible PSC instances.
        for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not _valid(particle) or not particle.is_active():
                continue
            tags = particle.get_editor_property('component_tags')
            if unreal.Name('SparrowETextureStudy') in tags or unreal.Name('SparrowSkillFX') not in tags:
                continue
            if particle.get_editor_property('template') != template:
                continue
            if (particle.get_world_location() - point).length() > 190.:
                continue
            self.hide(particle)
            if particle.get_path_name() not in self.replaced_native_particles:
                key = 'muzzle' if template == self.templates['muzzle'] else 'impact'
                self.native_replacement_counts[key] += 1
            self.replaced_native_particles.add(particle.get_path_name())

    def begin(self, target):
        self.dense_started = self.now()
        direction = target.get_actor_location() - self.rig['skills']().get_arrow_origin()
        self.dense_forward, self.dense_right, self.dense_up = _basis(direction)
        self._spawn_mesh_silhouette()
        self.next_feed = self.dense_started + .095
        self._feed(.62)
        self.preparation_events += 1

    def _spawn_mesh_silhouette(self):
        origin = self.rig['skills']().get_arrow_origin()
        name = 'SparrowEDenseMesh_' + self.dense_option
        self.rig['cmd'](f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {origin.x} {origin.y} {origin.z}')
        actor = next((item for item in unreal.GameplayStatics.get_all_actors_of_class(
            self.rig['world'](), unreal.StaticMeshActor) if item.get_name() == name), None)
        assert actor, name
        actor.set_actor_enable_collision(False)
        actor.set_life_span(3.)
        actor.set_editor_property('tags', [unreal.Name('SparrowEDenseMeshPreview')])
        component = actor.get_editor_property('static_mesh_component')
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property('generate_overlap_events', False)
        component.set_editor_property('can_ever_affect_navigation', False)
        component.set_editor_property('cast_shadow', False)
        component.set_static_mesh(unreal.load_asset(ENERGY_MESH))
        material = component.create_dynamic_material_instance(0, unreal.load_asset(ENERGY_MATERIAL))
        assert material
        material.set_scalar_parameter_value('Envelope', 0.)
        material.set_scalar_parameter_value('Growth', 0.)
        self.mesh_proxy, self.mesh_component, self.mesh_mid = actor, component, material
        self.mesh_proxy_refs.append(actor)
        self.mids.append(material)
        self._update_mesh_silhouette()

    def _update_mesh_silhouette(self):
        if not _valid(self.mesh_proxy):
            return
        elapsed = self.now() - self.dense_started
        pulse = max(0., 1. - (self.now() - self.last_dense_release) / .10)
        fade = max(0., min(1., (1.30 - elapsed) / .24))
        origin = self.rig['skills']().get_arrow_origin()
        direction = self.dense_forward
        rotation = unreal.MathLibrary.make_rot_from_x(unreal.Vector(direction.x, direction.y, 0.))
        # Source wings spread along local +/-Y with negative-X sweep. E10 uses
        # the observed S silhouette at small scale. E11 reflects/lengthens X and
        # compresses Y into a six-finned forward nozzle, not another wide wing.
        if self.dense_option == 'E10':
            scale = unreal.Vector(.40, .42, .40)
            position = origin + direction * 28. + self.dense_up * 5.
            envelope = (.62 + pulse * .16) * fade
        else:
            scale = unreal.Vector(-1.10, .15, .28)
            position = origin + direction * 18. + self.dense_up * 7.
            envelope = (.75 + pulse * .15) * fade
        self.mesh_proxy.set_actor_location_and_rotation(position, rotation, False, True)
        self.mesh_proxy.set_actor_scale3d(scale)
        self.mesh_mid.set_scalar_parameter_value('Envelope', envelope)
        self.mesh_mid.set_scalar_parameter_value('Growth', min(1., max(0., elapsed / .16)))
        self.mesh_component.set_visibility(envelope > .002)
        if len(self.mesh_samples) < 4 and elapsed >= (.10, .30, .57, .90)[len(self.mesh_samples)]:
            self.mesh_samples.append({'elapsed': elapsed, 'envelope': envelope,
                                      'scale': [scale.x, scale.y, scale.z],
                                      'origin_offset_cm': 28. if self.dense_option == 'E10' else 18.})

    def _feed(self, gain=1.):
        origin = self.rig['skills']().get_arrow_origin()
        forward, right, up = self.dense_forward, self.dense_right, self.dense_up
        if self.dense_option == 'E10':
            # The fixed mesh carries the readable wing silhouette. Sparse
            # source fragments now decorate its ends instead of attempting to
            # construct a wing from randomly oriented sixteen-particle bursts.
            for side in (-1., 1.):
                position = origin + right * (side * 49.) + up * 19. + forward * 9.
                direction = forward + right * (side * .22) + up * .06
                self.fragment(position, direction, .17 * gain, .26 * gain, .18, 2.3)
        else:
            # Explicit origin and common direction. Three simultaneous depths
            # have visibly different lengths; random world offsets are absent.
            for layer in range(3):
                reach = 14. + layer * 24.
                width = 20. - layer * 6.
                for side in (-1., 1.):
                    position = origin + forward * reach + right * (side * width) + up * (5. + layer * 3.)
                    direction = forward + right * (side * .055)
                    self.fragment(position, direction, (.13 + layer * .025) * gain,
                                  (.23 + layer * .12) * gain, .20, 2.1)
        self.feed_serial += 1

    def _dense_release(self, stage, origin, direction, right, up, serial):
        self.release_stages[stage] += 1
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        if stage == 0:
            self._replace_native_at(origin, self.templates['muzzle'])
            size = (1.10, .61, .61) if self.dense_option == 'E10' else (1.35, .42, .42)
            self.pulse('muzzle', ('Wisps',), origin + direction * 8., rotation, size, .19, 1.75)
            self.pulse('muzzle', ('Sparks',), origin, rotation, (.55, .33, .33), .16, 2.3)
        elif stage == 1:
            if self.dense_option == 'E10':
                for side in (-1., 1.):
                    self.fragment(origin + direction * 42. + right * (side * 12.),
                                  direction + right * (side * .12), .17, .28, .19, 2.2)
            else:
                for side in (-1., 1.):
                    self.pulse('impact', ('SparkTrailHeads',), origin + direction * 30. + right * (side * 8.),
                               rotation, (.42, .16, .16), .14, 2.6)
        else:
            self.pulse('muzzle', ('Wisps',), origin + direction * 54., rotation,
                       (.95, .36, .36) if self.dense_option == 'E10' else (1.20, .29, .29), .16, 1.85)

    def arrow(self, arrow):
        direction, right, up = _basis(arrow.get_flight_direction())
        serial = len(self.arrows)
        self.last_dense_release = self.now()
        self.arrows.append({'arrow': arrow, 'born': self.now(), 'next_emit': self.now() + .035,
                            'serial': serial, 'emissions': 0, 'direction': direction, 'right': right, 'up': up})
        for particle in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            name = particle.get_name()
            if name not in ('ArrowTrail', 'RapidArrowFlow'):
                continue
            self.modified_components[name] += 1
            self.snapshots.append((particle, particle.is_visible(),
                particle.get_editor_property('relative_scale3d'),
                particle.get_editor_property('custom_time_dilation'), particle.get_material(0)))
            if name == 'ArrowTrail':
                width = .90 if self.dense_option == 'E10' else .78
                particle.set_world_scale3d(unreal.Vector(1., width, width))
            else:
                width = 1.05
                particle.set_world_scale3d(unreal.Vector(1., width, width))
                # The native muzzle Wisps material is a soft glow. Both new
                # previews require the inspected torn-flame age-erosion source.
                material = self.e7_native_flame
                particle.set_material(0, material)
                self._audit_binding(particle, 0, material, 'RapidArrowFlow_' + self.dense_option)
        origin = self.rig['skills']().get_arrow_origin()
        self._dense_release(0, origin, direction, right, up, serial)
        self._later(.033, self._dense_release, 1, origin, direction, right, up, serial)
        self._later(.067, self._dense_release, 2, origin, direction, right, up, serial)

    def _flight(self, row):
        arrow = row['arrow']
        if not _valid(arrow):
            return
        position = arrow.get_actor_location()
        direction, right, up = row['direction'], row['right'], row['up']
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        if self.dense_option == 'E10':
            # Keep the inspected erosion source and fixed bow-wing silhouette.
            # Repeated large Wisps were visibly soft yellow blobs in actual
            # e-final30/.57 captures; only the existing small folded tips remain.
            if row['emissions'] % 2 == 0:
                for side in (-1., 1.):
                    self.fragment(position - direction * 19. + right * (side * 11.),
                                  direction + right * (side * .09), .12, .20, .18, 2.2)
        else:
            self.pulse('muzzle', ('Wisps',), position - direction * 36.,
                       rotation, (1.20, .46, .46), .21, 1.6)
            if row['emissions'] % 2 == 0:
                self.pulse('impact', ('SparkTrailHeads',), position - direction * 16., rotation,
                           (.32, .13, .13), .12, 2.6)
        row['emissions'] += 1

    def hit(self, target, direction):
        forward, right, up = _basis(direction)
        point = target.get_actor_location()
        rotation = unreal.MathLibrary.make_rot_from_x(forward)
        self._replace_native_at(point, self.templates['impact'])
        self.hit_serial += 1
        self.pulse('impact', ('Sparks', 'SparkTrailHeads'), point, rotation,
                   (.60, .39, .39) if self.dense_option == 'E10' else (.68, .25, .25), .20, 2.25)
        if self.dense_option == 'E10':
            for side in (-1., 1.):
                self.fragment(point - forward * 8. + right * (side * 12.),
                              forward + right * (side * .30) + up * .08, .18, .27, .19, 2.15)
        else:
            for side in (-1., 0., 1.):
                self.fragment(point - forward * 5. + right * (side * 9.),
                              forward + right * (side * .18) + up * .04, .13, .22, .17, 2.35)
        # One extra final fine spark gives closure without another broad flash.
        if self.hit_serial == 6:
            self._later(.045, self.pulse, 'impact', ('Sparks',), point + forward * 10., rotation,
                        (.44, .28, .28), .15, 2.4)

    def update(self, started):
        if self.dense_started is not None:
            now = self.now()
            elapsed = now - self.dense_started
            if elapsed < 1.04 and now >= self.next_feed:
                self.next_feed = now + .145
                self._feed()
            self._update_mesh_silhouette()
        super().update(started)

    def close(self):
        if _valid(self.mesh_proxy):
            self.mesh_proxy.destroy_actor()
        self.mesh_proxy = None
        self.mesh_component, self.mesh_mid = None, None
        return super().close()


def sequence(rig):
    """Two real casts with equal-time captures, damage and lifecycle checks."""
    rows = []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in _selected():
        rig['switch']('countess')
        yield .10
        rig['switch']('sparrow')
        yield .55
        rig['case']('refined_' + option)
        targets = rig['layout']([(750, 0), (750, 350), (750, -350)])
        yield .20
        target = targets[0]
        initial = previous = rig['health'](target)
        stacks = rig['skills']().get_relentless_stacks(target)
        expected = sum(10. * (1. + min(stacks + index, 10) * .0175) for index in range(6))
        direction = target.get_actor_location() - rig['skills']().get_arrow_origin()
        direction, _, _ = _basis(direction)
        study_class = DenseStudy if option in DENSE_OPTIONS else Study
        study, seen, hits, captures = study_class(rig, option), set(), [], []
        started = now()
        try:
            if option in DENSE_OPTIONS:
                study.begin(target)
            rig['use']('E', target)
            _FRESH['_clip'](rig, option)
            moments = [.10, .30, .57, .90] if option in DENSE_OPTIONS else [.23, .47, .73]
            while now() - started < 1.60:
                elapsed = now() - started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    path = arrow.get_path_name()
                    if arrow.get_owner() == rig['pawn']() and path not in seen:
                        seen.add(path)
                        study.arrow(arrow)
                health = rig['health'](target)
                if health < previous - .01:
                    study.hit(target, direction)
                    hits.append({'elapsed': elapsed, 'damage': previous - health})
                previous = health
                study.update(started)
                if moments and elapsed >= moments[0]:
                    moment = moments.pop(0)
                    label = option + '_at_' + str(round(moment * 100))
                    rig['capture'](label)
                    captures.append({'label': label, 'elapsed': elapsed})
                yield 1 / rig['FPS']
            rig['finish_video_clip']()
            actual = initial - rig['health'](target)
            rig['check'](len(seen) == 6, option + ' observes six actual native E arrows')
            rig['check'](study.modified_components == {'ArrowTrail': 6, 'RapidArrowFlow': 6},
                         option + ' adjusts both actual PSCs on all six arrows')
            rig['check'](abs(actual - expected) < .03, option + ' preserves actual E damage and passive stacks')
            rig['check'](study.release_stages == [6, 6, 6], option + ' completes all three short release stages')
            rig['check'](len(captures) == (4 if option in DENSE_OPTIONS else 3), option + ' records equal-time detail frames')
            rig['recovered']()
            row = {'id': option, **DESIGNS[option], 'native_arrows': len(seen), 'hits': hits,
                   'actual_damage': actual, 'expected_damage': expected, 'screenshots': captures,
                   'release_stage_counts': study.release_stages,
                   'modified_component_counts': study.modified_components,
                   'temporary_particles_created': study.created,
                   'peak_active_particles': study.peak_particles,
                   'enabled_study_emitters': sorted(study.emitter_selections),
                   'material_bindings': study.material_bindings,
                   'full_white_flash_added': False, 'new_damage_sources': False,
                   'production_installed': False}
            if option in DENSE_OPTIONS:
                row['preparation_events'] = study.preparation_events
                row['bow_feed_pulses'] = study.feed_serial
                row['native_muzzle_and_impact_PSCs_replaced'] = len(study.replaced_native_particles)
                row['native_replacement_counts'] = study.native_replacement_counts
                row['source_alpha_age_erosion_preserved'] = True
                row['project_owned_mesh_reused_without_save'] = ENERGY_MESH
                row['mesh_silhouette_samples'] = study.mesh_samples
        finally:
            rig['finish_video_clip']()
            restored = study.close()
        remaining = [particle for particle in study.particle_refs
                     if _valid(particle) and particle.is_active()]
        rig['check'](not remaining, option + ' cleans every temporary study PSC')
        rig['check'](not study.events, option + ' clears all delayed release/impact actions')
        if option in DENSE_OPTIONS:
            mesh_remaining = [actor for actor in study.mesh_proxy_refs if _valid(actor)]
            rig['check'](not mesh_remaining, option + ' cleans its temporary mesh silhouette actor')
            row['temporary_mesh_actor_cleaned'] = not mesh_remaining
        row['surviving_native_components_restored'] = restored
        row['temporary_effects_cleaned'] = not remaining
        rows.append(row)
        yield .20
    result = {'passed': True, 'revision': 7, 'studies': rows, 'assets_saved_in_PIE': False,
              'source_pack_assets_changed': False, 'production_defaults_changed': False,
              'selection_required_for_production': True, 'visual_acceptance': 'pending actual capture review',
              'limitations': ['Python observes native firing/hit after the game tick, so overlays may lag one frame.',
                             'Particle counts are diagnostic values, not a GPU performance measurement.',
                             'Legacy E7r/E9r preserve native hit flashes; E10/E11 temporarily replace matching native muzzle/impact PSC visibility.',
                             'The new bow-wing silhouettes are source curved flame meshes, not an anatomical wing asset.']}
    _write(rig['OUT'], 'E-refined-studies.json', result)
