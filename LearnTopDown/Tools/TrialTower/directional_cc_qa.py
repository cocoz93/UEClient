"""Scoped real-PIE coverage for directional reactions and optional player CC.

Run only in the parent's single editor session. Fixtures borrow actors from the
PIE world, restore them on completion, and never modify or save the editor world.
"""
import unreal
import qa_play
from hit_reaction_qa import CommonCombatRunner, CHARACTERS


def dot(left, right):
    return left.x * right.x + left.y * right.y + left.z * right.z


class DirectionalCombatRunner(CommonCombatRunner):
    def __init__(self, output, groups=None):
        super().__init__(output)
        self.groups = groups or ('directions', 'crowd_control', 'boundaries', 'cast_interruptions', 'lifecycle')
        self.fixtures = []

    def mesh(self):
        return self.pawn().get_component_by_class(unreal.SkeletalMeshComponent)

    def animation_name(self):
        animation = self.combat().get_active_reaction_animation()
        return animation.get_name() if animation else ''

    def borrow_fixture(self, actor_class, location):
        actors = unreal.GameplayStatics.get_all_actors_of_class(self.world(), actor_class)
        if actor_class == unreal.StaticMeshActor:
            # Avoid floor pieces and nearby gameplay geometry. Only a normal
            # BlockAll profile is borrowed, so no custom response table is lost.
            candidates = []
            for actor in actors:
                mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
                if (mesh and str(mesh.get_collision_profile_name()) in ('BlockAll', 'BlockAllDynamic')
                        and (actor.get_actor_location() - self.pawn().get_actor_location()).length() > 1000):
                    _, bounds = actor.get_actor_bounds(False)
                    if bounds.x < 1000 and bounds.y < 1000 and bounds.z > 50:
                        candidates.append(actor)
            actors = candidates
        self.check(bool(actors), 'PIE has a reusable fixture of class ' + actor_class.__name__, True)
        actor = actors[0]
        saved = {'actor': actor, 'transform': actor.get_actor_transform(),
                 'collision': actor.get_actor_enable_collision()}
        if actor_class == unreal.StaticMeshActor:
            mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
            saved.update(mesh=mesh, asset=mesh.get_editor_property('static_mesh'),
                         mobility=mesh.get_editor_property('mobility'))
            mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        else:
            actor.set_actor_enable_collision(False)
        self.fixtures.append(saved)
        actor.set_actor_location(location, False, True)
        return actor

    def destroy_fixtures(self):
        for saved in self.fixtures:
            actor = saved['actor']
            if unreal.SystemLibrary.is_valid(actor):
                mesh = saved.get('mesh')
                if mesh:
                    mesh.set_static_mesh(saved['asset'])
                actor.set_actor_transform(saved['transform'], False, True)
                actor.set_actor_enable_collision(saved['collision'])
                if mesh:
                    mesh.set_mobility(saved['mobility'])
        self.fixtures = []

    def prepare(self, key='Two', name='BP_SparrowCharacter_C'):
        unreal.GameplayStatics.set_global_time_dilation(self.world(), 1.0)
        if self.combat().is_crowd_controlled() or not self.combat().is_alive():
            yield from self.respawn_common()
        if self.pawn().get_class().get_name() != name:
            yield from self.select(key, name)
        # Respawning after selection also removes the selected hero's intro.
        yield from self.respawn_common()
        self.controller().stop_movement()
        self.pawn().set_actor_rotation(unreal.Rotator(yaw=37), True)
        yield .10

    def wait_recovered(self, label, timeout=5):
        yield qa_play.Until(lambda:not self.combat().is_crowd_controlled(), timeout, label)
        self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_WALKING,
                   label + ': walking restored', True)

    def directional_damage(self, direction, amount=10):
        pawn = self.pawn()
        causer = self.borrow_fixture(unreal.KwangTrainingDummy,
            pawn.get_actor_location() + direction * 400)
        self.report.setdefault('damage_fixtures', []).append({
            'time': self.now(), 'amount': amount, 'source': causer.get_name(),
            'purpose': 'temporarily positioned PIE training dummy selects relative impact direction'})
        unreal.GameplayStatics.apply_damage(pawn, amount, None, causer, None)
        return causer

    def directions(self):
        for key, name in CHARACTERS:
            yield from self.prepare(key, name)
            hero = name.replace('BP_', '').replace('Character_C', '').replace('Character', '').lower()
            for direction_name in ('Front', 'Back', 'Left', 'Right'):
                yield from self.respawn_common()
                self.pawn().set_actor_rotation(unreal.Rotator(yaw=37), True)
                forward = self.pawn().get_actor_forward_vector()
                right = self.pawn().get_actor_right_vector()
                vectors = {'Front': forward, 'Back': forward * -1,
                           'Left': right * -1, 'Right': right}
                mesh, anim = self.mesh(), self.mesh().get_anim_instance()
                unreal.GameplayStatics.set_global_time_dilation(self.world(), .2)
                self.directional_damage(vectors[direction_name])
                selected = self.animation_name()
                direction = str(self.combat().get_hit_direction())
                montage = anim.get_current_active_montage()
                if key == 'One':
                    self.check(direction_name.upper() in direction.upper() and
                               not self.combat().is_crowd_controlled() and not selected,
                               name + ' reports impact direction without interrupting animation', True)
                    self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_WALKING,
                               name + ' ordinary damage keeps walking enabled', True)
                    yield .07
                    yield from self.capture(hero + '-hit-' + direction_name.lower())
                    unreal.GameplayStatics.set_global_time_dilation(self.world(), 1.0)
                    self.destroy_fixtures()
                    continue
                suffixes = {'Front': ('fwd', 'front'), 'Back': ('bwd', 'back'),
                            'Left': ('left',), 'Right': ('right',)}
                self.check(direction_name.upper() in direction.upper() and
                           selected.lower().endswith(suffixes[direction_name]),
                           name + ' selects ' + direction_name + ' at a rotated heading', True)
                self.check(self.combat().is_hit_reacting() and self.combat().is_crowd_controlled()
                           and montage is not None,
                           name + ' ' + direction_name + ' plays a locked reaction', True)
                expected_rate = 2.0
                self.check(abs(anim.montage_get_play_rate(montage) - expected_rate) < .001,
                           name + ' ' + direction_name + ' uses its ordinary impact tempo', True)
                self.report.setdefault('directions', []).append({
                    'hero': name, 'heading_degrees': 37, 'direction': direction_name,
                    'reported_direction': direction, 'animation': selected,
                    'montage': str(montage), 'time': self.now()})
                yield .07
                yield from self.capture(hero + '-hit-' + direction_name.lower())
                unreal.GameplayStatics.set_global_time_dilation(self.world(), 1.0)
                yield from self.wait_recovered(name + ' ' + direction_name + ' recovers')
                self.check(mesh.get_anim_instance() == anim,
                           name + ' ' + direction_name + ' preserves the existing animation instance', True)
                self.destroy_fixtures()
        yield from self.respawn_common()
        self.common_damage()
        self.check('FRONT' in str(self.combat().get_hit_direction()).upper(),
                   'source-less damage falls back to Front', True)
        yield from self.wait_recovered('source-less reaction recovers')

    def crowd_control(self):
        for key, name in CHARACTERS:
            yield from self.prepare(key, name)
            hero = name.replace('BP_', '').replace('Character_C', '').replace('Character', '').lower()
            anim = self.mesh().get_anim_instance()
            before = self.pawn().get_actor_location()
            self.check(self.combat().apply_stun(2.0), name + ' accepts explicit stun', True)
            self.check(self.combat().is_stunned() and self.combat().is_crowd_controlled()
                       and not self.combat().is_hit_reacting(), name + ' exposes distinct stun state', True)
            start_animation = self.animation_name()
            self.check('stun' in start_animation.lower(), name + ' uses a native stun clip', True)
            yield .12
            yield from self.capture(hero + '-stun-start')
            yield qa_play.Until(lambda:'loop' in self.animation_name().lower(), 4,
                               name + ' transitions into its stun loop')
            loop_animation = self.animation_name()
            yield .12
            yield from self.capture(hero + '-stun-loop')
            self.report.setdefault('stuns', []).append({
                'hero': name, 'start_animation': start_animation, 'loop_animation': loop_animation})
            self.check((self.pawn().get_actor_location() - before).length() < 2,
                       name + ' stun does not displace the capsule', True)
            health = self.combat().get_health()
            self.common_damage()
            self.check(self.combat().get_health() == health - 10 and self.combat().is_stunned()
                       and not self.combat().is_hit_reacting(),
                       name + ' accepts damage without replacing its stun loop', True)
            yield from self.wait_recovered(name + ' stun expires')
            self.check(self.mesh().get_anim_instance() == anim,
                       name + ' stun returns through the original animation instance', True)

            yield from self.respawn_common()
            before = self.pawn().get_actor_location()
            facing = self.pawn().get_actor_forward_vector()
            # Move away from the facing direction, leaving room near the spawn.
            direction = facing * -1
            self.check(self.combat().apply_knockback(direction, 220.0, .4),
                       name + ' accepts explicit knockback', True)
            self.check(self.combat().is_knocked_back() and self.combat().is_crowd_controlled()
                       and not self.combat().is_hit_reacting(), name + ' exposes distinct knockback state', True)
            clip = self.animation_name()
            self.check('knock' in clip.lower(), name + ' uses a native knockback clip', True)
            yield .10
            yield from self.capture(hero + '-knockback')
            yield from self.wait_recovered(name + ' knockback expires')
            after = self.pawn().get_actor_location()
            displacement = after - before
            projected = dot(displacement, direction)
            self.check(170 <= projected <= 250,
                       name + ' knockback moves about the requested 220 cm', True)
            self.check(dot(self.pawn().get_actor_forward_vector(), facing) > .995,
                       name + ' keeps its facing while being pushed', True)
            yield .25
            self.check((self.pawn().get_actor_location() - after).length() < 3,
                       name + ' has no residual knockback velocity after recovery', True)
            self.report.setdefault('knockbacks', []).append({
                'hero': name, 'animation': clip, 'requested_cm': 220,
                'observed_projected_cm': projected,
                'displacement': [displacement.x, displacement.y, displacement.z]})

    def boundaries(self):
        yield from self.prepare()
        combat = self.combat()
        self.check(not combat.apply_stun(0) and not combat.apply_stun(-1),
                   'non-positive stun durations are rejected', True)
        self.check(not combat.apply_knockback(unreal.Vector(), 200, .4) and
                   not combat.apply_knockback(unreal.Vector(1, 0, 0), 0, .4) and
                   not combat.apply_knockback(unreal.Vector(1, 0, 0), 200, 0),
                   'zero direction, distance, or duration cannot start knockback', True)
        p = self.pawn().get_actor_location()
        move_goal = self.point(p.x - 200, p.y)
        cast_goal = self.point(p.x, p.y + 350)
        self.aim(cast_goal); self.press('R'); yield .06; self.release('R')
        self.check(self.skills().is_casting(), 'Sparrow R is active before hard CC', True)
        self.common_damage()
        self.check(self.skills().is_casting() and not combat.is_hit_reacting(),
                   'ordinary damage still preserves an active skill', True)
        self.check(combat.apply_stun(.7), 'stun interrupts an active skill', True)
        started = self.now()
        self.check(not self.skills().is_casting(), 'hard CC cancels the active R cast', True)
        self.aim(cast_goal); self.press('Q'); self.click_goal(move_goal)
        yield .05; self.release('Q')
        self.check(not self.skills().is_casting() and
                   (self.pawn().get_actor_location() - p).length() < 2,
                   'stun blocks new skill and movement input', True)
        yield from self.wait_elapsed(started, .25)
        self.check(not combat.apply_stun(2.0) and
                   not combat.apply_knockback(unreal.Vector(1, 0, 0), 200, .4),
                   'overlapping CC is rejected instead of refreshing the deadline', True)
        self.common_damage()
        self.check(combat.get_health() == 90 and combat.is_stunned() and not combat.is_hit_reacting(),
                   'protected repeated damage does not replace an active hard CC reaction', True)
        yield from self.wait_recovered('stun ends on its original deadline')
        recovered_at = self.now()
        elapsed = recovered_at - started
        self.check(.65 <= elapsed <= .82, 'rejected overlap does not extend 0.7-second stun', True)
        self.check(not combat.apply_stun(.5), 'post-CC protection blocks immediate re-stun', True)
        self.click_goal(move_goal)
        yield .35
        self.check((self.pawn().get_actor_location() - p).length() > 60,
                   'native movement returns during post-CC protection', True)
        self.aim(cast_goal); self.press('Q'); yield .04; self.release('Q')
        self.check(self.skills().is_casting(), 'native Q returns after hard CC', True)
        yield qa_play.Until(lambda:not self.skills().is_casting(), 6, 'Q completes after hard CC')
        # Skill duration is unrelated to the protection deadline. Measure from
        # observed CC recovery instead of assuming Q lasts at least 0.75 seconds.
        yield from self.wait_elapsed(recovered_at, .80)
        self.check(combat.apply_stun(.15), 'CC is accepted again after protection expires', True)
        yield from self.wait_recovered('second stun recovers')

        # A damaging ability may apply damage first and then explicit CC.
        yield from self.respawn_common()
        self.common_damage()
        self.check(combat.is_hit_reacting() and combat.apply_stun(.3) and combat.is_stunned(),
                   'hard CC can replace a brief hit despite independent damage protection', True)
        yield from self.wait_recovered('hit-to-stun upgrade recovers')

        yield from self.respawn_common()
        p = self.pawn().get_actor_location()
        cast_goal = self.point(p.x, p.y + 350)
        move_goal = self.point(p.x, p.y + 200)
        self.aim(cast_goal); self.press('R'); yield .06; self.release('R')
        self.check(self.skills().is_casting(), 'Sparrow R starts before knockback', True)
        self.check(combat.apply_knockback(unreal.Vector(-1, 0, 0), 200, .5),
                   'knockback interrupts an active cast', True)
        self.check(not self.skills().is_casting(), 'knockback cancels the active skill', True)
        self.aim(cast_goal); self.press('Q'); self.click_goal(move_goal)
        yield .05; self.release('Q')
        self.check(not self.skills().is_casting() and abs(self.pawn().get_actor_location().y - p.y) < 2,
                   'walking-mode knockback still blocks skill and steering input', True)
        yield from self.wait_recovered('casting knockback recovers')

        distances = []
        for fps in (30, 60):
            yield from self.respawn_common()
            self.console('t.MaxFPS ' + str(fps))
            yield .10
            p = self.pawn().get_actor_location()
            self.check(combat.apply_knockback(unreal.Vector(-1, 0, 0), 240, .4),
                       'knockback starts at ' + str(fps) + ' FPS', True)
            yield from self.wait_recovered('knockback ends at ' + str(fps) + ' FPS')
            distance = p.x - self.pawn().get_actor_location().x
            distances.append(distance)
            self.check(200 <= distance <= 270, str(fps) + ' FPS knockback distance is bounded', True)
            self.report.setdefault('frame_rate_knockback', []).append({'fps_cap': fps, 'distance_cm': distance})
        self.check(abs(distances[0] - distances[1]) < 30,
                   '30/60 FPS knockback distances agree within one movement frame', True)
        self.console('t.MaxFPS 60')

        yield from self.respawn_common()
        p = self.pawn().get_actor_location()
        wall = self.borrow_fixture(unreal.StaticMeshActor, p + unreal.Vector(-250, 0, 0))
        mesh = wall.get_component_by_class(unreal.StaticMeshComponent)
        mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        wall.set_actor_scale3d(unreal.Vector(.5, 4, 4))
        yield .10
        self.check(combat.apply_knockback(unreal.Vector(-1, 0, 0), 400, .4),
                   'knockback starts toward a real blocking collision fixture', True)
        yield from self.wait_recovered('wall-blocked knockback still recovers')
        distance = p.x - self.pawn().get_actor_location().x
        self.check(80 < distance < 220, 'knockback collision stops the capsule before the wall', True)
        self.report['wall_knockback_distance_cm'] = distance
        yield from self.capture('sparrow-knockback-blocked-by-wall')
        self.destroy_fixtures()

    def lifecycle(self):
        yield from self.prepare()
        combat = self.combat()
        self.check(combat.apply_stun(2), 'stun starts before lethal damage', True)
        self.common_damage(1000)
        self.check(not combat.is_alive() and not combat.is_crowd_controlled(),
                   'death clears active CC', True)
        self.check(not combat.apply_stun(1) and not combat.apply_knockback(unreal.Vector(1, 0, 0), 200, .4),
                   'a dead player rejects new hard CC', True)
        yield .5
        self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_NONE,
                   'old CC cleanup cannot restore movement after death', True)
        yield from self.respawn_common()
        self.check(not combat.is_crowd_controlled() and combat.apply_knockback(unreal.Vector(-1, 0, 0), 200, .4),
                   'respawn clears CC protection and allows a new knockback', True)
        old = self.pawn()
        yield from self.respawn_common()
        self.check(self.pawn() != old and not combat.is_crowd_controlled(),
                   'retry during knockback removes the old movement source', True)
        p = self.pawn().get_actor_location()
        yield .6
        self.check((self.pawn().get_actor_location() - p).length() < 2,
                   'new pawn cannot inherit the old knockback displacement', True)

        # Input normally prevents switching under CC. Unpossession is also an
        # independent lifecycle boundary and can reuse the current PIE pawn.
        self.check(combat.apply_stun(2), 'stun starts before programmatic unpossession', True)
        old = self.pawn()
        player = self.controller()
        player.un_possess()
        self.check(not combat.is_crowd_controlled(), 'unpossession clears the previous pawn CC', True)
        player.possess(old)
        yield .08
        self.check(self.pawn() == old and not combat.is_crowd_controlled(),
                   'repossession does not inherit the old CC', True)
        yield from self.respawn_common()
        p = self.pawn().get_actor_location()
        self.click_goal(self.point(p.x - 180, p.y))
        yield .35
        self.check((self.pawn().get_actor_location() - p).length() > 60,
                   'input ownership is restored after repossession', True)

        self.click('ToggleTravel'); yield .10
        self.check(combat.apply_stun(2), 'stun starts before map travel', True)
        self.click('GoTower')
        yield qa_play.Until(lambda:self.ready('Lvl_TrialTower'), 45, 'map travel completes during stun')
        self.check(self.combat() != combat and not self.combat().is_crowd_controlled()
                   and self.combat().get_health() == 100,
                   'new map has no inherited CC or damage state', True)
        # Return immediately: no new monster CC source has been installed.
        self.click('ToggleTravel'); yield .10; self.click('GoTraining')
        yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'), 45, 'return to original training map')

    def cast_interruptions(self):
        # Sparrow is covered by boundaries(); these are the other three
        # existing skill implementations' CancelSkill/Finish paths.
        cases = [('One', 'BP_CountessCharacter_C', 'W'),
                 ('Three', 'GideonCharacter', 'R'),
                 ('Four', 'AuroraCharacter', 'R')]
        for key, name, skill in cases:
            for effect in ('stun', 'knockback'):
                yield from self.prepare(key, name)
                combat = self.combat()
                p = self.pawn().get_actor_location()
                aim_goal = self.point(p.x, p.y + 350)
                move_goal = self.point(p.x, p.y + 200)
                self.aim(aim_goal); self.press(skill); yield .06; self.release(skill)
                label = name + ' ' + skill + ' -> ' + effect
                self.check(self.skills().is_casting(), label + ': native skill starts', True)
                accepted = (combat.apply_stun(.6) if effect == 'stun' else
                            combat.apply_knockback(unreal.Vector(-1, 0, 0), 180, .4))
                self.check(accepted and not self.skills().is_casting() and combat.is_crowd_controlled(),
                           label + ': CC cancels the active skill', True)
                yield .20
                self.check(combat.is_crowd_controlled() and not self.skills().is_casting(),
                           label + ': cancelled skill does not restart during CC', True)
                if effect == 'stun':
                    self.check(self.movement().movement_mode == unreal.MovementMode.MOVE_NONE,
                               label + ': skill cleanup cannot release the stun lock', True)
                yield from self.wait_recovered(label + ': control returns')
                self.click_goal(move_goal)
                start = self.pawn().get_actor_location()
                yield .35
                self.check((self.pawn().get_actor_location() - start).length() > 60 and
                           not combat.is_crowd_controlled(),
                           label + ': native movement works after recovery', True)
                self.report.setdefault('cast_interruptions', []).append({
                    'hero': name, 'skill': skill, 'effect': effect, 'passed': True})

    def countess_feedback(self):
        yield from self.prepare('One', 'BP_CountessCharacter_C')
        self.check(self.combat().uses_non_interrupting_damage_feedback(), 'Countess enables new feedback', True)
        self.camera()
        for fps in (30, 60):
            self.console('t.MaxFPS ' + str(fps))
            yield from self.respawn_common()
            p = self.pawn().get_actor_location()
            self.click_goal(self.point(p.x + 600, p.y))
            yield qa_play.Until(lambda:self.pawn().get_velocity().length() > 100, 4, 'movement starts before damage')
            position = self.pawn().get_actor_location()
            self.common_damage(20)
            self.check(self.combat().get_health() == 80 and not self.combat().is_crowd_controlled() and
                       self.pawn().get_velocity().length() > 100,
                       'damage preserves movement immediately at ' + str(fps) + ' FPS', True)
            self.check(self.combat().get_damage_trail_health() == 100, 'lost health is held briefly', True)
            yield .2
            self.check((self.pawn().get_actor_location()-position).length() > 50,
                       'existing move order continues without a new click at ' + str(fps) + ' FPS', True)
            animation = self.mesh().get_anim_instance()
            self.check(isinstance(animation, unreal.CountessDamageAnimInstance) and
                       animation.get_editor_property('damage_reaction_weight') > .8 and
                       abs(animation.get_editor_property('damage_reaction_time') -
                           self.combat().get_damage_feedback_age()) < .06,
                       'independent recoil plays at authored 1x while moving at ' + str(fps) + ' FPS', True)
            self.common_damage(20)
            self.check(self.combat().get_health() == 80, 'repeated protected damage remains rejected', True)
            yield .6
            self.check(abs(self.combat().get_damage_trail_health()-80) < .01 and not self.combat().is_invulnerable(),
                       'damage trail and original protection expire at ' + str(fps) + ' FPS', True)
            self.check(animation.get_editor_property('damage_reaction_weight') > 0 and
                       self.combat().get_damage_reaction_age() < .75,
                       'protected contact restarts only the Countess visual recoil', True)
            yield .2
            self.check(animation.get_editor_property('damage_reaction_weight') == 0,
                       'visual recoil settles without a recovery lock at ' + str(fps) + ' FPS', True)
        for label, sign, axis in [('Fwd', 1, 'forward'), ('Bwd', -1, 'forward'),
                                  ('Left', -1, 'right'), ('Right', 1, 'right')]:
            yield from self.respawn_common()
            direction = (self.pawn().get_actor_forward_vector() if axis == 'forward'
                         else self.pawn().get_actor_right_vector()) * sign
            self.directional_damage(direction)
            yield .18
            animation = self.mesh().get_anim_instance()
            self.check(animation.get_editor_property('damage_reaction_sequence').get_name().endswith(label)
                       and animation.get_editor_property('damage_reaction_weight') > .9
                       and not self.combat().is_crowd_controlled(),
                       'Countess upper-body recoil selects ' + label + ' without locking controls', True)
            self.destroy_fixtures()
        self.check(self.combat().apply_stun(.2), 'short stun can supersede ordinary recoil', True)
        yield from self.wait_recovered('short stun recovers')
        yield .04
        self.check(self.mesh().get_anim_instance().get_editor_property('damage_reaction_weight') == 0,
                   'short stun recovery does not resume the previous ordinary recoil', True)
        yield from self.respawn_common()
        p = self.pawn().get_actor_location()
        aim = self.point(p.x + 350, p.y)
        self.console(f'CountessComboQA.Mouse Press Left {aim.x} {aim.y} {aim.z}')
        yield qa_play.Until(lambda:self.pawn().is_attacking(), 4, 'held basic attack starts')
        anim = self.mesh().get_anim_instance()
        montage = anim.get_current_active_montage()
        self.common_damage()
        self.check(self.pawn().is_attacking() and anim.get_current_active_montage() == montage and
                   not self.combat().is_crowd_controlled(), 'damage preserves the active basic attack montage', True)
        yield 1.1
        self.check(self.pawn().is_attacking(), 'held basic attacks continue after damage without another press', True)
        self.console(f'CountessComboQA.Mouse Release Left {aim.x} {aim.y} {aim.z}')
        yield .8
        yield from self.respawn_common()
        self.aim(aim)
        self.press('W')
        yield .05
        self.release('W')
        self.check(self.skills().is_casting(), 'W starts before damage', True)
        self.common_damage()
        self.check(self.skills().is_casting() and not self.combat().is_crowd_controlled(), 'ordinary damage preserves W', True)
        self.check(self.combat().apply_stun(.7), 'explicit stun still interrupts W', True)
        self.check(not self.skills().is_casting() and self.combat().is_stunned(), 'explicit stun owns the control lock', True)
        yield .04
        self.check(self.mesh().get_anim_instance().get_editor_property('damage_reaction_weight') == 0,
                   'ordinary recoil yields to the explicit stun pose', True)
        montage = self.mesh().get_anim_instance().get_current_active_montage()
        self.check(abs(self.mesh().get_anim_instance().montage_get_play_rate(montage)-1.0) < .001,
                   'stun retains authored 1x animation speed', True)
        yield from self.wait_recovered('explicit stun restores movement')
        yield .8
        self.check(self.combat().apply_knockback(unreal.Vector(1,0,0),180,.4), 'explicit knockback remains usable', True)
        yield from self.wait_recovered('knockback restores movement')
        yield from self.respawn_common()
        self.common_damage(80)
        yield .12
        yield from self.capture('countess-low-health')
        self.check(self.combat().get_health() == 20 and not self.combat().is_crowd_controlled(),
                   'low health warning does not restrict controls', True)
        yield .7
        self.common_damage(1000)
        self.check(not self.combat().is_alive(), 'lethal damage still reaches death', True)
        yield from self.respawn_common()
        self.check(self.combat().get_damage_trail_health() == 100 and self.combat().get_damage_feedback_age() > 1,
                   'respawn clears damage trail and warning state', True)

    def countess_repeat_feedback(self):
        for fps in (30, 60):
            self.console('t.MaxFPS ' + str(fps))
            yield from self.prepare('One', 'BP_CountessCharacter_C')
            combat = self.combat()
            animation = self.mesh().get_anim_instance()
            pawn = self.pawn()
            position = pawn.get_actor_location()
            source = self.directional_damage(pawn.get_actor_forward_vector(), 20)
            first_hit = self.now()
            yield .18
            self.check(combat.get_health() == 80 and animation.get_editor_property('damage_reaction_weight') > .9,
                       'first Countess hit begins recoil at ' + str(fps) + ' FPS', True)
            for direction, clip in [(pawn.get_actor_forward_vector() * -1.0, 'Bwd'),
                                    (pawn.get_actor_right_vector(), 'Right')]:
                source.set_actor_location(position + direction * 400, False, True)
                damage_age = combat.get_damage_feedback_age()
                unreal.GameplayStatics.apply_damage(pawn, 20, None, source, None)
                self.check(combat.get_health() == 80 and combat.is_invulnerable() and
                           combat.get_damage_reaction_age() < .01 and
                           combat.get_damage_feedback_age() >= damage_age,
                           'protected contact restarts recoil without changing health or damage time: ' + clip, True)
                yield .12
                self.check(animation.get_editor_property('damage_reaction_sequence').get_name().endswith(clip) and
                           animation.get_editor_property('damage_reaction_time') < .20 and
                           animation.get_editor_property('damage_reaction_weight') > .9 and
                           not combat.is_crowd_controlled(),
                           'unfinished recoil reacts again in the latest contact direction: ' + clip, True)
            yield from self.wait_elapsed(first_hit, .79)
            self.check(not combat.is_invulnerable() and combat.get_health() == 80 and
                       abs(combat.get_damage_trail_health() - 80) < .01,
                       'repeat contacts do not extend the .75s protection or HUD trail', True)
            unreal.GameplayStatics.apply_damage(pawn, 20, None, source, None)
            self.check(combat.get_health() == 60, 'damage applies after the original protection deadline', True)
            self.check(combat.apply_stun(.2), 'explicit stun can still supersede repeat recoil', True)
            yield .04
            previous_age = combat.get_damage_reaction_age()
            unreal.GameplayStatics.apply_damage(pawn, 20, None, source, None)
            self.check(combat.get_damage_reaction_age() >= previous_age,
                       'contacts during stun do not queue an ordinary recoil', True)
            yield .25
            self.check(animation.get_editor_property('damage_reaction_weight') == 0,
                       'stun recovery does not replay an older contact', True)
            self.destroy_fixtures()
        for key, name in CHARACTERS[1:]:
            yield from self.prepare(key, name)
            combat = self.combat()
            self.common_damage(10)
            yield .2
            self.common_damage(10)
            self.check(not combat.uses_non_interrupting_damage_feedback() and combat.get_health() == 90 and
                       combat.get_damage_reaction_age() > 1 and not combat.is_hit_reacting(),
                       name + ': existing protected-hit behavior is unchanged', True)
        yield from self.prepare('One', 'BP_CountessCharacter_C')
        self.check(self.combat().get_damage_reaction_age() > 1 and
                   self.mesh().get_anim_instance().get_editor_property('damage_reaction_weight') == 0,
                   'switching back to Countess does not inherit previous contact feedback', True)

    def sequence(self):
        if not self.ready('Lvl_DarkTrainingRoom'):
            self.click('ToggleTravel'); yield .1; self.click('GoTraining')
            yield qa_play.Until(lambda:self.ready('Lvl_DarkTrainingRoom'), 45, 'training opens for directional CC QA')
        self.console('CharacterVisualQA.ViewportSize 1600 900')
        self.console('t.MaxFPS 60')
        self.report['scope'] = 'selected groups only: ' + ', '.join(self.groups)
        self.report['groups'] = list(self.groups)
        self.report['fixtures'] = 'PIE dummy/remote prop transforms and mesh are borrowed and restored; editor world is untouched'
        self.report['capture_only_time_dilation'] = .2
        for group in self.groups:
            if group not in ('directions', 'crowd_control', 'boundaries', 'cast_interruptions', 'lifecycle', 'countess_feedback', 'countess_repeat_feedback'):
                raise ValueError('Unknown QA group: ' + group)
            yield from getattr(self, group)()

    def finish(self, error=None):
        self.destroy_fixtures()
        super().finish(error)


ACTIVE = None


def start(output, reuse_pie=True, groups=None):
    """Run all coverage or a selected group in the parent's real PIE session."""
    global ACTIVE
    ACTIVE = DirectionalCombatRunner(output, groups)
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
