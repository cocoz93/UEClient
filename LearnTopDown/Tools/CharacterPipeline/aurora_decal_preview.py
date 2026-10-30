"""Floor decal look check: one decal actor per material in DECAL_MATERIALS (comma list) laid on the training room floor, each
seen from the game camera angle by its own scene capture. DECAL_RADIUS sets the decal radius (default 350). DECAL_WAIT = play
seconds before the capture (default 2; textures may still be at low streamed mips that early). DECAL_SCALARS = optional
"Name=value,..." set on a dynamic instance of every decal (e.g. Reveal=0.5 to see which end a sweep starts from).
The camera looks along world yaw 45 (screen up), screen right = yaw 135. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
MATERIALS = os.environ['DECAL_MATERIALS'].split(',')
RADIUS = float(os.environ.get('DECAL_RADIUS', '350'))
WAIT = float(os.environ.get('DECAL_WAIT', '2'))
SPACING = RADIUS * 2.4
state = {'phase': 'load', 'wall': time.monotonic()}
report = {'materials': MATERIALS, 'captures': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'decal-preview.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def stage(editor_world):
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + unreal.Vector(0, 0, -96)
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    for index, path in enumerate(MATERIALS):
        spot = center + right * ((index - (len(MATERIALS) - 1) / 2.0) * SPACING)
        tag = unreal.Name(f'decal_{index}')
        decal = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DecalActor, spot, unreal.Rotator(roll=0, pitch=-90, yaw=0))
        decal.set_editor_property('tags', [tag])
        component = decal.get_editor_property('decal')
        component.set_editor_property('decal_size', unreal.Vector(120, RADIUS, RADIUS))
        material = unreal.load_asset(path)
        if material:
            component.set_decal_material(material)
            scalars = [pair.split('=') for pair in os.environ.get('DECAL_SCALARS', '').split(',') if '=' in pair]
            if scalars:
                dynamic = component.create_dynamic_material_instance()
                for name, value in scalars:
                    dynamic.set_scalar_parameter_value(name.strip(), float(value))
        else:
            report.setdefault('missing', []).append(path)
        camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
            spot + unreal.Vector(0, 0, 100) - rotation.get_forward_vector() * (RADIUS * 3.2), rotation)
        camera.set_editor_property('tags', [tag])


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300 + WAIT:
            raise TimeoutError('decal preview timed out')
        if state['phase'] == 'load':
            stage(unreal.EditorLoadingAndSavingUtils.load_map(MAP))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'wait'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            return
        if unreal.GameplayStatics.get_time_seconds(world) < WAIT:
            return
        pawn.set_actor_hidden_in_game(True)
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D):
            tags = [str(t) for t in actor.get_editor_property('tags')]
            if not tags or not tags[0].startswith('decal_'):
                continue
            capture = actor.get_editor_property('capture_component2d')
            capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            capture.set_editor_property('fov_angle', 40)
            capture.set_editor_property('texture_target',
                unreal.RenderingLibrary.create_render_target2d(world, 480, 480, unreal.TextureRenderTargetFormat.RTF_RGBA8))
            capture.capture_scene()
            file = f'{tags[0]}.png'
            unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
            report['captures'].append(file)
        finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
