"""Short real-PIE checks for the tower veil, neutral palette and camera edges."""
from pathlib import Path
import unreal
import qa_play
import camera_bounds


class PresentationRunner(qa_play.Runner):
    def settle_camera(self, label):
        # Background editor frames can advance game time faster than SpringArm's
        # clamped lag step. Wait for actual camera convergence before visual QA.
        previous = [None, 0]
        def stable():
            position = self.pawn().get_component_by_class(unreal.CameraComponent).get_world_location()
            old = previous[0]
            delta = ((position.x-old.x)**2+(position.y-old.y)**2+(position.z-old.z)**2)**.5 if old else 1e9
            previous[1] = previous[1]+1 if delta < .5 else 0
            previous[0] = position
            return previous[1] >= 3
        yield qa_play.Until(stable, 25, 'camera lag settles: ' + label)

    def relocate(self, x, y):
        goal = self.point(x, y)
        pawn = self.pawn()
        pawn.get_component_by_class(unreal.CharacterMovementComponent).stop_movement_immediately()
        half = pawn.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
        pawn.set_actor_location(unreal.Vector(goal.x, goal.y, goal.z + half + 2), False, True)

    def projection(self, position):
        result = self.controller().project_world_location_to_screen(position, True)
        if isinstance(result, tuple):
            result = next((item for item in result if isinstance(item, unreal.Vector2D)), None)
        if not isinstance(result, unreal.Vector2D):
            return None
        width, height = self.controller().get_viewport_size()
        return [result.x / width, result.y / height]

    def camera_sample(self, label):
        sample = camera_bounds.sample_runtime()
        sample['label'] = label
        sample['screen'] = self.projection(self.pawn().get_actor_location())
        self.report.setdefault('edge_samples', []).append(sample)
        self.write()
        pivot = sample['effective_pivot']
        actors = unreal.GameplayStatics.get_all_actors_with_tag(self.world(), 'TrialTowerCameraBounds')
        self.check(len(actors) == 1, 'one map-local camera limiter: ' + label, True)
        limit = actors[0]
        bounded = all(limit.get_editor_property('CameraMin'+axis)-.1 <= pivot[i]
                      <= limit.get_editor_property('CameraMax'+axis)+.1 for i,axis in enumerate(('X','Y')))
        self.check(bounded, 'actual camera target remains inside bounds: ' + label)
        screen = sample['screen']
        self.check(screen is not None and .04 < screen[0] < .96 and .04 < screen[1] < .84,
                   'player remains inside viewport above HUD: ' + label)
        return sample

    def sequence(self):
        self.click('ToggleTravel'); yield .2; self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'),45,'updated tower loads through real map UI')
        yield 2.0
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.press('Two'); yield .08; self.release('Two')
        yield qa_play.Until(lambda:self.pawn().get_class().get_name()=='BP_SparrowCharacter_C',12,'Sparrow selected')
        yield 1.5
        self.camera()
        yield from self.capture('neutral-sparrow-idle')
        p=self.point(1050,550)
        self.console(f'CountessComboQA.Mouse Move Left {p.x} {p.y} {p.z}')
        self.press('Q'); yield .05; self.release('Q')
        yield .65
        yield from self.capture('neutral-sparrow-q')
        yield 2.5

        for label,x,y in [('center',0,0),('near-corner',-1450,-1450),
                          ('left-corner',-1400,1250),('right-corner',1250,-1400),
                          ('far-corner',1200,1200),('west-entry',-2110,0),
                          ('east-entry',2110,0),('south-entry',0,-2110),('north-entry',0,2110)]:
            self.relocate(x,y)
            yield 2.0
            yield from self.settle_camera(label)
            self.camera_sample(label)
            if label in ('near-corner','east-entry','north-entry','west-entry'):
                yield from self.capture(label)

        # Switching at the clamped edge must retain both native view ownership
        # and bounds, rather than passing only when the correction is zero.
        self.relocate(-1400,0); yield 1.5
        yield from self.move(-1780,0)
        yield from self.move(-2110,0)
        self.camera_sample('walking-across-boundary')
        for key,expected in [('One','BP_CountessCharacter_C'),('Three','GideonCharacter'),
                             ('Four','AuroraCharacter'),('Two','BP_SparrowCharacter_C')]:
            self.press(key); yield .08; self.release(key)
            yield qa_play.Until(lambda expected=expected:self.pawn().get_class().get_name()==expected,
                               12,'bounded character switch '+key)
            yield 1.8
            self.camera_sample('switch-'+key)
            self.camera()

        self.relocate(0,0); yield 1.5
        arm=self.pawn().get_component_by_class(unreal.SpringArmComponent)
        arm.set_editor_property('target_arm_length',7200.0)
        yield 2.0
        yield from self.settle_camera('overview')
        yield from self.capture('neutral-tower-overview')
        arm.set_editor_property('target_arm_length',2000.0)
        yield 1.5
        self.relocate(550,550); yield 1.5
        self.press('Four'); yield .08; self.release('Four')
        yield qa_play.Until(lambda:self.pawn().get_class().get_name()=='AuroraCharacter',12,'Aurora comparison selected')
        yield 1.0
        p=self.point(1000,550)
        self.console(f'CountessComboQA.Mouse Move Left {p.x} {p.y} {p.z}')
        self.press('R'); yield .08; self.release('R')
        yield .8
        yield from self.capture('neutral-aurora-r')
        yield 2.0
        self.click('ToggleTravel'); yield .2; self.click('GoTraining')
        yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'),45,'return to unchanged training map')
        yield 1.5
        arm=self.pawn().get_component_by_class(unreal.SpringArmComponent)
        offset=arm.get_editor_property('target_offset')
        self.check(abs(offset.x)<.01 and abs(offset.y)<.01, 'training camera has no tower clamp offset')
        self.check(not unreal.GameplayStatics.get_all_actors_with_tag(self.world(),'TrialTowerCameraBounds'),
                   'training has no tower camera actor')
        self.camera()


ACTIVE=None
def start(output):
    global ACTIVE
    ACTIVE=PresentationRunner(output).begin()
    return ACTIVE
