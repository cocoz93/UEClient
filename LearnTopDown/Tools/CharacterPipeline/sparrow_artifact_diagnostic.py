"""Read-only asset inspection and transient PIE isolation of reported visual artifacts."""
import json
import os
from pathlib import Path
import sys
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
job_file = qa / 'job.json'
job_file.write_text(json.dumps({'profile': str(root / 'Tools/CharacterPipeline/Profiles/sparrow.json'),
    'baseline': str(root / 'Saved/QA/CharacterPipeline/baseline-20261015-pose-final/baseline.json'),
    'output': str(qa), 'fps': int(os.environ['SPARROW_QA_FPS'])}), encoding='utf-8')
os.environ['CHARACTER_PIPELINE_JOB'] = str(job_file)
sys.path.insert(0, str(root / 'Tools/CharacterPipeline'))
sys.path.insert(0, str(root / 'Tools/CharacterPipeline/Suites'))
from sparrow_runtime import Runner
from character_switch import SwitchRunner
from sparrow_field_presentation import select_sparrow


def q_frames(rig, prefix):
    unreal.SystemLibrary.execute_console_command(rig.world, 'Sparrow.Skills.IgnoreCooldowns 1')
    target = rig.dummy(600)
    rig.aim_target(target)
    started = rig.now
    yield from rig.skill_key('Q', target.get_actor_location())
    for seconds in (0.15, 0.30, 0.45, 0.65):
        yield max(0.0, seconds - (rig.now - started))
        if seconds >= 0.30 and prefix != 'normal':
            fragment = 'P_ReleaseArrow' if prefix == 'without_release' else 'P_RainofArrowsProj'
            for actor in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.Actor):
                for particle in actor.get_components_by_class(unreal.ParticleSystemComponent):
                    template = particle.get_editor_property('template')
                    if template and fragment in template.get_path_name():
                        particle.deactivate()
                        particle.set_template(None)
            yield 1.0 / int(os.environ['SPARROW_QA_FPS'])
        rig.snapshot()
        yield rig.capture(prefix + '-q-' + str(round(seconds * 100)))
    yield rig.idle()
    yield 3.5


def normal_q(rig):
    rig.data['cloth_settings'] = {p: str(rig.mesh.get_editor_property(p)) for p in (
        'teleport_rotation_threshold', 'teleport_distance_threshold', 'reset_after_teleport')}
    mesh = unreal.load_asset('/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Aura_v1')
    rig.data['corona_mesh_materials'] = []
    for slot in mesh.get_editor_property('static_materials'):
        material = slot.get_editor_property('material_interface')
        rig.data['corona_mesh_materials'].append(material.get_path_name() if material else None)
    yield from q_frames(rig, 'normal')


def no_release_q(rig):
    yield from q_frames(rig, 'without_release')


def no_launch_q(rig):
    yield from q_frames(rig, 'without_launch')


class DiagnosticRunner(SwitchRunner):
    def __init__(self):
        Runner.__init__(self, 'sparrow_artifact_diagnostic', [('selection', select_sparrow),
            ('normal_q', normal_q), ('without_release_q', no_release_q), ('without_launch_q', no_launch_q)])
        self.selected_pawn = None
        self.report.update(asset_saves=False, temporary_PIE_component_changes_only=True)


runtime = DiagnosticRunner()
runtime.start()
