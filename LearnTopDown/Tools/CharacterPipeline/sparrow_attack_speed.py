"""Check the native bow speed default, cadence, cancel and R shooting."""
import json
import os
from pathlib import Path
import sys
import traceback
import types
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
job=json.loads(Path(os.environ['CHARACTER_PIPELINE_JOB']).read_text(encoding='utf-8'))
OUT=Path(job['output'])
RATE=float(job.get('attack_rate',1.2))
NATURAL='/Game/TopDown/Characters/Sparrow/Animations/AM_Sparrow_PrimaryNatural'
report={'passed':False,'rate':RATE,'asset_defaults_modified':False}
try:
    assert .5<=RATE<=2 and OUT.resolve().is_relative_to(ROOT/'Saved/QA')
    actual=unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Attack.Speed')
    assert abs(actual-RATE)<.0001, 'Build the native attack-speed default before this smoke check'
    report['native_default_rate']=actual
    report['passed']=True
except Exception:
    report['error']=traceback.format_exc()
finally:
    (OUT/'speed-configuration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if not report['passed']:
    unreal.log_error(report['error'])
    unreal.SystemLibrary.quit_editor()
else:
    from context import fps
    from training_room_verify import TrainingRunner, select
    from countess_w_speed_compare import settle_switch

    def ready(rig):
        yield from select(rig,'sparrow')
        step=rig.pawn.get_editor_property('combo_attacks')[0]
        rig.check(abs(step.get_editor_property('play_rate')-RATE)<.0001,'spawned bow uses saved faster attack rate')
        rig.check(abs(rig.pawn.get_editor_property('combo_restart_cooldown')-.3/RATE)<.0001,
                  'spawned bow uses matching shorter restart cooldown')

    def cadence(rig):
        yield from ready(rig)
        target=rig.dummy(0,550)
        starts=[]; releases=[]
        for index in range(3):
            if index==0:
                start=rig.now
                yield from rig.click('Left',target.get_actor_location())
            else:
                accepted_at=[]
                def next_shot():
                    if rig.pawn.try_basic_attack(target.get_actor_location()):
                        accepted_at.append(rig.now)
                        return True
                    return False
                yield rig.until(next_shot,1.5,
                                'next attack starts when the real restart cooldown clears')
                start=accepted_at[0]
            starts.append(start)
            rig.check(rig.pawn.is_attacking(),'accepted input plays the basic attack')
            montage=unreal.load_asset(NATURAL)
            rig.check(abs(rig.anim.montage_get_play_rate(montage)-RATE)<.0001,'actual natural montage plays at 1.2x')
            if index==0:
                yield .10
                yield rig.capture('faster-bow-draw')
            yield rig.until(lambda:bool(rig.arrows()),.45,'draw produces a flying arrow')
            release=rig.now-start
            rig.check(.25/RATE-.0001<=release<=.25/RATE+3/fps,'release remains synchronized with the faster draw')
            releases.append(release)
            if index==0:
                yield rig.capture('faster-bow-release')
            yield rig.idle()
        yield .35
        intervals=[b-a for a,b in zip(starts,starts[1:])]
        expected=(.9297272562980652+.3)/RATE
        rig.check(all(abs(dt-expected)<4/fps for dt in intervals),'actual repeated-shot interval is approximately 1.025 seconds')
        rig.check(abs(rig.health(target)-38.95)<.01 and rig.component.get_relentless_stacks(target)==3,
                  'three faster shots preserve existing damage and E passive scaling')
        rig.assert_recovered()
        rig.data.update(start_intervals=intervals,release_delays=releases,target_health=rig.health(target))

    def cancel(rig):
        yield from ready(rig)
        target=rig.dummy(0,550)
        rig.check(rig.pawn.try_basic_attack(target.get_actor_location()),'faster draw begins before cancel')
        yield .08
        rig.interrupt()
        yield 1.0
        rig.check(rig.health(target)==100 and not rig.arrows(),'canceling before faster release still prevents damage')
        rig.assert_recovered()

    def enhanced(rig):
        yield from ready(rig)
        target=rig.dummy(0,650)
        yield from rig.skill_key('R',target.get_actor_location())
        yield rig.idle()
        rig.check(rig.component.is_inner_fire_active(),'R is active for the enhanced basic attack')
        start=rig.now
        yield from rig.click('Left',target.get_actor_location())
        yield rig.until(lambda:len(rig.arrows())==3,.3,'R basic attack still emits three arrows')
        rig.check(.05/RATE-.0001<=rig.now-start<=.05/RATE+3/fps,'R release scales with basic attack speed')
        rig.data['release_delay']=rig.now-start
        yield 1.1
        rig.assert_recovered()

    class SpeedRunner(TrainingRunner):
        def __init__(self):
            super().__init__()
            self.cases=[('cadence',cadence),('cancel_before_release',cancel),('R_basic_attack',enhanced)]
            self.report_name='attack-speed-smoke.json'
            self.report.update(suite='sparrow_attack_speed_scoped',attack_rate=RATE,
                               verification_scope='60fps cadence, cancel, enhanced shot; selected-file preservation only')
        def case_generator(self,factory):
            self.rig.switch=types.MethodType(settle_switch,self.rig)
            yield from TrainingRunner.case_generator(self,factory)
    runtime=SpeedRunner()
    runtime.start()
