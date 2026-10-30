"""Scoped PIE checks for player combat state and the tower encounter facade.

The parent owns editor launch and asset installation. Native input hooks drive
skills/movement; explicitly recorded damage fixtures isolate protection/lifecycle
boundaries without changing any saved actor or asset.
"""
import unreal
import qa_play
import survival_qa


CHARACTERS = [('One', 'BP_CountessCharacter_C'), ('Two', 'BP_SparrowCharacter_C'),
              ('Three', 'GideonCharacter'), ('Four', 'AuroraCharacter')]


class HitReactionRunner(survival_qa.SurvivalRunner):
    def now(self):
        return unreal.GameplayStatics.get_time_seconds(self.world())

    def skills(self):
        return self.pawn().get_skills()

    def movement(self):
        return self.pawn().get_component_by_class(unreal.CharacterMovementComponent)

    def click_goal(self, goal):
        # Project before windup. A first editor navigation query can hitch and
        # otherwise postpone the input until after the short reaction window.
        self.console(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        self.console(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')

    def fixture_damage(self, amount=10):
        self.report.setdefault('damage_fixtures', []).append({
            'time': self.now(), 'amount': amount, 'source': self.subject.get_name(),
            'purpose': 'registered living monster damage for a timing/lifecycle boundary'})
        unreal.GameplayStatics.apply_damage(self.pawn(), amount,
            self.subject.get_controller(), self.subject, None)

    def wait_elapsed(self, start, seconds):
        while self.now() - start < seconds:
            yield .001

    def fresh(self, key='Two', name='BP_SparrowCharacter_C', natural=False):
        run = self.encounter()
        run.restart_run()
        if self.pawn().get_class().get_name() != name:
            yield from self.select(key, name)
        yield qa_play.Until(lambda:len(run.get_active_monsters()) == 8, 15,
                           'fresh eight enemies for ' + name)
        enemies = run.get_active_monsters()
        self.subject = enemies[0]
        for enemy in enemies[1:]:
            enemy.stop_combat()
        if not natural:
            self.subject.stop_combat()
        p = self.pawn().get_actor_location()
        self.move_goal = self.point(p.x - 200, p.y)
        self.cast_goal = self.point(p.x, p.y + 400)
        self.check(run.get_player_health() == 100 and not run.is_player_hit_reacting(),
                   'fresh run has full health and no inherited reaction', True)

    def timing_case(self, fps):
        self.console('t.MaxFPS ' + str(fps))
        yield from self.fresh(natural=True)
        run = self.encounter()
        p = self.pawn().get_actor_location()
        self.subject.set_actor_location(unreal.Vector(p.x + 180, p.y, p.z), False, False)
        yield qa_play.Until(lambda:run.is_player_hit_reacting(), 6,
                           'natural melee starts player reaction at ' + str(fps) + ' FPS')
        start = self.now()
        self.subject.stop_combat()
        self.check(run.get_player_health() == 90 and run.is_player_invulnerable(),
                   'natural hit applies ten damage and protection', True)
        self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_NONE,
                   'reaction disables movement', True)
        position = self.pawn().get_actor_location()
        self.aim(self.cast_goal)
        self.press('Q')
        self.click_goal(self.move_goal)
        yield .04
        self.release('Q')
        self.check(not self.skills().is_casting(), 'new Q input is blocked during reaction', True)
        self.check((self.pawn().get_actor_location() - position).length() < 2,
                   'right click cannot move during reaction', True)
        yield from self.wait_elapsed(start, .05)
        self.fixture_damage()
        self.check(run.get_player_health() == 90 and run.is_player_hit_reacting(),
                   'second hit during reaction cannot damage or restart it', True)
        yield qa_play.Until(lambda:not run.is_player_hit_reacting(), 2,
                           'reaction ends without extension at ' + str(fps) + ' FPS')
        end = self.now() - start
        self.report.setdefault('reaction_timings', []).append({'fps_cap': fps,
            'observed_seconds': end, 'origin': 'first Slate observation of natural hit'})
        self.check(.07 <= end <= .18, 'reaction lasts about 0.12 seconds with frame tolerance', True)
        self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_WALKING,
                   'walking mode is restored after reaction', True)
        self.click_goal(self.move_goal)
        yield from self.wait_elapsed(start, .50)
        self.check((self.pawn().get_actor_location() - position).length() > 60,
                   'new movement input works after recovery', True)
        self.fixture_damage()
        self.check(run.get_player_health() == 90 and not run.is_player_hit_reacting(),
                   'protection allows movement without a second flinch', True)
        yield from self.wait_elapsed(start, .82)
        self.check(not run.is_player_invulnerable(),
                   'protection expires from the first hit, not the later hits', True)
        self.fixture_damage()
        self.check(run.get_player_health() == 80 and run.is_player_hit_reacting(),
                   'a hit after protection can damage and stagger again', True)
        yield .25
        self.aim(self.cast_goal)
        self.press('Q')
        yield .04
        self.release('Q')
        self.check(self.skills().is_casting(), 'new Q input works after recovery', True)
        yield qa_play.Until(lambda:not self.skills().is_casting(), 6, 'Q finishes normally')

    def character_reactions(self):
        self.console('t.MaxFPS 60')
        for key, name in CHARACTERS:
            yield from self.fresh(key, name)
            run = self.encounter()
            mesh = self.pawn().get_component_by_class(unreal.SkeletalMeshComponent)
            anim = mesh.get_anim_instance()
            if key in ('One', 'Three'):
                yield from self.capture(name + '-before-hit')
                unreal.GameplayStatics.set_global_time_dilation(self.world(), .2)
            self.fixture_damage()
            montage = anim.get_current_active_montage()
            self.check((not run.is_player_hit_reacting() and montage is None) if key == 'One' else
                       (run.is_player_hit_reacting() and montage is not None),
                       name + ' uses its intended ordinary damage presentation', True)
            self.report.setdefault('character_reactions', []).append({
                'character': name, 'anim_class': anim.get_class().get_name(),
                'montage': str(montage), 'health': run.get_player_health()})
            if key in ('One', 'Three'):
                yield .06
                yield from self.capture(name + '-hit-reaction')
                unreal.GameplayStatics.set_global_time_dilation(self.world(), 1.0)
            yield .3
            self.check(not run.is_player_hit_reacting() and mesh.get_anim_instance() == anim,
                       name + ' returns to the existing animation instance', True)
            self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_WALKING,
                       name + ' recovers walking', True)

    def casting_case(self):
        yield from self.fresh()
        run = self.encounter()
        self.aim(self.cast_goal)
        self.press('R')
        yield .06
        self.release('R')
        self.check(self.skills().is_casting(), 'Sparrow R is casting before damage', True)
        anim = self.pawn().get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
        montage = anim.get_current_active_montage()
        self.fixture_damage()
        self.check(run.get_player_health() == 90 and not run.is_player_hit_reacting(),
                   'casting takes damage without entering reaction', True)
        self.check(self.skills().is_casting() and anim.get_current_active_montage() == montage,
                   'hit preserves the active skill and its montage', True)
        yield qa_play.Until(lambda:not self.skills().is_casting(), 8,
                           'protected casting completes normally')

    def lifecycle_cases(self):
        yield from self.fresh()
        run = self.encounter()
        self.fixture_damage()
        self.check(run.is_player_hit_reacting(), 'reaction exists before restart', True)
        old_pawn = self.pawn()
        run.restart_run()
        yield .3
        self.check(self.pawn() != old_pawn and not run.is_player_hit_reacting(),
                   'restart removes the old reaction and pawn', True)
        p = self.pawn().get_actor_location()
        goal = self.point(p.x - 200, p.y)
        self.click_goal(goal)
        yield .4
        self.check((self.pawn().get_actor_location() - p).length() > 80,
                   'restart restores native movement input', True)

        yield from self.fresh()
        self.fixture_damage(1000)
        self.check(run.get_run_state() == unreal.TrialTowerRunState.DEFEATED,
                   'lethal damage enters defeat instead of reaction', True)
        yield .3
        self.aim(self.cast_goal)
        self.press('Q'); yield .04; self.release('Q')
        self.check(not run.is_player_hit_reacting() and not self.skills().is_casting() and
                   self.movement().movement_mode == unreal.MovementMode.MOVE_NONE,
                   'reaction cleanup does not unlock a dead player', True)
        self.restart_button()
        self.check(run.get_player_health() == 100 and not run.is_player_hit_reacting(),
                   'death retry restores health without lingering reaction', True)

        yield from self.fresh()
        self.click('ToggleTravel')
        yield .1
        self.fixture_damage()
        self.check(run.is_player_hit_reacting(), 'reaction exists at map-exit request', True)
        self.click('GoTraining')
        yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'), 45,
                           'training opens while tower reaction was active')
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world(), unreal.TrialTowerEncounter),
                   'training has no tower reaction owner', True)
        p = self.pawn().get_actor_location()
        yield from self.move(p.x + 200, p.y)
        yield from self.select('Two', 'BP_SparrowCharacter_C')
        goal = self.point(self.pawn().get_actor_location().x, self.pawn().get_actor_location().y + 350)
        self.aim(goal); self.press('Q'); yield .04; self.release('Q')
        self.check(self.skills().is_casting(), 'training skill input has no lingering tower lock', True)

    def sequence(self):
        if not self.ready('Lvl_TrialTower'):
            self.click('ToggleTravel'); yield .2; self.click('GoTower')
            yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'), 45, 'enter tower for reaction QA')
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.report['scope'] = 'player flinch, input recovery, protection, casting and cleanup'
        self.report['capture_only_time_dilation'] = .2
        for fps in (30, 60):
            yield from self.timing_case(fps)
        yield from self.character_reactions()
        yield from self.casting_case()
        yield from self.lifecycle_cases()

    def finish(self, error=None):
        if self.world():
            unreal.GameplayStatics.set_global_time_dilation(self.world(), 1.0)
        super().finish(error)


