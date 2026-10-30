"""Small real-PIE check for the tower map and the shared map selector.

The owning editor session calls start(). No editor launch, asset save, or native
change occurs here. Button delegates exercise the installed Blueprint handlers;
physical mouse routing remains a separate visual/UI acceptance check.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import time
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
TRAINING = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
TOWER = '/Game/TopDown/TrialTower/Maps/Lvl_TrialTower'
WIDGET_CLASS = '/Game/TopDown/TrialTower/UI/WBP_MapSelector.WBP_MapSelector_C'


class Until:
    def __init__(self, predicate, seconds, label):
        self.predicate, self.seconds, self.label = predicate, seconds, label


class Runner:
    def __init__(self, output):
        self.out = Path(output)
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / 'screenshots').mkdir(exist_ok=True)
        self.handle = None
        self.started = time.monotonic()
        self.phase = 'nav'
        self.waiting = None
        self.widget_class = unreal.load_class(None, WIDGET_CLASS)
        if not self.widget_class:
            raise RuntimeError('Map selector class has not been installed')
        self.report = {
            'passed': False, 'complete': False, 'checks': [], 'screenshots': [],
            'input': 'existing controller input hooks and actual UMG OnClicked delegates',
            'physical_pointer_routing_tested': False, 'scene_changes_saved': False,
            'visual_acceptance': 'pending_image_review', 'packaged_build_tested': False,
        }

    def write(self):
        (self.out / 'qa-play.json').write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding='utf-8')

    def check(self, condition, label, fatal=False):
        self.report['checks'].append({'passed': bool(condition), 'label': label})
        self.write()
        if fatal and not condition:
            raise AssertionError(label)
        return bool(condition)

    def world(self):
        return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()

    def pawn(self):
        return unreal.GameplayStatics.get_player_character(self.world(), 0)

    def controller(self):
        return unreal.GameplayStatics.get_player_controller(self.world(), 0)

    def console(self, command):
        unreal.SystemLibrary.execute_console_command(self.world(), command)

    def map_name(self):
        world = self.world()
        return str(unreal.GameplayStatics.get_current_level_name(world, True)) if world else ''

    def ready(self, expected):
        world = self.world()
        if not world or self.map_name() != expected:
            return False
        pawn = self.pawn()
        return bool(pawn and self.controller() and pawn.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance())

    def widget(self):
        widgets = unreal.WidgetLibrary.get_all_widgets_of_class(self.world(), self.widget_class, True)
        self.check(len(widgets) == 1, 'exactly one map selector exists on current map', True)
        return widgets[0]

    def control(self, name):
        if name == 'TravelPanel':
            # The authored Border retains native bIsVariable=false. Resolve it
            # through the real hierarchy rather than assuming a BP member.
            return self.widget().get_editor_property('GoTraining').get_parent().get_parent()
        return self.widget().get_editor_property(name)

    def click(self, name):
        button = self.control(name)
        self.check(button is not None and button.get_is_enabled(), name + ' is a usable UMG button', True)
        button.get_editor_property('on_clicked').broadcast()

    def press(self, key):
        self.console('CountessInputQA.Key ' + key + ' Press')

    def release(self, key):
        self.console('CountessInputQA.Key ' + key + ' Release')

    def point(self, x, y):
        z = self.pawn().get_actor_location().z
        projected = unreal.NavigationSystemV1.project_point_to_navigation(self.world(), unreal.Vector(x,y,z),
            nav_data=None, filter_class=None, query_extent=unreal.Vector(100,100,250))
        if isinstance(projected, tuple):
            if any(isinstance(item,bool) and not item for item in projected):
                projected = None
            else:
                projected = next((item for item in projected if isinstance(item,unreal.Vector)), None)
        self.check(isinstance(projected, unreal.Vector), 'navigation projects a walkable goal at ' + str((x,y)), True)
        return projected

    def capture(self, name, ui=False):
        path = self.out / 'screenshots' / (name + '.png')
        self.console('CharacterPipeline.OutputDirectory ' + str(self.out))
        if ui:
            self.console('Shot -showui -nosuffix filename="' + path.as_posix() + '"')
        else:
            self.console('CharacterVisualQA.Capture ' + name)
        yield Until(lambda: path.exists() and path.stat().st_size > 100, 12, 'screenshot created: ' + name)
        if path.exists():
            data = path.read_bytes()
            complete = data[:8] == b'\x89PNG\r\n\x1a\n' and data[-8:-4] == b'IEND'
            self.check(complete, 'complete PNG capture: ' + name)
            width,height = struct.unpack('>II',data[16:24]) if complete else (0,0)
            self.report['screenshots'].append({'name':name,'path':str(path),'width':width,'height':height,'includes_slate_ui':ui})
            self.write()

    def camera(self):
        pawn = self.pawn()
        arm = pawn.get_component_by_class(unreal.SpringArmComponent)
        camera = pawn.get_component_by_class(unreal.CameraComponent)
        rotation = arm.get_editor_property('relative_rotation')
        actual = [arm.get_editor_property('target_arm_length'), rotation.pitch, rotation.yaw, camera.get_editor_property('field_of_view')]
        self.check(all(abs(a-b)<.01 for a,b in zip(actual,[2000,-50,45,55])), 'camera remains 2000cm / pitch -50 / yaw45 / FOV55')
        self.report['camera'] = actual

    def move(self,x,y):
        goal = self.point(x,y)
        self.console(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        # A click queues both events for the next input frame. Holding across
        # Slate frames in a visible editor allows the real pointer to replace
        # this fixture's viewport cursor cache and steer the held movement.
        self.console(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        yield Until(lambda: math.hypot(self.pawn().get_actor_location().x-goal.x,self.pawn().get_actor_location().y-goal.y)<65,
                    10, 'right-click movement reaches ' + str((x,y)))
        movement=self.pawn().get_component_by_class(unreal.CharacterMovementComponent)
        self.check(not movement.is_falling(), 'pawn stands on continuous collision after movement')
        yield 1.2

    def entry_paths(self):
        start=self.pawn().get_actor_location()
        rows=[]
        for x,y in [(0,1900),(1900,0),(0,-1900),(-1900,0)]:
            goal=self.point(x,y)
            path=unreal.NavigationSystemV1.find_path_to_location_synchronously(
                self.world(),start,goal,pathfinding_context=self.pawn(),filter_class=None)
            valid=path is not None and path.is_valid() and not path.is_partial()
            self.check(valid,'unbroken navigation route connects playable floor to entry '+str((x,y)))
            rows.append({'goal':[x,y],'valid':bool(path and path.is_valid()),
                         'partial':bool(path and path.is_partial())})
        self.report['entry_routes']=rows
        self.write()

    def sequence(self):
        yield 2.0
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.console('CharacterPipeline.OutputDirectory ' + str(self.out))
        self.check(not self.control('GoTraining').get_is_enabled(), 'current training map is disabled in selector')
        self.click('ToggleTravel')
        yield .3
        self.check(self.control('TravelPanel').get_visibility() == unreal.SlateVisibility.VISIBLE, 'map panel opens')
        yield from self.capture('01-training-map-selector', True)
        self.click('GoTower')
        yield Until(lambda:self.ready('Lvl_TrialTower'),60,'training UI loads tower and a playable pawn')
        yield 2.5
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.check(not self.control('GoTower').get_is_enabled(),'current tower map is disabled in selector')
        self.check(self.control('TravelPanel').get_visibility() == unreal.SlateVisibility.COLLAPSED,'new map begins with compact map UI')
        self.check(isinstance(self.controller().get_hud(),unreal.CharacterSkillHUD),'existing skill HUD survives new controller BP')
        self.camera()
        yield from self.capture('02-tower-arrival')
        self.entry_paths()
        yield from self.move(400,150)
        for key,expected in [('Two','BP_SparrowCharacter_C'),('Three','GideonCharacter'),('Four','AuroraCharacter'),('One','BP_CountessCharacter_C')]:
            self.press(key)
            yield .08
            self.release(key)
            yield Until(lambda expected=expected:self.pawn().get_class().get_name()==expected,12,'character selection '+key+' remains functional')
            yield .3
        self.press('Four')
        yield .08
        self.release('Four')
        yield Until(lambda:self.pawn().get_class().get_name()=='AuroraCharacter',12,'Aurora selected for ice readability')
        yield 1.0
        self.camera()
        yield from self.move(650,550)
        yield from self.capture('03-tower-edge-game-camera')
        yield from self.move(0,0)
        aim = self.point(360,240)
        self.console(f'CountessComboQA.Mouse Move Left {aim.x} {aim.y} {aim.z}')
        self.press('R')
        yield .08
        self.release('R')
        self.check(self.pawn().get_aurora_skills().is_casting(),'Aurora ice field accepts ordinary R binding')
        yield .8
        yield from self.capture('04-tower-ice-skill')
        yield 3.0
        self.click('ToggleTravel')
        yield .3
        yield from self.capture('05-tower-map-selector',True)
        self.click('CloseTravel')
        yield .2
        self.check(self.control('TravelPanel').get_visibility()==unreal.SlateVisibility.COLLAPSED,'close returns to compact UI')
        self.click('ToggleTravel')
        yield .2
        self.click('GoTraining')
        yield Until(lambda:self.ready('Lvl_DarkTrainingRoom'),60,'tower UI returns to training and a playable pawn')
        yield 2.5
        self.check(self.control('GoTower').get_is_enabled(),'tower can be entered again after a full round trip')
        self.check(self.control('TravelPanel').get_visibility()==unreal.SlateVisibility.COLLAPSED,'returning map begins with compact UI')
        self.camera()

    def begin(self):
        if self.world():
            raise RuntimeError('Stop the current PIE explicitly before this independent QA run')
        editor_world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        # Reloading an already-open training map through this API can leave its
        # generated navigation empty in UE 5.8. Preserve the loaded world.
        if not editor_world or editor_world.get_path_name().split('.',1)[0] != TRAINING:
            if not unreal.EditorLoadingAndSavingUtils.load_map(TRAINING):
                raise RuntimeError('Could not load the existing training map')
        self.handle=unreal.register_slate_post_tick_callback(self.tick)
        self.write()
        return self

    def tick(self,delta):
        try:
            now=time.monotonic()
            if now-self.started>300:
                raise TimeoutError('Trial tower QA exceeded 300 wall seconds')
            if self.phase=='nav':
                world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
                starts=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.PlayerStart)
                nav_ready=bool(starts) and all(unreal.NavigationSystemV1.project_point_to_navigation(
                    world,start.get_actor_location(),nav_data=None,filter_class=None,
                    query_extent=unreal.Vector(100,100,250)) is not None for start in starts)
                if now-self.started>45:
                    raise RuntimeError('Training navigation is not ready before PIE; do not classify this as a gameplay failure')
                if now-self.started>1 and nav_ready and not unreal.NavigationSystemV1.is_navigation_being_built(world):
                    self.report['navigation_ready_before_pie']=True
                    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                    self.phase='pawn'
                return
            if self.phase=='pawn':
                if self.ready('Lvl_DarkTrainingRoom'):
                    self.generator=self.sequence()
                    self.phase='sequence'
                    self.advance()
                return
            if self.phase!='sequence':
                return
            if isinstance(self.waiting,Until):
                if self.waiting.predicate():
                    self.check(True,self.waiting.label)
                    self.advance()
                elif now-self.wait_wall>self.waiting.seconds:
                    self.check(False,self.waiting.label)
                    raise TimeoutError(self.waiting.label)
            else:
                world=self.world()
                current=unreal.GameplayStatics.get_time_seconds(world) if world else 0
                if current-self.wait_game>=float(self.waiting):
                    self.advance()
        except Exception:
            self.finish(traceback.format_exc())

    def advance(self):
        try:
            self.waiting=next(self.generator)
            self.wait_wall=time.monotonic()
            world=self.world()
            self.wait_game=unreal.GameplayStatics.get_time_seconds(world) if world else 0
        except StopIteration:
            self.finish()

    def finish(self,error=None):
        if self.handle is not None:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle=None
        if error:
            self.report['error']=error
            unreal.log_error(error)
        self.report.update(complete=True,passed=not error and all(row['passed'] for row in self.report['checks']),wall_seconds=time.monotonic()-self.started)
        self.write()
        # Preserve PIE so the parent can inspect or extend the exact final state.
        unreal.log('TRIAL_TOWER_QA_COMPLETE ' + str(self.report['passed']))


ACTIVE=None
def start(output):
    global ACTIVE
    ACTIVE=Runner(output).begin()
    return ACTIVE
