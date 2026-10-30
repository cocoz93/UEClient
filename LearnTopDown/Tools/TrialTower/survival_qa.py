"""Scoped tower survival checks in the existing real-PIE/input harness."""
import math
import time
import unreal
import qa_play
import combat_qa


class SurvivalRunner(combat_qa.CombatRunner):
    def select(self, key, expected):
        self.press(key); yield .08; self.release(key)
        yield qa_play.Until(lambda:self.pawn().get_class().get_name()==expected,10,'select '+expected)

    def click_move(self, x, y):
        goal=self.point(x,y)
        self.console(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        self.console(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')

    def restart_button(self):
        button=self.status_widget().get_editor_property('restart_button')
        self.check(button.get_is_enabled() and button.is_visible(),'retry button is available',True)
        button.get_editor_property('on_clicked').broadcast()

    def health_sample(self,label):
        run=self.encounter()
        self.report.setdefault('health_samples',[]).append({'label':label,'health':run.get_player_health(),
            'state':str(run.get_run_state()),'floor':run.get_floor_number(),
            'character':self.pawn().get_class().get_name()})
        self.write()

    def sequence(self):
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world(),unreal.TrialTowerEncounter),
                   'training has no tower encounter')
        self.click('ToggleTravel'); yield .2; self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'),45,'enter tower from original map UI')
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        run=self.encounter()
        yield from self.select('Two','BP_SparrowCharacter_C')
        self.check(run.get_player_health()==100,'fresh tower starts at full health',True)

        # Position fixtures isolate the attack geometry; movement itself uses
        # the installed right-click controller. No synthetic player damage.
        for fps in ([30,60] if getattr(self,'verify_geometry',True) else []):
            self.console('t.MaxFPS '+str(fps))
            run.restart_run()
            yield qa_play.Until(lambda:len(run.get_active_monsters())==8,20,'eight enemies for '+str(fps)+' fps check')
            enemies=run.get_active_monsters(); attacker=enemies[0]
            for other in enemies[1:]: other.stop_combat()
            p=self.pawn().get_actor_location()
            attacker.set_actor_location(unreal.Vector(p.x+180,p.y,p.z),False,False)
            yield qa_play.Until(lambda:attacker.is_attacking(),5,'melee windup starts at '+str(fps)+' fps cap')
            self.check(run.get_player_health()==100,'windup does not apply immediate contact damage')
            self.click_move(p.x-650,p.y)
            yield .8
            self.check(run.get_player_health()==100,'ordinary movement evades committed melee at '+str(fps)+' fps cap',True)
            self.check(not self.pawn().get_component_by_class(unreal.CharacterMovementComponent).is_falling(),
                       'dodge movement remains on navigation floor')
        run.restart_run()
        yield qa_play.Until(lambda:run.get_player_health()<100,40,'natural enemy swing damages player')
        health=run.get_player_health()
        self.check(health==90 and run.is_player_invulnerable(),'first hit deals ten and starts protection',True)
        bar=self.status_widget().get_editor_property('health_bar')
        self.check(abs(bar.get_editor_property('percent')-.9)<.001,'health bar reflects damage')
        yield .35
        self.check(run.get_player_health()==health,'overlapping melee cannot bypass short hit protection',True)
        yield from self.capture('01-monsters-attack',True)
        self.health_sample('first-hit')
        # Switch during protection and inspect immediately: same run HP.
        yield qa_play.Until(lambda:run.is_player_invulnerable(),8,'next hit protection window')
        before=run.get_player_health()
        yield from self.select('Four','AuroraCharacter')
        self.check(run.get_player_health()==before,'character switching preserves shared health',True)
        self.health_sample('switched-aurora')
        yield qa_play.Until(lambda:run.get_player_health()<before,8,'newly possessed character receives melee damage')
        yield qa_play.Until(lambda:run.get_run_state()==unreal.TrialTowerRunState.DEFEATED,35,
                           'natural melee damage reaches player death')
        self.check(run.get_player_health()==0,'death clamps health to zero',True)
        self.check(all(not a.is_attacking() for a in run.get_active_monsters()),'death cancels all queued monster strikes')
        pawn=self.pawn(); position=pawn.get_actor_location(); remaining=run.get_remaining_monsters()
        self.click_move(-700,0)
        self.press('Q'); yield .08; self.release('Q')
        self.press('One'); yield .08; self.release('One')
        yield 2.0
        self.check(self.pawn()==pawn,'character selection is blocked while dead',True)
        self.check((self.pawn().get_actor_location()-position).length()<2,'dead player cannot move')
        self.check(not self.pawn().is_combat_busy(),'dead player cannot cast or attack')
        self.check(run.get_remaining_monsters()==remaining and run.get_floor_number()==1,
                   'death freezes combat counts and floor progression')
        self.health_sample('defeated')
        yield from self.capture('02-player-defeated',True)
        yield from self.capture('02-player-defeated-game-camera')
        self.restart_button()
        self.check(run.get_run_state()==unreal.TrialTowerRunState.PREPARING and run.get_player_health()==100,
                   'real retry button resets floor and health',True)
        self.check(self.pawn()!=pawn and self.pawn().get_class().get_name()=='AuroraCharacter',
                   'retry recreates selected character with fresh skill state')
        self.check(self.pawn().get_component_by_class(unreal.SkeletalMeshComponent).get_animation_mode()==unreal.AnimationMode.ANIMATION_BLUEPRINT,
                   'retry restores original character animation blueprint')
        yield from self.move(-600,0)
        self.camera()
        yield qa_play.Until(lambda:len(run.get_active_monsters())==8,20,'retry starts eight fresh monsters')
        yield qa_play.Until(lambda:min(self.distance(a) for a in run.get_active_monsters())<330,
                           15,'enemy enters the original Aurora Q range')
        target=min(run.get_active_monsters(),key=self.distance)
        total=sum(a.get_health() for a in run.get_active_monsters())
        yield from self.cast('Q',target)
        yield qa_play.Until(lambda:sum(a.get_health() for a in run.get_active_monsters())<total,
                           10,'original Aurora Q works after death and retry')
        self.click('ToggleTravel'); yield .2; self.click('GoTraining')
        yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'),45,'return to training during live combat')
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world(),unreal.TrialTowerMonster),
                   'training has no tower enemies')
        self.check(not unreal.WidgetLibrary.get_all_widgets_of_class(self.world(),unreal.TrialTowerStatusWidget,True),
                   'training has no tower health UI')
        # The harness now preserves the loaded editor map and verifies its
        # navigation before PIE, avoiding the redundant-load failure.
        p=self.pawn().get_actor_location()
        yield from self.move(p.x+200,p.y)
        yield from self.select('Two','BP_SparrowCharacter_C')
        self.camera()