class CommonCombatRunner(HitReactionRunner):
    """Migration coverage: common combat works without a tower actor present.

The existing full tower suite remains available through start(). This shorter
entry point runs one timing case and the new ownership/lifecycle boundaries.
"""
    def combat(self):
        component = self.controller().get_player_combat()
        if component is None:
            raise AssertionError('Player controller has no shared combat component')
        return component

    def common_damage(self, amount=10):
        self.report.setdefault('damage_fixtures', []).append({
            'time': self.now(), 'amount': amount, 'source': None,
            'map': self.map_name(),
            'purpose': 'source-less generic damage proves combat is independent of tower actors'})
        unreal.GameplayStatics.apply_damage(self.pawn(), amount, None, None, None)

    def respawn_common(self):
        self.check(self.combat().respawn_player(), 'common RespawnPlayer succeeds', True)
        yield .05
        combat = self.combat()
        self.check(combat.get_health() == combat.get_max_health() and combat.is_alive() and
                   not combat.is_hit_reacting() and not combat.is_invulnerable(),
                   'common respawn resets health, reaction and protection', True)

    def training_reactions(self):
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world(), unreal.TrialTowerEncounter),
                   'training has no tower encounter for common damage tests', True)
        component = self.combat()
        for key, name in CHARACTERS:
            yield from self.respawn_common()
            if self.pawn().get_class().get_name() != name:
                yield from self.select(key, name)
            mesh = self.pawn().get_component_by_class(unreal.SkeletalMeshComponent)
            anim = mesh.get_anim_instance()
            before = component.get_health()
            hit_at = self.now()
            self.common_damage()
            montage = anim.get_current_active_montage()
            expected_reaction = (not component.is_crowd_controlled() and montage is None) if key == 'One' else (
                component.is_hit_reacting() and montage is not None)
            self.check(component.get_health() == before - 10 and component.is_invulnerable() and expected_reaction,
                       name + ' receives generic damage with its intended presentation without tower actors', True)
            self.report.setdefault('common_character_reactions', []).append({
                'character': name, 'health': component.get_health(),
                'anim_class': anim.get_class().get_name(), 'montage': str(montage)})
            yield .25
            self.check(not component.is_hit_reacting() and mesh.get_anim_instance() == anim and
                       self.movement().movement_mode == unreal.MovementMode.MOVE_WALKING,
                       name + ' recovers through the shared component', True)

        # The final Aurora hit is still protected. A normal character selection
        # must preserve controller-owned health and the original deadline.
        health = component.get_health()
        yield from self.select('One', 'BP_CountessCharacter_C')
        self.check(self.combat() == component and component.get_health() == health and
                   component.is_invulnerable(),
                   'character switching preserves shared health and active protection', True)
        self.common_damage()
        self.check(component.get_health() == health and not component.is_hit_reacting(),
                   'new pawn remains protected by the pre-switch hit', True)
        yield from self.wait_elapsed(hit_at, .82)
        self.check(not component.is_invulnerable(),
                   'character switching does not restart the protection deadline', True)

    def training_cast_and_death(self):
        yield from self.respawn_common()
        yield from self.select('Two', 'BP_SparrowCharacter_C')
        combat = self.combat()
        p = self.pawn().get_actor_location()
        goal = self.point(p.x, p.y + 350)
        self.aim(goal); self.press('R'); yield .06; self.release('R')
        self.check(self.skills().is_casting(), 'training R starts before generic damage', True)
        anim = self.pawn().get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
        montage = anim.get_current_active_montage()
        self.common_damage()
        self.check(combat.get_health() == 90 and not combat.is_hit_reacting() and
                   self.skills().is_casting() and anim.get_current_active_montage() == montage,
                   'common damage preserves an active training skill', True)
        yield qa_play.Until(lambda:not self.skills().is_casting(), 8, 'training R completes normally')

        yield from self.respawn_common()
        p = self.pawn().get_actor_location()
        move_goal = self.point(p.x + 200, p.y)
        self.common_damage(1000)
        self.check(not combat.is_alive() and combat.get_health() == 0 and not combat.is_hit_reacting(),
                   'source-less lethal damage kills the training player', True)
        self.aim(goal); self.press('Q'); self.click_goal(move_goal)
        yield .05; self.release('Q'); yield .25
        self.check(not self.skills().is_casting() and (self.pawn().get_actor_location() - p).length() < 2 and
                   self.movement().movement_mode == unreal.MovementMode.MOVE_NONE,
                   'training death keeps skill and movement input locked', True)
        dead_pawn = self.pawn()
        yield from self.respawn_common()
        self.check(self.pawn() != dead_pawn and self.pawn().get_class().get_name() == 'BP_SparrowCharacter_C',
                   'common respawn recreates the selected character', True)
        p = self.pawn().get_actor_location()
        self.click_goal(self.point(p.x + 200, p.y))
        yield .4
        self.check((self.pawn().get_actor_location() - p).length() > 80,
                   'common respawn restores native training movement', True)
        goal = self.point(self.pawn().get_actor_location().x, self.pawn().get_actor_location().y + 350)
        self.aim(goal); self.press('Q'); yield .04; self.release('Q')
        self.check(self.skills().is_casting(), 'common respawn restores native training skill input', True)
        yield qa_play.Until(lambda:not self.skills().is_casting(), 6, 'training Q completes after respawn')

    def training_to_tower(self):
        yield from self.respawn_common()
        previous = self.combat()
        self.click('ToggleTravel'); yield .1
        self.common_damage()
        self.check(previous.is_hit_reacting(), 'common reaction is active when leaving training', True)
        self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'), 45,
                           'tower opens during a training reaction')
        combat = self.combat()
        self.check(combat != previous and combat.get_health() == 100 and combat.is_alive() and
                   not combat.is_hit_reacting() and not combat.is_invulnerable(),
                   'new map starts with a fresh unlocked combat component', True)
        run = self.encounter()
        self.check(run.get_player_health() == combat.get_health() and
                   run.get_max_player_health() == combat.get_max_health(),
                   'tower health facade reflects the shared component', True)

    def basic_attack_case(self):
        # Reuse the previously verified damageable-target interruption setup;
        # StopCombat would make the target invulnerable and mask a stray hit.
        yield from self.fresh('One', 'BP_CountessCharacter_C', natural=True)
        p = self.pawn().get_actor_location()
        self.subject.set_actor_location(unreal.Vector(p.x + 180, p.y, p.z), False, False)
        goal = self.subject.get_actor_location()
        before = self.subject.get_health()
        self.console(f'CountessComboQA.Mouse Press Left {goal.x} {goal.y} {goal.z}')
        yield qa_play.Until(lambda:self.pawn().is_attacking(), 3, 'native basic attack starts before common damage')
        self.common_damage()
        self.check(self.combat().is_hit_reacting() and not self.pawn().is_attacking(),
                   'shared reaction interrupts a basic attack', True)
        self.console(f'CountessComboQA.Mouse Release Left {goal.x} {goal.y} {goal.z}')
        yield .3
        self.check(not self.pawn().is_attacking() and self.subject.get_health() == before,
                   'interrupted basic attack has no held restart or queued damage', True)
        self.console(f'CountessComboQA.Mouse Press Left {goal.x} {goal.y} {goal.z}')
        yield qa_play.Until(lambda:self.pawn().is_attacking(), 3, 'new basic attack works after common recovery')
        self.console(f'CountessComboQA.Mouse Release Left {goal.x} {goal.y} {goal.z}')

    def tower_death_facade(self):
        yield from self.fresh()
        run = self.encounter()
        self.fixture_damage(1000)
        self.check(not self.combat().is_alive() and run.get_run_state() == unreal.TrialTowerRunState.DEFEATED and
                   run.get_player_health() == 0,
                   'common player death notifies the tower encounter', True)
        self.check(all(not enemy.is_attacking() for enemy in run.get_active_monsters()),
                   'tower stops monster attacks after shared death', True)
        self.restart_button()
        self.check(self.combat().get_health() == 100 and self.combat().is_alive() and
                   not self.combat().is_hit_reacting() and run.get_run_state() == unreal.TrialTowerRunState.PREPARING,
                   'tower retry uses the common respawn and resets its own run', True)

    def sequence(self):
        if not self.ready('Lvl_DarkTrainingRoom'):
            self.click('ToggleTravel'); yield .2; self.click('GoTraining')
            yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'), 45, 'training opens for shared combat QA')
        self.console('t.MaxFPS 60')
        self.report['scope'] = 'shared combat outside tower, character/map lifecycle, tower facade regression'
        self.report['reused_prior_validation'] = 'full 30/60 tower reaction suite; only one 60 FPS timing case rerun after ownership migration'
        yield from self.training_reactions()
        yield from self.training_cast_and_death()
        yield from self.training_to_tower()
        yield from self.timing_case(60)
        self.check(self.encounter().get_player_health() == self.combat().get_health(),
                   'natural tower hits and fixtures update the same shared health', True)
        yield from self.basic_attack_case()
        yield from self.tower_death_facade()


