"""Scoped real-PIE validation of the three-floor tower, using native input hooks."""
import math
import unreal
import qa_play
import presentation_qa


class CombatRunner(presentation_qa.PresentationRunner):
    def begin(self):
        # An unfocused editor otherwise throttles to roughly 3 fps, too coarse
        # for the existing short basic-attack montage/timer sequence.
        self.performance = unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
        self.old_throttle = self.performance.get_editor_property('bThrottleCPUWhenNotForeground')
        self.old_fps = unreal.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground',False)
        unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')
        self.report['input_timing_environment'] = 'background editor throttle disabled; maximum 60 fps'
        try:
            return super().begin()
        except Exception:
            self.restore_timing()
            raise

    def restore_timing(self):
        if hasattr(self,'performance'):
            self.performance.set_editor_property('bThrottleCPUWhenNotForeground',self.old_throttle)
            unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS '+str(self.old_fps))

    def finish(self,error=None):
        super().finish(error)
        self.restore_timing()

    def encounter(self):
        actors = unreal.GameplayStatics.get_all_actors_of_class(self.world(),unreal.TrialTowerEncounter)
        if len(actors) != 1:
            raise AssertionError('Expected one map-local encounter')
        return actors[0]

    def status_widget(self):
        widgets = unreal.WidgetLibrary.get_all_widgets_of_class(self.world(),unreal.TrialTowerStatusWidget,True)
        if len(widgets) != 1:
            raise AssertionError('Expected one tower status widget')
        return widgets[0]

    def aim(self, target):
        p = target.get_actor_location() if isinstance(target,unreal.Actor) else target
        self.console(f'CountessComboQA.Mouse Move Left {p.x} {p.y} {p.z}')

    def cast(self, key, target):
        self.aim(target)
        self.press(key); yield .08; self.release(key)

    def distance(self, actor):
        p = self.pawn().get_actor_location(); q = actor.get_actor_location()
        return math.hypot(p.x-q.x,p.y-q.y)

    def sample(self, label):
        run = self.encounter()
        result = {'label':label, 'floor':run.get_floor_number(), 'state':str(run.get_run_state()),
                  'remaining':run.get_remaining_monsters(), 'enemies':[
                      {'name':a.get_name(),'hp':a.get_health(),'distance':self.distance(a)}
                      for a in run.get_active_monsters()]}
        self.report.setdefault('encounter_samples',[]).append(result)
        self.write()
        return result

    def sequence(self):
        self.click('ToggleTravel'); yield .2; self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'),45,'tower opens through existing map selector')
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.press('Two'); yield .08; self.release('Two')
        yield qa_play.Until(lambda:self.pawn().get_class().get_name()=='BP_SparrowCharacter_C',12,'Sparrow selected')
        yield qa_play.Until(lambda:len(self.encounter().get_active_monsters())==8,20,'first floor spawns eight enemies')
        initial = self.sample('first-spawn')
        self.check(self.encounter().get_remaining_monsters()==8,'remaining count includes the full first floor')
        yield from self.capture('01-four-entrances',True)
        yield 5.0
        chased = self.sample('pursuit')
        before = {a['name']:a['distance'] for a in initial['enemies']}
        self.check(all(a['distance'] < before[a['name']]-120 for a in chased['enemies']),
                   'enemies from all four gates approach current player',True)
        self.check(all(a.get_controller() is not None for a in self.encounter().get_active_monsters()),
                   'all living monsters have pursuit controllers')
        target = max(self.encounter().get_active_monsters(),key=self.distance)
        health_before = sum(a.get_health() for a in self.encounter().get_active_monsters())
        p=target.get_actor_location()
        self.console(f'CountessComboQA.Mouse Press Left {p.x} {p.y} {p.z}')
        yield .8
        self.console(f'CountessComboQA.Mouse Release Left {p.x} {p.y} {p.z}')
        yield qa_play.Until(lambda:sum(a.get_health() for a in self.encounter().get_active_monsters())<health_before,
                           10,'native Sparrow basic attack damages tower monster')
        yield from self.capture('02-first-combat',True)
        yield from self.capture('02-first-combat-game-camera')
        for floor,total in [(1,8),(2,12),(3,16)]:
            run = self.encounter()
            yield qa_play.Until(lambda floor=floor:run.get_floor_number()==floor and
                run.get_run_state()==unreal.TrialTowerRunState.FIGHTING,35,'floor '+str(floor)+' begins')
            if floor > 1:
                yield qa_play.Until(lambda total=total:len(run.get_active_monsters())==total,20,
                                   'floor '+str(floor)+' spawns '+str(total)+' enemies')
                yield 5.5
                self.sample('floor-'+str(floor)+'-combat')
                yield from self.capture('floor-'+str(floor),True)
            for attempt in range(28):
                if run.get_run_state()!=unreal.TrialTowerRunState.FIGHTING:
                    break
                enemies=run.get_active_monsters()
                if enemies:
                    target=min(enemies,key=self.distance)
                    yield from self.cast('Q',target)
                    yield 1.6
                else:
                    yield .3
            self.check(run.get_run_state()!=unreal.TrialTowerRunState.FIGHTING,
                       'real skill damage clears floor '+str(floor),True)
            self.check(run.get_remaining_monsters()==0,'floor '+str(floor)+' clears with no remaining monsters')
            self.sample('floor-'+str(floor)+'-cleared')
            if floor < 3:
                self.check(run.get_run_state()==unreal.TrialTowerRunState.INTERMISSION,
                           'clear banner precedes next floor')
        self.check(run.get_run_state()==unreal.TrialTowerRunState.COMPLETE,'third floor completes the run',True)
        yield from self.capture('03-three-floors-complete',True)
        button=self.status_widget().get_editor_property('restart_button')
        self.check(button.get_is_enabled() and button.get_visibility()==unreal.SlateVisibility.VISIBLE,
                   'completion shows an enabled restart button')
        button.get_editor_property('on_clicked').broadcast()
        self.check(run.get_floor_number()==1 and run.get_run_state()==unreal.TrialTowerRunState.PREPARING,
                   'real restart button resets to floor one')
        yield qa_play.Until(lambda:len(run.get_active_monsters())==8,20,'restart spawns a fresh first floor')
        self.click('ToggleTravel'); yield .2; self.click('GoTraining')
        yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'),45,'training map still opens during combat')
        yield 2.0
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world(),unreal.TrialTowerMonster),
                   'no tower monsters remain in training')
        self.check(not unreal.WidgetLibrary.get_all_widgets_of_class(self.world(),unreal.TrialTowerStatusWidget,True),
                   'tower status UI removed on map exit')
        self.camera()


ACTIVE=None
def start(output):
    global ACTIVE
    ACTIVE=CombatRunner(output).begin()
    return ACTIVE
