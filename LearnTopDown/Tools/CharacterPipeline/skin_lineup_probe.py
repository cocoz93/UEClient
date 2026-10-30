"""Read-only: front captures of every skin mesh of one Paragon hero (SKIN_HERO), to pick a skin by eye. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
# 영웅 이름은 환경 변수 SKIN_HERO(기본 Gideon). 기본 메시 + Skins/*/Meshes 의 스킨 메시를 파일에서 찾는다.
NAME = os.environ.get('SKIN_HERO', 'Gideon')
HERO = f'/Game/Paragon{NAME}/Characters/Heroes/{NAME}'
_disk = Path(unreal.Paths.project_dir()).resolve() / f'Content/Paragon{NAME}/Characters/Heroes/{NAME}'
MESHES = {'base': f'{HERO}/Meshes/{NAME}'}
for _file in sorted(_disk.glob('Skins/*/Meshes/*.uasset')):
    if 'PhysMat' not in _file.stem and 'Physics' not in _file.stem and 'Cloth' not in _file.stem:
        # 이름순으로 본 메시(예: Aurora_GlacialEmpress)가 먼저 오므로 뒤의 _RigidBody 등이 덮어쓰지 않게 한다.
        MESHES.setdefault(_file.parent.parent.name.lower(), f'{HERO}/Skins/{_file.parent.parent.name}/Meshes/{_file.stem}')
POSE = HERO + '/Animations/Idle'
# 원본 시험 맵의 기존 배치 옆 바닥에 한 줄로 세운다. Paragon 메시는 +Y를 보므로 180° 돌려 해가 비추는 -Y 쪽을 보게 한다.
ORIGIN = unreal.Vector(800, 0, 0)
state = {'phase': 'spawn', 'mark': 0.0, 'wall': time.monotonic(), 'actors': {}}
report = {'captures': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    report['passed'] = error is None
    report['error'] = error
    (qa / 'skins.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 400:
            raise TimeoutError('skin lineup timed out')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if state['phase'] == 'spawn':
            pose = unreal.load_asset(POSE)
            # 스킨 메시 폴더에 물리 에셋 등이 섞여 있으므로 스켈레탈 메시만 세운다.
            meshes = [(name, unreal.load_asset(path)) for name, path in MESHES.items()]
            meshes = [(name, mesh) for name, mesh in meshes if isinstance(mesh, unreal.SkeletalMesh)]
            for index, (name, mesh) in enumerate(meshes):
                actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor,
                    ORIGIN + unreal.Vector(index * 600, 0, 0), unreal.Rotator(roll=0, pitch=0, yaw=180))
                component = actor.get_editor_property('skeletal_mesh_component')
                component.set_skeletal_mesh_asset(mesh)
                component.set_update_animation_in_editor(True)
                if pose:
                    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                    component.play_animation(pose, True)
                component.prestream_textures(30, True)
                state['actors'][name] = actor
            state.update(phase='settle', mark=time.monotonic())
            return
        if time.monotonic() - state['mark'] < 50:
            return
        target = unreal.RenderingLibrary.create_render_target2d(world, 768, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8)
        rotation = unreal.Rotator(roll=0, pitch=-5, yaw=90)
        for name, actor in state['actors'].items():
            center = actor.get_actor_location() + unreal.Vector(0, 0, 110)
            camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
                center - rotation.get_forward_vector() * 420, rotation)
            capture = camera.get_editor_property('capture_component2d')
            capture.set_editor_property('texture_target', target)
            capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            capture.set_editor_property('fov_angle', 40)
            capture.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, target, str(qa), name + '.png')
            report['captures'].append({'skin': name, 'file': str(qa / (name + '.png')), 'exists': (qa / (name + '.png')).is_file()})
            camera.destroy_actor()
        finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


unreal.EditorLoadingAndSavingUtils.load_map(HERO + '/AnimationTestMap')
handle = unreal.register_slate_post_tick_callback(tick)
