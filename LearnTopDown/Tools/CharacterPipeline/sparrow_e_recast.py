"""Read-only source audit, then one authored-source E recast candidate.

This helper owns no production code or source-pack assets. Its author entry
loads ten narrowly selected original ParticleSystems and reads their native
emitters/materials. It does not save, duplicate, compile or replace any asset.
"""
import json
import math
import os
from pathlib import Path
import re
import traceback

import unreal


SPARROW_BASE = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/'
CANDIDATES = {
    'arrow_complete': SPARROW_BASE + 'Ultimate/FX/P_Arrow_Ultimate',
    'arrow_ultimate': SPARROW_BASE + 'Ultimate/FX/P_Sparrow_UltArrow',
    'arrow_primary': SPARROW_BASE + 'Primary/FX/P_Sparrow_PrimaryAttack',
    'charge_projectile': SPARROW_BASE + 'DrawABead/FX/P_Sparrow_RMB',
    'release': SPARROW_BASE + 'Primary/FX/P_SparrowPrimaryMuzzleFlash',
    'impact': SPARROW_BASE + 'Ultimate/FX/P_Sparrow_UltHit',
    'burst': SPARROW_BASE + 'Ultimate/FX/P_Sparrow_Burst',
    'bow_reaction': SPARROW_BASE + 'Ultimate/FX/P_SparrowBuff',
    'gideon_projectile': '/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_Projectile',
    'serath_cast': '/Game/ParagonSerath/FX/Particles/Abilities/Fury/FX/P_Fury_CastingHand',
}
ARROW_SOURCE = CANDIDATES['arrow_ultimate']
ARROW_KEEP = ('MeshCoronaLarge', 'SparksTrailing')
ARROW_EMITTERS = ('RibbonTrail', 'DebugRibbon', 'TrailsLinger', 'Flare_Big', 'Flare', 'Sparks',
                  'SparksTrailing', 'Refraction', 'Particle Emitter', 'MeshCoronaLarge', 'AirglowFlash', 'Airglow')
EXISTING_NATIVE = 'Saved/QA/CharacterPipeline/sparrow-texture-restore-20261023/asset-audit/sparrow-native-inventory.json'