ACTIVE = None


def start(output, reuse_pie=False):
    """Reuse the parent's tower PIE or enter through the normal training harness."""
    global ACTIVE
    ACTIVE = HitReactionRunner(output)
    if not reuse_pie:
        return ACTIVE.begin()
    if not ACTIVE.ready('Lvl_TrialTower'):
        raise RuntimeError('reuse_pie requires a ready Trial Tower PIE')
    ACTIVE.performance = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    ACTIVE.old_throttle = ACTIVE.performance.get_editor_property('bThrottleCPUWhenNotForeground')
    ACTIVE.old_fps = unreal.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
    ACTIVE.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
    ACTIVE.phase = 'sequence'
    ACTIVE.generator = ACTIVE.sequence()
    ACTIVE.handle = unreal.register_slate_post_tick_callback(ACTIVE.tick)
    ACTIVE.advance()
    return ACTIVE


def start_common(output, reuse_pie=False):
    """Run shared combat coverage, optionally reusing training or tower PIE."""
    global ACTIVE
    ACTIVE = CommonCombatRunner(output)
    if not reuse_pie:
        return ACTIVE.begin()
    if not (ACTIVE.ready('Lvl_DarkTrainingRoom') or ACTIVE.ready('Lvl_TrialTower')):
        raise RuntimeError('reuse_pie requires ready training or tower PIE')
    ACTIVE.performance = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    ACTIVE.old_throttle = ACTIVE.performance.get_editor_property('bThrottleCPUWhenNotForeground')
    ACTIVE.old_fps = unreal.SystemLibrary.get_console_variable_float_value('t.MaxFPS')
    ACTIVE.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
    ACTIVE.phase = 'sequence'
    ACTIVE.generator = ACTIVE.sequence()
    ACTIVE.handle = unreal.register_slate_post_tick_callback(ACTIVE.tick)
    ACTIVE.advance()
    return ACTIVE