class ClearRunner(SurvivalRunner):
    def sequence(self):
        self.click('ToggleTravel'); yield .2; self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'),45,'tower for full survival clear')
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        yield from self.select('Two','BP_SparrowCharacter_C')
        yield from self.fight_floors()

    def fight_floors(self):
        run=self.encounter()
        corners=[(-850,-850),(850,-850),(850,850),(-850,850)]
        corner=0; observed=set(); deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            state=run.get_run_state()
            self.check(state!=unreal.TrialTowerRunState.DEFEATED,'player survives this combat step',True)
            if state==unreal.TrialTowerRunState.COMPLETE: break
            if state==unreal.TrialTowerRunState.FIGHTING:
                floor=run.get_floor_number()
                if floor not in observed:
                    observed.add(floor); self.health_sample('floor-'+str(floor))
                p=self.pawn().get_actor_location(); goal=corners[corner]
                if math.hypot(p.x-goal[0],p.y-goal[1])<200:
                    corner=(corner+1)%4; goal=corners[corner]
                enemies=run.get_active_monsters()
                if enemies:
                    yield from self.cast('Q',min(enemies,key=self.distance))
                    yield .35
                # Native cursor input must target a visible point. Split long
                # routes into nearby clicks instead of projecting off-screen.
                p=self.pawn().get_actor_location()
                dx,dy=goal[0]-p.x,goal[1]-p.y
                distance=math.hypot(dx,dy)
                scale=min(1.0,500.0/max(distance,1.0))
                self.click_move(p.x+dx*scale,p.y+dy*scale)
                yield 1.25
            else:
                yield .25
        self.check(run.get_run_state()==unreal.TrialTowerRunState.COMPLETE and observed=={1,2,3},
                   'native movement and skill input clears all three floors with enemy attacks enabled',True)
        self.health_sample('complete')
        yield from self.capture('03-survival-three-floors-complete',True)
        yield from self.capture('03-survival-combat-game-camera')
        self.restart_button()
        self.check(run.get_floor_number()==1 and run.get_player_health()==100,'completion retry also resets health')


ACTIVE=None
def start(output, clear=False):
    global ACTIVE
    ACTIVE=(ClearRunner if clear else SurvivalRunner)(output).begin()
    return ACTIVE