def _write(out, name, value):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _paths(value):
    paths = set()
    if isinstance(value, str):
        paths.update(re.findall(r"(/Game/[^'\s,\)\"]+)", value))
    elif isinstance(value, dict):
        for child in value.values():
            paths.update(_paths(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            paths.update(_paths(child))
    return paths


def _emitter_summary(emitter):
    lods = emitter.get('lods', [])
    lod = lods[0] if lods else {}
    required = lod.get('required', {}).get('properties', {})
    type_data = lod.get('type_data', {})
    modules = lod.get('modules', [])
    distributions = []
    for module in modules:
        properties = module.get('properties', {})
        selected = {key: properties[key] for key in (
            'Lifetime', 'StartSize', 'StartVelocity', 'StartColor', 'StartAlpha',
            'ColorOverLife', 'AlphaOverLife', 'ColorScaleOverLife', 'AlphaScaleOverLife',
            'DynamicParams', 'DynamicParameters', 'MeshMaterials', 'SourceLocations',
            'SkelMeshActorParamName', 'SourceType', 'SourceNames') if key in properties}
        if selected:
            distributions.append({'class': module.get('class'), 'properties': selected})
    return {'index': emitter.get('index'),
            'name': emitter.get('properties', {}).get('EmitterName'),
            'lod0_enabled': lod.get('enabled'),
            'required_material': required.get('Material'),
            'screen_alignment': required.get('ScreenAlignment'),
            'local_space_raw': required.get('bUseLocalSpace'),
            'duration_raw': required.get('EmitterDuration'), 'loops_raw': required.get('EmitterLoops'),
            'subimages': [required.get('SubImages_Horizontal'), required.get('SubImages_Vertical')],
            'named_material_overrides': required.get('NamedMaterialOverrides'),
            'type_data_class': type_data.get('class'),
            'type_data_properties': type_data.get('properties', {}),
            'spawn': lod.get('spawn', {}).get('properties', {}),
            'module_classes': [module.get('class') for module in modules],
            'requires_bone_source': any('BoneSocket' in module.get('class', '') for module in modules),
            'distributions': distributions}


def _cross_pack_read(asset):
    """Python-only read where the existing native Sparrow allowlist ends."""
    row = {'path': asset.get_path_name(), 'class': asset.get_class().get_name(),
           'native_dump_used': False, 'objects': [], 'unavailable_properties': []}
    fields = ('emitter_name', 'lod_levels', 'enabled', 'material', 'emitter_duration',
              'emitter_loops', 'screen_alignment', 'use_local_space', 'sub_images_horizontal',
              'sub_images_vertical', 'mesh', 'rate', 'rate_scale', 'burst_list', 'lifetime',
              'start_size', 'start_velocity', 'start_color', 'start_alpha', 'color_scale_over_life',
              'alpha_scale_over_life', 'dynamic_params', 'source_locations', 'skel_mesh_actor_param_name')
    prefix = asset.get_path_name() + ':'
    for obj in unreal.ObjectIterator(unreal.Object):
        # ObjectIterator also exposes reflected UClass wrappers as Python
        # classes. Their get_path_name is an unbound method, not this module.
        if isinstance(obj, type):
            continue
        try:
            object_path = obj.get_path_name()
        except (TypeError, RuntimeError):
            continue
        if not object_path.startswith(prefix):
            continue
        kind = obj.get_class().get_name()
        if not any(tag in kind for tag in ('ParticleEmitter', 'ParticleSpriteEmitter', 'ParticleModule', 'ParticleLODLevel')):
            continue
        entry = {'path': object_path, 'class': kind, 'properties': {}}
        for field in fields:
            try:
                value = obj.get_editor_property(field)
            except Exception:
                continue
            entry['properties'][field] = value.get_path_name() if isinstance(value, unreal.Object) else str(value)
        row['objects'].append(entry)
    row['limitation'] = 'Protected fields omitted; no native allowlist expansion and no inferred values.'
    return row


def _material_read(material):
    lib = unreal.MaterialEditingLibrary
    base = material.get_base_material()
    row = {'path': material.get_path_name(), 'base': base.get_path_name(),
           'class': material.get_class().get_name(), 'scalars': {}, 'vectors': {},
           'textures': [], 'expression_classes': [], 'properties': {}}
    instance = isinstance(material, unreal.MaterialInstanceConstant)
    for field in ('blend_mode', 'shading_model', 'two_sided'):
        row['properties'][field] = str(base.get_editor_property(field))
    for name in lib.get_scalar_parameter_names(material):
        try:
            row['scalars'][str(name)] = (lib.get_material_instance_scalar_parameter_value(material, name)
                                         if instance else lib.get_material_default_scalar_parameter_value(base, name))
        except Exception as error:
            row['scalars'][str(name)] = {'error': str(error)}
    for name in lib.get_vector_parameter_names(material):
        try:
            color = (lib.get_material_instance_vector_parameter_value(material, name)
                     if instance else lib.get_material_default_vector_parameter_value(base, name))
            row['vectors'][str(name)] = [color.r, color.g, color.b, color.a]
        except Exception as error:
            row['vectors'][str(name)] = {'error': str(error)}
    row['textures'] = [texture.get_path_name() for texture in lib.get_material_used_textures(base)]
    expressions = lib.get_material_expressions(base)
    row['expression_classes'] = sorted({node.get_class().get_name() for node in expressions})
    row['outputs'] = {}
    for name, prop in (('opacity', unreal.MaterialProperty.MP_OPACITY),
                       ('emissive', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                       ('world_position_offset', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)):
        source = lib.get_material_property_input_node(base, prop)
        row['outputs'][name] = source.get_class().get_name() if source else None
    return row


def author(out):
    """Reuse the existing eight-source native audit unless a full read is requested."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(unreal.Paths.project_dir()).resolve()
    cached_file = Path(os.environ.get('SPARROW_E_RECAST_NATIVE_SOURCE', str(root / EXISTING_NATIVE)))
    if os.environ.get('SPARROW_E_RECAST_FULL_AUDIT') != '1' and cached_file.is_file():
        native = json.loads(cached_file.read_text(encoding='utf-8-sig'))
        entry = next(asset for asset in native['assets'] if asset['path'].split('.')[0] == ARROW_SOURCE)
        names = {emitter['properties']['EmitterName'] for emitter in entry.get('emitters', [])}
        assert names == set(ARROW_EMITTERS), sorted(names)
        assert isinstance(unreal.load_asset(ARROW_SOURCE), unreal.ParticleSystem)
        report = {'passed': True, 'revision': 2, 'read_only': True, 'assets_saved': False,
                  'native_source_reused': str(cached_file), 'preferred_for_visual_audition': ARROW_SOURCE,
                  'enabled_emitters': list(ARROW_KEEP),
                  'projectile_scale': [1.05, 1.89, 1.89],
                  'release_aura_seconds': .14, 'release_aura_visual_time_scale': 3.8,
                  'source_emitter_summaries': [_emitter_summary(emitter) for emitter in entry['emitters']],
                  'source_color_unchanged': True, 'source_material_and_dynamic_parameters_unchanged': True,
                  'new_materials_or_particle_assets': False, 'production_E_changed': False,
                  'selection_status': 'One actual-game gold aura arrow candidate; visual review pending.'}
        _write(out, 'E-recast-selected-source.json', report)
        return {'passed': True, 'read_only': True, 'assets_saved': False,
                'native_audit_reused': True, 'report': str(out / 'E-recast-selected-source.json')}
    assets = {key: unreal.load_asset(path) for key, path in CANDIDATES.items()}
    for key, asset in assets.items():
        assert isinstance(asset, unreal.ParticleSystem), (key, CANDIDATES[key], asset)
    native_paths = [path for path in CANDIDATES.values() if path.startswith('/Game/ParagonSparrow/')]
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + out.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + path + '"' for path in native_paths))
    native_file = out / 'sparrow-native-inventory.json'
    native = json.loads(native_file.read_text(encoding='utf-8-sig'))
    assert native.get('passed') and len(native.get('assets', [])) == len(native_paths), native.get('passed')
    summaries = []
    for asset in native['assets']:
        summaries.append({'path': asset['path'], 'class': asset.get('class'),
                          'emitters': [_emitter_summary(emitter) for emitter in asset.get('emitters', [])]})
    cross = [_cross_pack_read(assets[key]) for key in ('gideon_projectile', 'serath_cast')]
    material_paths = _paths(native) | _paths(cross)
    materials = []
    for path in sorted(path for path in material_paths if '/Materials/' in path):
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.MaterialInterface):
            materials.append(_material_read(asset))
    report = {'passed': True, 'read_only': True, 'assets_saved': False, 'assets_compiled': False,
              'source_pack_changes': False, 'candidate_count': len(CANDIDATES),
              'candidates': CANDIDATES, 'native_source': str(native_file),
              'sparrow_emitter_summaries': summaries, 'cross_pack_python_reads': cross,
              'material_reads': materials,
              'preferred_for_visual_audition': ARROW_SOURCE,
              'selection_status': 'One actual-game gold aura arrow candidate; visual review pending.',
              'offline_exclusions': {
                  'P_ReleaseArrow': 'Serialized dependencies are camera mesh/pulse material, not a visible flying arrow.',
                  'Serath P_AngelTrails': 'Serialized AnimTrail and BoneSocket dependencies; not a standalone projectile.',
                  'Aurora P_Aurora_Primary_Trail': 'Serialized AnimTrail dependency; not a standalone projectile.',
                  'Gideon P_Gideon_Primary_Projectile': 'Contains FlameBall and SmokeTrail; inspect spline detail only if the authored Sparrow arrow fails.'}}
    _write(out, 'E-recast-source-audit.json', report)
    return {'passed': True, 'read_only': True, 'assets_saved': False,
            'candidate_count': len(CANDIDATES), 'report': str(out / 'E-recast-source-audit.json')}


def _valid(value):
    return value is not None and unreal.SystemLibrary.is_valid(value)


class Recast:
    """Use the complete source emitter chain on each real E projectile PSC."""
    def __init__(self, rig):
        self.rig = rig
        self.source = unreal.load_asset(ARROW_SOURCE)
        assert isinstance(self.source, unreal.ParticleSystem)
        self.snapshots, self.modified, self.samples = [], 0, []
        self.restore_failures = []
        self.releases, self.release_refs = [], []
        self.release_created, self.release_halted = 0, 0

    def _release(self, direction):
        origin = self.rig['skills']().get_arrow_origin() + direction * 8.
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.source, origin, rotation,
            unreal.Vector(.70, .35, .35), False, unreal.PSCPoolMethod.NONE, False)
        assert particle
        particle.set_editor_property('component_tags', [unreal.Name('SparrowERecastRelease')])
        # The original .55-second local-space aura is compressed into .14 sec.
        # Particle color, mesh material, DP and age erosion stay source-authored.
        particle.set_editor_property('custom_time_dilation', 3.8)
        particle.activate(True)
        for name in ARROW_EMITTERS:
            particle.set_emitter_enable(name, name == 'MeshCoronaLarge')
        self.releases.append({'particle': particle, 'born': unreal.GameplayStatics.get_time_seconds(self.rig['world']()),
                              'direction': direction, 'rotation': rotation, 'halted': False})
        self.release_refs.append(particle)
        self.release_created += 1

    def update(self):
        now = unreal.GameplayStatics.get_time_seconds(self.rig['world']())
        alive = []
        for row in self.releases:
            particle = row['particle']
            if not _valid(particle):
                continue
            age = now - row['born']
            if age >= .14:
                particle.deactivate()
                particle.destroy_component(particle)
                continue
            # SetEmitterEnable only halts new spawning. The first frame's
            # authored particles continue their complete compressed lifetime.
            if not row['halted'] and age > .001:
                particle.set_emitter_enable('MeshCoronaLarge', False)
                row['halted'] = True
                self.release_halted += 1
            phase = max(0., min(1., age / .14))
            envelope = math.sin(phase * math.pi)
            particle.set_world_location(self.rig['skills']().get_arrow_origin() + row['direction'] * 8., False, False)
            particle.set_world_rotation(row['rotation'], False, False)
            particle.set_world_scale3d(unreal.Vector(.70 + .35 * envelope,
                                                    .35 + 1.95 * envelope, .35 + 1.95 * envelope))
            alive.append(row)
        self.releases = alive

    def arrow(self, arrow):
        components = arrow.get_components_by_class(unreal.ParticleSystemComponent)
        flow = next((component for component in components if component.get_name() == 'RapidArrowFlow'), None)
        assert flow, arrow.get_path_name()
        self.snapshots.append({'component': flow, 'template': flow.get_editor_property('template'),
                               'scale': flow.get_editor_property('relative_scale3d'),
                               'speed': flow.get_editor_property('custom_time_dilation'),
                               'visible': flow.is_visible(),
                               'materials': [flow.get_material(index) for index in range(flow.get_num_materials())]})
        # The component is already parented to the real arrow root. SetTemplate
        # rebuilds its emitter instances and keeps the original source's mesh
        # material, ParticleColor, DynamicParameter and local-space behavior.
        # The narrow native ArrowTrail remains untouched as a directional core.
        flow.set_template(self.source)
        flow.set_relative_scale3d(unreal.Vector(1.05, 1.89, 1.89))
        flow.set_editor_property('custom_time_dilation', 1.)
        flow.activate(True)
        for name in ARROW_EMITTERS:
            flow.set_emitter_enable(name, name in ARROW_KEEP)
        flow.set_visibility(True)
        self.modified += 1
        self.samples.append({'arrow': arrow.get_path_name(), 'component': flow.get_path_name(),
                             'actual_template': flow.get_editor_property('template').get_path_name(),
                             'enabled_emitters': list(ARROW_KEEP), 'relative_scale': [1.05, 1.89, 1.89],
                             'original_mesh_module_material': '/Game/ParagonSparrow/FX/Materials/Heroes/Sparrow/Abilities/M_Arrow_Aura4',
                             'source_mesh': '/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Aura_v1',
                             'source_mesh_particle_rgb': [100., 80., 20.], 'source_mesh_particle_alpha': .25,
                             'source_dynamic_parameters_preserved': ['RandX', 'RandY', 'Refraction', 'Param4']})
        self._release(arrow.get_flight_direction())

    def close(self):
        for row in self.releases:
            particle = row['particle']
            if _valid(particle):
                particle.deactivate()
                particle.destroy_component(particle)
        self.releases.clear()
        restored = 0
        for row in self.snapshots:
            component = row['component']
            if not _valid(component):
                continue
            component.set_template(row['template'])
            component.set_relative_scale3d(row['scale'])
            component.set_editor_property('custom_time_dilation', row['speed'])
            for index, material in enumerate(row['materials']):
                component.set_material(index, material)
            component.set_visibility(row['visible'])
            if component.get_editor_property('template') != row['template'] or component.is_visible() != row['visible']:
                self.restore_failures.append(component.get_path_name())
            restored += 1
        self.snapshots.clear()
        return restored


def sequence(rig):
    """One short actual E cast; no alternate concepts or broad regression."""
    rig['switch']('countess')
    yield .10
    rig['switch']('sparrow')
    yield .55
    rig['case']('E_recast_authored_gold_arrow')
    targets = rig['layout']([(750, 0), (750, 350), (750, -350)])
    yield .20
    target = targets[0]
    start_health = previous = rig['health'](target)
    stacks = rig['skills']().get_relentless_stacks(target)
    expected = sum(10. * (1. + min(stacks + index, 10) * .0175) for index in range(6))
    study, seen, hits, captures = Recast(rig), set(), [], []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    started = now()
    try:
        rig['use']('E', target)
        if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
            rig['STATE']['video_clip'] = {'case': 'E_recast', 'prefix': 'E_recast_video',
                                         'cast_time': started, 'frame_times': []}
        moments = [.23, .43, .63, .96]
        while now() - started < 1.65:
            elapsed = now() - started
            for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                path = arrow.get_path_name()
                if arrow.get_owner() == rig['pawn']() and path not in seen:
                    seen.add(path)
                    study.arrow(arrow)
            health = rig['health'](target)
            if health < previous - .01:
                hits.append({'elapsed': elapsed, 'damage': previous - health})
            previous = health
            study.update()
            if moments and elapsed >= moments[0]:
                requested = moments.pop(0)
                label = 'E_recast_at_' + str(round(requested * 100))
                rig['capture'](label)
                captures.append({'label': label, 'elapsed': elapsed})
            yield 1 / rig['FPS']
        rig['finish_video_clip']()
        actual = start_health - rig['health'](target)
        rig['check'](len(seen) == 6, 'E recast observes six actual native arrows')
        rig['check'](study.modified == 6, 'E recast reaches each actual native RapidArrowFlow component')
        rig['check'](abs(actual - expected) < .03, 'E recast preserves actual damage and existing passive stacks')
        rig['check'](study.release_created == 6 and study.release_halted == 6,
                     'E recast completes six short source-authored bow aura pulses')
        rig['recovered']()
        report = {'passed': True, 'revision': 2, 'candidate_count': 1, 'preview_only': True,
                  'source': ARROW_SOURCE, 'enabled_source_emitters': list(ARROW_KEEP),
                  'native_arrows': len(seen), 'actual_damage': actual, 'expected_damage': expected,
                  'actual_hits': hits, 'screenshots': captures, 'component_samples': study.samples,
                  'native_arrow_direction_core_unchanged': True, 'native_bow_reaction_unchanged': True,
                  'short_bow_aura_addition': {'source': ARROW_SOURCE, 'emitter': 'MeshCoronaLarge',
                                             'count': study.release_created, 'seconds': .14,
                                             'source_time_scale': 3.8, 'follows_current_bow_origin': True},
                  'native_target_impact_unchanged': True, 'source_color_and_material_graph_unchanged': True,
                  'source_pack_assets_saved': False, 'production_E_changed': False,
                  'new_particle_components_created': study.release_created, 'new_mesh_actors_created': 0,
                  'visual_review': 'Pending actual 30fps capture review; no visual quality claim.'}
    finally:
        rig['finish_video_clip']()
        restored = study.close()
    rig['check'](not study.restore_failures, 'E recast restores any surviving native component template and visibility')
    remaining_releases = [particle for particle in study.release_refs if _valid(particle) and particle.is_active()]
    rig['check'](not remaining_releases, 'E recast removes all short bow aura PSCs')
    report['surviving_native_components_restored'] = restored
    report['surviving_component_restore_failures'] = study.restore_failures
    report['short_bow_auras_cleaned'] = not remaining_releases
    _write(rig['OUT'], 'E-recast-studies.json', report)


if __name__ == '__main__':
    root = Path(unreal.Paths.project_dir()).resolve()
    output = Path(os.environ.get('SPARROW_E_RECAST_OUT', os.environ.get(
        'SPARROW_QA_OUTPUT', str(root / 'Saved/QA/CharacterPipeline/sparrow-e-recast-20261023/asset-audit')))).resolve()
    try:
        author(output)
    except Exception:
        _write(output, 'E-recast-source-audit-error.json', {'passed': False, 'error': traceback.format_exc(),
                                                         'read_only': True, 'assets_saved': False})
        unreal.log_error(traceback.format_exc())
    finally:
        unreal.SystemLibrary.execute_console_command(None, 'QUIT_EDITOR')
